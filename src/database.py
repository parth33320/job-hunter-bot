"""SQLite database for tracking applications and resume rules."""
import sqlite3
from pathlib import Path
from datetime import datetime

DB_PATH = Path(__file__).parent.parent / "job_hunter.db"

def init_db():
    """Create tables if they don't exist."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Table 1: Jobs we've already applied to
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS applied_jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_url TEXT UNIQUE,
            company TEXT,
            job_title TEXT,
            ats_type TEXT,
            resume_used TEXT,
            date_applied TIMESTAMP,
            status TEXT DEFAULT 'applied'
        )
    ''')
    
    # Table 2: Resume rules (job keyword -> resume filename)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS resume_rules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_keyword TEXT UNIQUE,
            resume_filename TEXT,
            date_learned TIMESTAMP
        )
    ''')
    
    # Table 3: Application stats
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS daily_stats (
            date TEXT PRIMARY KEY,
            applications_count INTEGER DEFAULT 0
        )
    ''')
    
    conn.commit()
    conn.close()
    print("🗄️ Database initialized.")

def already_applied(job_url: str) -> bool:
    """Check if we already applied to this job."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM applied_jobs WHERE job_url = ?", (job_url,))
    result = cursor.fetchone()
    conn.close()
    return result is not None

def log_application(job_url: str, company: str, job_title: str, ats_type: str, resume_used: str):
    """Record that we applied to a job."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT OR IGNORE INTO applied_jobs 
        (job_url, company, job_title, ats_type, resume_used, date_applied)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (job_url, company, job_title, ats_type, resume_used, datetime.now()))
    
    # Update daily count
    today = datetime.now().strftime("%Y-%m-%d")
    cursor.execute('''
        INSERT INTO daily_stats (date, applications_count) 
        VALUES (?, 1)
        ON CONFLICT(date) DO UPDATE SET applications_count = applications_count + 1
    ''', (today,))
    
    conn.commit()
    conn.close()

def get_today_application_count() -> int:
    """Get how many applications we've done today."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    today = datetime.now().strftime("%Y-%m-%d")
    cursor.execute("SELECT applications_count FROM daily_stats WHERE date = ?", (today,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else 0

def get_resume_for_keyword(job_title: str) -> str | None:
    """Check if we have a learned resume rule for this job type."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Check each word in job title against our rules
    job_words = job_title.lower().split()
    
    for word in job_words:
        cursor.execute(
            "SELECT resume_filename FROM resume_rules WHERE ? LIKE '%' || job_keyword || '%'",
            (job_title.lower(),)
        )
        result = cursor.fetchone()
        if result:
            conn.close()
            return result[0]
    
    conn.close()
    return None

def learn_resume_rule(job_keyword: str, resume_filename: str):
    """Save a new resume rule that Parth taught us."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT OR REPLACE INTO resume_rules (job_keyword, resume_filename, date_learned)
        VALUES (?, ?, ?)
    ''', (job_keyword.lower(), resume_filename, datetime.now()))
    
    conn.commit()
    conn.close()
    print(f"🧠 Bot learned: '{job_keyword}' -> '{resume_filename}'")

def get_total_dry_runs() -> int:
    """Count total applications (to know when to exit dry run mode)."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM applied_jobs")
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else 0

# Initialize on import
init_db()
