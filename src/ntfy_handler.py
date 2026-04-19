"""Send and receive ntfy notifications."""
import requests
import json
import time
from src.config import CONFIG

ALERT_TOPIC = CONFIG['secrets']['ntfy_alert_topic']
COMMAND_TOPIC = CONFIG['secrets']['ntfy_command_topic']

def send_alert(title: str, message: str, priority: str = "default", tags: list = None):
    """Send notification to Parth's phone."""
    headers = {
        "Title": title,
        "Priority": priority,
    }
    if tags:
        headers["Tags"] = ",".join(tags)
    
    try:
        requests.post(
            f"https://ntfy.sh/{ALERT_TOPIC}",
            data=message.encode('utf-8'),
            headers=headers
        )
        print(f"📱 Sent ntfy: {title}")
    except Exception as e:
        print(f"❌ Failed to send ntfy: {e}")

def send_screenshot(title: str, message: str, screenshot_path: str):
    """Send notification with screenshot attachment."""
    try:
        with open(screenshot_path, 'rb') as f:
            requests.post(
                f"https://ntfy.sh/{ALERT_TOPIC}",
                data=f.read(),
                headers={
                    "Title": title,
                    "Filename": "screenshot.png",
                    "X-Message": message,
                }
            )
        print(f"📱 Sent ntfy with screenshot: {title}")
    except Exception as e:
        print(f"❌ Failed to send screenshot: {e}")

def wait_for_response(timeout_minutes: int = 30) -> str | None:
    """Wait for Parth to respond via ntfy."""
    print(f"⏳ Waiting for Parth's response (timeout: {timeout_minutes} mins)...")
    
    timeout_seconds = timeout_minutes * 60
    start_time = time.time()
    
    # Use ntfy's JSON streaming endpoint
    try:
        # Get only new messages (since=now means only future messages)
        response = requests.get(
            f"https://ntfy.sh/{COMMAND_TOPIC}/json",
            params={"poll": 1, "since": "now"},
            stream=True,
            timeout=timeout_seconds
        )
        
        for line in response.iter_lines():
            if time.time() - start_time > timeout_seconds:
                print("⏰ Timeout waiting for response.")
                return None
                
            if line:
                try:
                    data = json.loads(line)
                    if data.get('event') == 'message':
                        message = data.get('message', '').strip()
                        print(f"📬 Received response: {message}")
                        return message
                except json.JSONDecodeError:
                    continue
                    
    except requests.exceptions.Timeout:
        print("⏰ Timeout waiting for response.")
        return None
    except Exception as e:
        print(f"❌ Error waiting for response: {e}")
        return None
    
    return None

def ask_for_resume(job_title: str, company: str, job_url: str) -> str | None:
    """Ask Parth which resume to use for a new job type."""
    message = f"""🦴 NEW JOB TYPE DETECTED!

Company: {company}
Title: {job_title}
URL: {job_url}

Bot doesn't know which resume to use.
Reply with the Google Drive filename (e.g., "Parth_Data_Analyst.pdf")

Or reply "SKIP" to skip this job."""

    send_alert(
        title="📄 Which Resume?",
        message=message,
        priority="high",
        tags=["question", "resume"]
    )
    
    response = wait_for_response(timeout_minutes=CONFIG['settings']['timeout_minutes'])
    
    if response and response.upper() != "SKIP":
        return response
    return None

def ask_for_approval(job_title: str, company: str, screenshot_path: str) -> bool:
    """Ask Parth to approve application (dry run mode)."""
    message = f"""🎯 READY TO APPLY!

Company: {company}
Title: {job_title}

Reply "YES" to submit
Reply "NO" to skip"""

    send_screenshot(
        title="👀 Review Application",
        message=message,
        screenshot_path=screenshot_path
    )
    
    response = wait_for_response(timeout_minutes=CONFIG['settings']['timeout_minutes'])
    
    if response and response.upper() in ["YES", "Y", "APPROVE", "SUBMIT"]:
        return True
    return False

def send_success(company: str, job_title: str, resume_used: str):
    """Notify Parth of successful application."""
    send_alert(
        title="✅ Application Submitted!",
        message=f"Applied to {job_title} at {company}\nResume: {resume_used}",
        tags=["white_check_mark", "tada"]
    )

def send_daily_summary(total_applied: int, jobs_found: int, errors: int):
    """Send end-of-day summary."""
    send_alert(
        title="📊 Daily Hunt Summary",
        message=f"""🦣 Hunt Complete!

Jobs Found: {jobs_found}
Applied: {total_applied}
Errors: {errors}

Bot go sleep now. Wake up tomorrow.""",
        tags=["chart_with_upwards_trend"]
    )
