import os
import re
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2 import service_account

def upload_resume_to_drive(pdf_path: str, company: str, role: str, service_account_path: str) -> dict:
    """
    Uploads a tailored resume PDF directly to Google Drive.
    If DRIVE_FOLDER_ID is set in the environment, it uploads to that folder.
    Otherwise, it uploads to the root of the service account's Drive.
    """
    try:
        # 1. Try to load OAuth2 token.json first (which uses the user's personal account quota)
        token_path = os.path.abspath(os.path.join(os.path.dirname(service_account_path), "token.json"))
        creds = None
        
        if os.path.exists(token_path):
            try:
                import json
                from google.oauth2.credentials import Credentials
                with open(token_path, 'r') as f:
                    creds = Credentials.from_authorized_user_info(
                        json.load(f),
                        scopes=['https://www.googleapis.com/auth/drive']
                    )
                print("Using OAuth2 personal credentials (token.json) for upload.")
            except Exception as token_err:
                print(f"Failed to load token.json, falling back: {token_err}")
                creds = None
                
        # 2. Fall back to Service Account credentials
        if not creds:
            if not os.path.exists(service_account_path):
                raise FileNotFoundError(f"Service account key not found at {service_account_path}")
            creds = service_account.Credentials.from_service_account_file(
                service_account_path,
                scopes=['https://www.googleapis.com/auth/drive']
            )
            print("Using Service Account credentials for upload.")
            
        drive_service = build('drive', 'v3', credentials=creds, cache_discovery=False)
        
        folder_id = os.getenv("DRIVE_FOLDER_ID", "").strip()
        if not folder_id:
            raise ValueError(
                "DRIVE_FOLDER_ID is not configured in your .env file. "
                "Since Google Service Accounts have 0 bytes of default storage quota, you must: "
                "1. Create a folder in your personal Google Drive. "
                "2. Share it with your service account email as an Editor. "
                "3. Set DRIVE_FOLDER_ID in your .env."
            )
        
        # 3. Query existing tailored resumes to calculate version number
        query = f"'{folder_id}' in parents and name contains 'Resume_v' and mimeType = 'application/pdf' and trashed = false"
            
        file_results = drive_service.files().list(
            q=query, 
            spaces='drive', 
            fields='files(name)',
            pageSize=100
        ).execute()
        files = file_results.get('files', [])
        
        highest_version = 0
        for f in files:
            name = f.get('name', '')
            match = re.search(r'Resume_v(\d+)', name)
            if match:
                val = int(match.group(1))
                if val > highest_version:
                    highest_version = val
                    
        next_version = highest_version + 1
        version_label = f"Resume_v{next_version}"
        
        # 4. Form clean filename
        clean_company = re.sub(r'[\\/*?:"<>| ]', '_', company)
        clean_role = re.sub(r'[\\/*?:"<>| ]', '_', role)
        filename = f"{version_label}_{clean_company}_{clean_role}.pdf"
        
        # 5. Form metadata
        file_metadata = {
            'name': filename,
            'parents': [folder_id]
        }
            
        # 6. Upload file
        media = MediaFileUpload(pdf_path, mimetype='application/pdf')
        uploaded_file = drive_service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id, webViewLink'
        ).execute()
        
        # 7. Make the file readable by anyone with the link
        try:
            drive_service.permissions().create(
                fileId=uploaded_file.get('id'),
                body={'type': 'anyone', 'role': 'reader'}
            ).execute()
            # Fetch updated link with permissions applied
            uploaded_file = drive_service.files().get(
                fileId=uploaded_file.get('id'),
                fields='id, webViewLink'
            ).execute()
        except Exception as perm_err:
            # Non-blocking error: might fail if permissions cannot be set, but continue
            print(f"Non-blocking permission setup error: {perm_err}")
            
        return {
            'success': True,
            'version_label': version_label,
            'filename': filename,
            'file_id': uploaded_file.get('id'),
            'drive_link': uploaded_file.get('webViewLink')
        }
    except ValueError as val_err:
        return {
            'success': False,
            'error': str(val_err)
        }
    except Exception as e:
        err_msg = str(e)
        if "storageQuotaExceeded" in err_msg or "storage quota" in err_msg.lower():
            err_msg = (
                "Google Drive storage quota error. Google Service Accounts have 0 bytes of "
                "allocated storage by default and cannot upload directly to personal 'My Drive' folders. "
                "To resolve this, you must either:\n"
                "1. (Recommended for personal Gmail): Set up OAuth2 Desktop credentials (credentials.json) "
                "so the application generates a 'token.json' and uploads files using your personal account quota.\n"
                "2. (Workspace accounts only): Create a Shared Drive in your domain, add your service account email "
                "as a member (Content Manager), and set DRIVE_FOLDER_ID in .env to the Shared Drive folder ID."
            )
        return {
            'success': False,
            'error': err_msg
        }
