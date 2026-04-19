"""Read OTP codes from Gmail for Workday verification."""
import imaplib
import email
import re
import time
from email.header import decode_header

from src.config import CONFIG

def get_latest_otp(sender_filter: str = "workday", max_wait_seconds: int = 120) -> str | None:
    """Wait for and extract OTP code from email."""
    
    gmail_address = CONFIG['secrets']['gmail_address']
    gmail_password = CONFIG['secrets']['gmail_app_password']
    
    print(f"📧 Checking Gmail for OTP from '{sender_filter}'...")
    
    start_time = time.time()
    
    while time.time() - start_time < max_wait_seconds:
        try:
            # Connect to Gmail
            mail = imaplib.IMAP4_SSL("imap.gmail.com")
            mail.login(gmail_address, gmail_password)
            mail.select("inbox")
            
            # Search for recent emails
            _, messages = mail.search(None, 'UNSEEN')
            email_ids = messages[0].split()
            
            # Check most recent emails
            for email_id in reversed(email_ids[-5:]):  # Last 5 unread
                _, msg_data = mail.fetch(email_id, "(RFC822)")
                raw_email = msg_data[0][1]
                msg = email.message_from_bytes(raw_email)
                
                # Check sender
                sender = msg["From"].lower()
                if sender_filter.lower() not in sender:
                    continue
                
                # Get email body
                body = ""
                if msg.is_multipart():
                    for part in msg.walk():
                        if part.get_content_type() == "text/plain":
                            body = part.get_payload(decode=True).decode()
                            break
                else:
                    body = msg.get_payload(decode=True).decode()
                
                # Extract OTP (usually 6 digits)
                otp_match = re.search(r'\b(\d{6})\b', body)
                if otp_match:
                    otp = otp_match.group(1)
                    print(f"🔑 Found OTP: {otp}")
                    mail.logout()
                    return otp
            
            mail.logout()
            
        except Exception as e:
            print(f"⚠️ Gmail error: {e}")
        
        # Wait before checking again
        print("⏳ No OTP yet, waiting 10 seconds...")
        time.sleep(10)
    
    print("❌ Timeout waiting for OTP email.")
    return None
