"""
Search for jobs using Google Custom Search API.
Search engine is pre-filtered to only search:
  - *.myworkdayjobs.com (Workday)
  - *.greenhouse.io (Greenhouse)
  - *.icims.com (iCIMS)

No need for site: operators in queries!
"""

import requests
import time
import random
import re
from datetime import datetime, timedelta
from src.config import CONFIG
from src.database import already_applied

class JobSearcher:
    """Searches for fresh jobs on ATS platforms."""
    
    def __init__(self):
        self.api_key = CONFIG['secrets']['google_api_key']
        self.cx = CONFIG['secrets']['google_cx']
        self.blacklist = [c.lower().strip() for c in CONFIG['blacklist_companies']]
        self.job_titles = CONFIG['job_search']['titles']
        self.locations = CONFIG['job_search']['locations']
        self.found_jobs = []
        self.seen_urls = set()
    
    def build_search_queries(self) -> list[str]:
        """
        Build search queries for all job titles and locations.
        
        Since our Custom Search Engine is pre-filtered to only search
        Workday, Greenhouse, and iCIMS domains, we don't need site: operators!
        """
        
        queries = []
        
        for title in self.job_titles:
            for location in self.locations:
                # Simple query - search engine handles domain filtering
                query = f'"{title}" "{location}"'
                queries.append({
                    'query': query,
                    'title': title,
                    'location': location
                })
        
        # Also add queries without location for broader results
        for title in self.job_titles:
            queries.append({
                'query': f'"{title}"',
                'title': title,
                'location': 'any'
            })
        
        return queries
    
    def search_google(self, query: str, max_results: int = 10) -> list[dict]:
        """
        Execute a single Google Custom Search API call.
        
        Args:
            query: The search query string
            max_results: Number of results to fetch (max 10 per call)
        
        Returns:
            List of search result items
        """
        
        try:
            params = {
                'key': self.api_key,
                'cx': self.cx,
                'q': query,
                'num': min(max_results, 10),  # API max is 10
                'dateRestrict': 'd1',  # 🔥 LAST 24 HOURS ONLY!
            }
            
            response = requests.get(
                'https://www.googleapis.com/customsearch/v1',
                params=params,
                timeout=30
            )
            
            if response.status_code == 429:
                print("⚠️ Rate limited! Waiting 60 seconds...")
                time.sleep(60)
                return []
            
            if response.status_code != 200:
                print(f"⚠️ Search API error {response.status_code}: {response.text[:200]}")
                return []
            
            data = response.json()
            
            # Check if we have results
            if 'items' not in data:
                return []
            
            return data['items']
            
        except requests.exceptions.Timeout:
            print("⚠️ Search request timed out")
            return []
        except Exception as e:
            print(f"❌ Search error: {e}")
            return []
    
    def detect_ats_type(self, url: str) -> str | None:
        """
        Detect which ATS platform from URL.
        
        Returns:
            'workday', 'greenhouse', 'icims', or None if unknown
        """
        url_lower = url.lower()
        
        # Workday patterns
        if 'myworkdayjobs.com' in url_lower or 'myworkday.com' in url_lower:
            return 'workday'
        
        # Greenhouse patterns
        if 'greenhouse.io' in url_lower:
            return 'greenhouse'
        
        # iCIMS patterns
        if 'icims.com' in url_lower:
            return 'icims'
        
        return None
    
    def extract_company_name(self, url: str, title: str) -> str:
        """
        Extract company name from URL or search result title.
        
        Args:
            url: The job posting URL
            title: The search result title
        
        Returns:
            Best guess at company name
        """
        
        # Workday: company.wd1.myworkdayjobs.com or company.wd5.myworkdayjobs.com
        workday_match = re.search(r'([a-zA-Z0-9-]+)\.wd\d+\.myworkdayjobs', url)
        if workday_match:
            company = workday_match.group(1)
            return company.replace('-', ' ').replace('_', ' ').title()
        
        # Workday alternate: https://company.myworkdayjobs.com
        workday_match2 = re.search(r'https?://([a-zA-Z0-9-]+)\.myworkdayjobs', url)
        if workday_match2:
            company = workday_match2.group(1)
            return company.replace('-', ' ').replace('_', ' ').title()
        
        # Greenhouse: boards.greenhouse.io/companyname or job-boards.greenhouse.io/companyname
        greenhouse_match = re.search(r'greenhouse\.io/([a-zA-Z0-9-]+)', url)
        if greenhouse_match:
            company = greenhouse_match.group(1)
            return company.replace('-', ' ').replace('_', ' ').title()
        
        # iCIMS: careers-company.icims.com or company.icims.com
        icims_match = re.search(r'([a-zA-Z0-9-]+)\.icims\.com', url)
        if icims_match:
            company = icims_match.group(1)
            # Remove common prefixes
            company = re.sub(r'^careers[-_]?', '', company)
            company = re.sub(r'^jobs[-_]?', '', company)
            return company.replace('-', ' ').replace('_', ' ').title()
        
        # Fallback: Try to extract from title
        # Common patterns: "Job Title at Company Name" or "Job Title - Company Name"
        at_match = re.search(r' at ([A-Z][^|–\-]+)', title)
        if at_match:
            return at_match.group(1).strip()
        
        dash_match = re.search(r' [-–] ([A-Z][^|]+)$', title)
        if dash_match:
            return dash_match.group(1).strip()
        
        return "Unknown Company"
    
    def is_blacklisted(self, company: str, url: str, title: str) -> bool:
        """
        Check if job is from a blacklisted company.
        
        Args:
            company: Extracted company name
            url: Job URL
            title: Search result title
        
        Returns:
            True if blacklisted, False otherwise
        """
        
        check_text = f"{company} {url} {title}".lower()
        
        for blacklisted in self.blacklist:
            if blacklisted in check_text:
                return True
        
        return False
    
    def is_spam_aggregator(self, url: str) -> bool:
        """
        Check if URL is from a spam job aggregator site.
        
        Even with pre-filtered search engine, sometimes weird results slip through.
        """
        
        spam_domains = [
            'jooble.org',
            'adzuna.com',
            'talent.com',
            'ziprecruiter.com',
            'glassdoor.com',
            'indeed.com',
            'linkedin.com',
            'monster.com',
            'careerbuilder.com',
            'simplyhired.com',
            'jobrapido.com',
            'neuvoo.com',
            'recruit.net',
            'jobleads.com',
        ]
        
        url_lower = url.lower()
        
        for spam in spam_domains:
            if spam in url_lower:
                return True
        
        return False
    
    def process_search_result(self, item: dict, search_title: str) -> dict | None:
        """
        Process a single search result into a job dict.
        
        Args:
            item: Google search result item
            search_title: The job title we searched for
        
        Returns:
            Job dict or None if should be skipped
        """
        
        url = item.get('link', '')
        title = item.get('title', '')
        snippet = item.get('snippet', '')
        
        # Skip if already seen this URL in this run
        if url in self.seen_urls:
            return None
        self.seen_urls.add(url)
        
        # Skip if already applied
        if already_applied(url):
            print(f"   ⏭️ Already applied: {title[:50]}...")
            return None
        
        # Skip spam aggregators
        if self.is_spam_aggregator(url):
            print(f"   🚫 Spam aggregator: {url[:50]}...")
            return None
        
        # Detect ATS type
        ats_type = self.detect_ats_type(url)
        if not ats_type:
            print(f"   ❓ Unknown ATS: {url[:50]}...")
            return None
        
        # Extract company name
        company = self.extract_company_name(url, title)
        
        # Check blacklist
        if self.is_blacklisted(company, url, title):
            print(f"   🚫 Blacklisted company: {company}")
            return None
        
        # Build job dict
        job = {
            'url': url,
            'title': title,
            'company': company,
            'snippet': snippet,
            'ats_type': ats_type,
            'search_title': search_title,  # What we searched for
            'found_at': datetime.now().isoformat(),
        }
        
        return job
    
    def hunt(self, max_results_per_query: int = 10) -> list[dict]:
        """
        Main hunting function. Searches for all job titles and locations.
        
        Args:
            max_results_per_query: How many results to fetch per search query
        
        Returns:
            List of job dicts ready for application
        """
        
        self.found_jobs = []
        self.seen_urls = set()
        
        queries = self.build_search_queries()
        total_queries = len(queries)
        
        print(f"\n{'='*60}")
        print(f"🦴 CAVEMAN JOB HUNT BEGINNING!")
        print(f"   Searching {total_queries} queries...")
        print(f"   Date filter: Last 24 hours only")
        print(f"   ATS platforms: Workday, Greenhouse, iCIMS")
        print(f"{'='*60}\n")
        
        for i, query_info in enumerate(queries):
            query = query_info['query']
            search_title = query_info['title']
            location = query_info['location']
            
            print(f"\n🔍 [{i+1}/{total_queries}] Searching: {search_title} ({location})")
            
            # Execute search
            results = self.search_google(query, max_results_per_query)
            
            if not results:
                print(f"   No results found.")
                continue
            
            print(f"   Found {len(results)} raw results...")
            
            # Process each result
            for item in results:
                job = self.process_search_result(item, search_title)
                if job:
                    self.found_jobs.append(job)
                    print(f"   ✅ [{job['ats_type'].upper()}] {job['company']}: {job['title'][:40]}...")
            
            # Be nice to Google - random delay between queries
            delay = random.uniform(1.5, 3.0)
            time.sleep(delay)
        
        # Sort by ATS type (Greenhouse first - easiest to apply)
        ats_priority = {'greenhouse': 1, 'icims': 2, 'workday': 3}
        self.found_jobs.sort(key=lambda x: ats_priority.get(x['ats_type'], 99))
        
        # Final summary
        print(f"\n{'='*60}")
        print(f"🎯 HUNT COMPLETE!")
        print(f"   Total jobs found: {len(self.found_jobs)}")
        
        # Count by ATS
        ats_counts = {}
        for job in self.found_jobs:
            ats = job['ats_type']
            ats_counts[ats] = ats_counts.get(ats, 0) + 1
        
        for ats, count in ats_counts.items():
            print(f"   - {ats.upper()}: {count} jobs")
        
        print(f"{'='*60}\n")
        
        return self.found_jobs
    
    def get_jobs_summary(self) -> str:
        """Get a text summary of found jobs for ntfy notification."""
        
        if not self.found_jobs:
            return "No new jobs found in last 24 hours."
        
        summary = f"Found {len(self.found_jobs)} new jobs:\n\n"
        
        for i, job in enumerate(self.found_jobs[:10]):  # First 10 only for ntfy
            summary += f"{i+1}. [{job['ats_type'].upper()}] {job['company']}\n"
            summary += f"   {job['title'][:50]}\n"
        
        if len(self.found_jobs) > 10:
            summary += f"\n...and {len(self.found_jobs) - 10} more jobs."
        
        return summary


# === STANDALONE FUNCTION FOR EASY IMPORT ===

def search_jobs(max_results_per_query: int = 10) -> list[dict]:
    """
    Convenience function to search for jobs.
    
    Usage:
        from src.job_search import search_jobs
        jobs = search_jobs()
    """
    searcher = JobSearcher()
    return searcher.hunt(max_results_per_query)


# === TEST FUNCTION ===

def test_search():
    """Test the job search functionality."""
    
    print("🧪 Testing Job Search...")
    
    searcher = JobSearcher()
    
    # Test with just one query
    test_queries = searcher.build_search_queries()[:3]  # First 3 only
    
    print(f"\nTest queries:")
    for q in test_queries:
        print(f"  - {q}")
    
    # Run actual search
    jobs = searcher.hunt(max_results_per_query=5)
    
    print(f"\n📋 Sample results:")
    for job in jobs[:5]:
        print(f"\n  Company: {job['company']}")
        print(f"  Title: {job['title']}")
        print(f"  ATS: {job['ats_type']}")
        print(f"  URL: {job['url'][:80]}...")


if __name__ == "__main__":
    # Run test if this file is executed directly
    test_search()
