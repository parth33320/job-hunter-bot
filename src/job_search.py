"""Search for jobs using Google Custom Search API."""
import requests
from datetime import datetime, timedelta
from src.config import CONFIG
from src.database import already_applied

def build_search_queries() -> list[str]:
    """Build Google search queries for all job titles and ATS platforms."""
    
    job_titles = CONFIG['job_search']['titles']
    locations = CONFIG['job_search']['locations']
    ats_domains = CONFIG['job_search']['ats_domains']
    
    queries = []
    
    # Build site: filter for all ATS platforms
    site_filter = " OR ".join([f"site:{domain}" for domain in ats_domains.values()])
    
    for title in job_titles:
        for location in locations:
            # Combine into one efficient query
            query = f'({site_filter}) "{title}" "{location}"'
            queries.append(query)
    
    return queries

def search_jobs(max_results_per_query: int = 10) -> list[dict]:
    """Search Google for jobs posted in last 24 hours."""
    
    api_key = CONFIG['secrets']['google_api_key']
    cx = CONFIG['secrets']['google_cx']
    blacklist = [c.lower() for c in CONFIG['blacklist_companies']]
    
    all_jobs = []
    seen_urls = set()
    
    queries = build_search_queries()
    print(f"🔍 Running {len(queries)} search queries...")
    
    for query in queries:
        try:
            params = {
                'key': api_key,
                'cx': cx,
                'q': query,
                'num': max_results_per_query,
                'dateRestrict': 'd1',  # Last 24 hours only!
            }
            
            response = requests.get(
                'https://www.googleapis.com/customsearch/v1',
                params=params
            )
            
            if response.status_code != 200:
                print(f"⚠️ Search API error: {response.status_code}")
                continue
            
            data = response.json()
            items = data.get('items', [])
            
            for item in items:
                url = item['link']
                title = item['title']
                snippet = item.get('snippet', '')
                
                # Skip if already seen this URL
                if url in seen_urls:
                    continue
                seen_urls.add(url)
                
                # Skip if already applied
                if already_applied(url):
                    continue
                
                # Skip blacklisted companies
                is_blacklisted = False
                for blacklisted in blacklist:
                    if blacklisted in url.lower() or blacklisted in title.lower():
                        is_blacklisted = True
                        break
                
                if is_blacklisted:
                    print(f"🚫 Skipping blacklisted: {title}")
                    continue
                
                # Determine ATS type
                ats_type = detect_ats_type(url)
                if not ats_type:
                    continue  # Not a supported ATS
                
                # Extract company name from URL/title
                company = extract_company_name(url, title)
                
                job = {
                    'url': url,
                    'title': title,
                    'company': company,
                    'snippet': snippet,
                    'ats_type': ats_type,
                }
                
                all_jobs.append(job)
                print(f"🦴 Found: {company} - {title} [{ats_type}]")
        
        except Exception as e:
            print(f"❌ Search error: {e}")
            continue
    
    print(f"\n🎯 Total jobs found: {len(all_jobs)}")
    return all_jobs

def detect_ats_type(url: str) -> str | None:
    """Detect which ATS platform from URL."""
    url_lower = url.lower()
    
    if 'myworkdayjobs.com' in url_lower or 'myworkday.com' in url_lower:
        return 'workday'
    elif 'greenhouse.io' in url_lower:
        return 'greenhouse'
    elif 'icims.com' in url_lower:
        return 'icims'
    
    return None

def extract_company_name(url: str, title: str) -> str:
    """Try to extract company name from URL or title."""
    import re
    
    # Workday: company.wd1.myworkdayjobs.com
    workday_match = re.search(r'([a-zA-Z0-9-]+)\.wd\d\.myworkdayjobs', url)
    if workday_match:
        return workday_match.group(1).replace('-', ' ').title()
    
    # Greenhouse: boards.greenhouse.io/company
    greenhouse_match = re.search(r'greenhouse\.io/([a-zA-Z0-9-]+)', url)
    if greenhouse_match:
        return greenhouse_match.group(1).replace('-', ' ').title()
    
    # iCIMS: careers-company.icims.com
    icims_match = re.search(r'careers[-_]?([a-zA-Z0-9-]+)\.icims', url)
    if icims_match:
        return icims_match.group(1).replace('-', ' ').title()
    
    # Fallback: try to get from title
    # Often format: "Job Title at Company Name"
    at_match = re.search(r' at ([A-Z][^|]+)', title)
    if at_match:
        return at_match.group(1).strip()
    
    return "Unknown Company"
