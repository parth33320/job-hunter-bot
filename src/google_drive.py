"""Download resumes from Google Drive."""
import io
import os
from pathlib import Path
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

from src.config import CONFIG

SCOPES = ['https://www.googleapis.com/auth/drive.readonly']
TEMP_DIR = Path(__file__).parent.parent / "temp_downloads"
TEMP_DIR.mkdir(exist_ok=True)

def get_drive_service():
    """Create authenticated Drive service."""
    credentials = service_account.Credentials.from_service_account_info(
        CONFIG['secrets']['service_account'],
        scopes=SCOPES
    )
    return build('drive', 'v3', credentials=credentials)

def list_resumes() -> list[dict]:
    """List all files in the Resumes folder."""
    service = get_drive_service()
    folder_id = CONFIG['secrets']['google_drive_folder_id']
    
    results = service.files().list(
        q=f"'{folder_id}' in parents and trashed=false",
        fields="files(id, name, mimeType)"
    ).execute()
    
    files = results.get('files', [])
    print(f"📁 Found {len(files)} files in Google Drive:")
    for f in files:
        print(f"   - {f['name']}")
    return files

def download_resume(filename: str) -> str | None:
    """Download a specific resume to temp folder. Returns local path."""
    service = get_drive_service()
    folder_id = CONFIG['secrets']['google_drive_folder_id']
    
    # Find the file
    results = service.files().list(
        q=f"'{folder_id}' in parents and name='{filename}' and trashed=false",
        fields="files(id, name)"
    ).execute()
    
    files = results.get('files', [])
    if not files:
        print(f"❌ File not found in Drive: {filename}")
        return None
    
    file_id = files[0]['id']
    file_name = files[0]['name']
    
    # Download
    request = service.files().get_media(fileId=file_id)
    local_path = TEMP_DIR / file_name
    
    with open(local_path, 'wb') as f:
        downloader = MediaIoBaseDownload(f, request)
        done = False
        while not done:
            status, done = downloader.next_chunk()
    
    print(f"📥 Downloaded: {file_name} -> {local_path}")
    return str(local_path)

def cleanup_temp():
    """Delete downloaded files after use."""
    for file in TEMP_DIR.iterdir():
        file.unlink()
    print("🧹 Cleaned up temp downloads.")
