import os
import io
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

# Define the scopes required for Google Drive API
SCOPES = ['https://www.googleapis.com/auth/drive.readonly']

def get_drive_service(creds_dict):
    """
    Authenticate and return the Google Drive service object.
    creds_dict should be a dictionary representing the Service Account JSON.
    """
    try:
        credentials = service_account.Credentials.from_service_account_info(
            creds_dict, scopes=SCOPES)
        service = build('drive', 'v3', credentials=credentials)
        return service
    except Exception as e:
        print(f"Error authenticating with Google Drive: {e}")
        return None

def download_pdfs_from_folder(service, folder_id, download_path):
    """
    Downloads all PDF files from a specific Google Drive folder.
    """
    try:
        if not os.path.exists(download_path):
            os.makedirs(download_path)
            
        # Query to get all PDF files in the specified folder
        query = f"'{folder_id}' in parents and mimeType='application/pdf' and trashed=false"
        
        # Paginate through results if there are many files
        page_token = None
        downloaded_files = 0
        
        while True:
            response = service.files().list(
                q=query,
                spaces='drive',
                fields='nextPageToken, files(id, name)',
                pageToken=page_token
            ).execute()
            
            files = response.get('files', [])
            
            for file in files:
                file_id = file.get('id')
                file_name = file.get('name')
                
                print(f"Downloading: {file_name}")
                
                request = service.files().get_media(fileId=file_id)
                file_path = os.path.join(download_path, file_name)
                
                with io.FileIO(file_path, 'wb') as fh:
                    downloader = MediaIoBaseDownload(fh, request)
                    finished = False
                    while finished is False:
                        status, finished = downloader.next_chunk()
                downloaded_files += 1
                
            page_token = response.get('nextPageToken', None)
            if page_token is None:
                break
                
        return True, f"{downloaded_files} PDFs baixados com sucesso."
    
    except Exception as e:
        error_msg = f"Erro ao baixar do Google Drive: {e}"
        print(error_msg)
        return False, error_msg

def clear_directory(directory_path):
    """Deletes all files in a directory."""
    if os.path.exists(directory_path):
        for filename in os.listdir(directory_path):
            file_path = os.path.join(directory_path, filename)
            try:
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.unlink(file_path)
            except Exception as e:
                print(f'Failed to delete {file_path}. Reason: {e}')
