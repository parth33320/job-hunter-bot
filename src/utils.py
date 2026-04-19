"""Utility functions."""
import random
import time
from pathlib import Path

SCREENSHOT_DIR = Path(__file__).parent.parent / "screenshots"
SCREENSHOT_DIR.mkdir(exist_ok=True)

def human_delay(min_seconds: float = 1.0, max_seconds: float = 3.0):
    """Random delay to seem more human."""
    delay = random.uniform(min_seconds, max_seconds)
    time.sleep(delay)

def long_delay():
    """Longer random delay between applications."""
    delay = random.gauss(mu=45, sigma=15)
    delay = max(20, min(delay, 90))
    print(f"⏳ Waiting {delay:.0f} seconds before next application...")
    time.sleep(delay)

def get_screenshot_path(company: str, job_title: str) -> str:
    """Generate screenshot filename."""
    safe_company = "".join(c if c.isalnum() else "_" for c in company)
    safe_title = "".join(c if c.isalnum() else "_" for c in job_title)
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    filename = f"{timestamp}_{safe_company}_{safe_title}.png"
    return str(SCREENSHOT_DIR / filename)
