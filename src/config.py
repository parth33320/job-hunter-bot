"""Load configuration from yaml and environment variables."""
import os
import yaml
from pathlib import Path
from dotenv import load_dotenv

# Load .env file if running locally
load_dotenv()

def load_config():
    """Load config.yaml and merge with environment secrets."""
    
    # Find config.yaml
    config_path = Path(__file__).parent.parent / "config.yaml"
    
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    # Add secrets from environment
    config['secrets'] = {
        'google_api_key': os.getenv('GOOGLE_API_KEY'),
        'google_cx': os.getenv('GOOGLE_CX'),
        'gmail_address': os.getenv('GMAIL_ADDRESS'),
        'gmail_app_password': os.getenv('GMAIL_APP_PASSWORD'),
        'ntfy_alert_topic': os.getenv('NTFY_ALERT_TOPIC'),
        'ntfy_command_topic': os.getenv('NTFY_COMMAND_TOPIC'),
        'google_drive_folder_id': os.getenv('GOOGLE_DRIVE_FOLDER_ID'),
    }
    
    # Load service account JSON (from env or file)
    sa_json = os.getenv('GOOGLE_SERVICE_ACCOUNT_JSON')
    if sa_json:
        import json
        config['secrets']['service_account'] = json.loads(sa_json)
    else:
        # Try loading from file
        sa_path = Path(__file__).parent.parent / "service_account.json"
        if sa_path.exists():
            import json
            with open(sa_path) as f:
                config['secrets']['service_account'] = json.load(f)
    
    return config

CONFIG = load_config()
