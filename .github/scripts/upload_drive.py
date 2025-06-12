import os
import json
import kotobase
from pathlib import Path
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# Load credentials from the environment variable (via GitHub secret)
creds_json = json.loads(os.environ['GCP_SA_KEY'])
creds = Credentials.from_service_account_info(
    creds_json,
    scopes=['https://www.googleapis.com/auth/drive'])
service = build('drive', 'v3', credentials=creds)
# Get metadata from environment variables
file_id = os.environ['DRIVE_FILE_ID']
db_dir = Path(kotobase.__file__).parent / 'db'
file_path = str(db_dir / 'kotobase.db')
file_metadata = {'name': os.path.basename(file_path)}
media = MediaFileUpload(file_path, mimetype='application/x-sqlite3')

# Update the existing file on Google Drive
print(f'Uploading {file_path} to Google Drive file ID {file_id}...')
updated_file = service.files().update(fileId=file_id,
                                      media_body=media,
                                      fields='id'
                                      ).execute()
print(f'Upload complete. File ID: {updated_file.get("id")}')
