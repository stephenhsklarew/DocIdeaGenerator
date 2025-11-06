import os
import pickle
from typing import List, Dict, Optional
from datetime import datetime
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from dotenv import load_dotenv

load_dotenv()

# Scopes required for Drive and Docs access
SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/drive.readonly',
    'https://www.googleapis.com/auth/documents',  # For creating/editing Google Docs
    'https://www.googleapis.com/auth/drive.file'   # For creating files in Drive
]

class GoogleDriveClient:
    def __init__(self, folder_id: Optional[str] = None, credentials_path='token.pickle'):
        """
        Initialize Google Drive client using existing credentials

        Args:
            folder_id: Google Drive folder ID to scan (optional, can be set from env)
            credentials_path: Path to the credentials pickle file
        """
        self.service = None
        self.folder_id = folder_id or os.getenv('DRIVE_FOLDER_ID')
        self.recursive = os.getenv('DRIVE_RECURSIVE', 'false').lower() == 'true'
        self.load_credentials(credentials_path)

    def load_credentials(self, credentials_path):
        """Load or create credentials with OAuth flow"""
        creds = None

        # Load existing credentials if available
        if os.path.exists(credentials_path):
            with open(credentials_path, 'rb') as token:
                creds = pickle.load(token)

        # If credentials are invalid or don't exist, authenticate
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                # Refresh expired credentials
                creds.refresh(Request())
            else:
                # Run OAuth flow to get new credentials
                if not os.path.exists('credentials.json'):
                    raise FileNotFoundError(
                        "credentials.json not found. Please download it from Google Cloud Console.\n"
                        "See README for instructions."
                    )
                flow = InstalledAppFlow.from_client_secrets_file(
                    'credentials.json', SCOPES)
                creds = flow.run_local_server(port=0)

            # Save credentials for future use
            with open(credentials_path, 'wb') as token:
                pickle.dump(creds, token)

        self.service = build('drive', 'v3', credentials=creds)

    def get_documents_in_folder(
        self,
        folder_id: Optional[str] = None,
        name_pattern: Optional[str] = None,
        modified_after: Optional[str] = None
    ) -> List[Dict]:
        """
        Get all Google Docs in a specified folder

        Args:
            folder_id: Google Drive folder ID (uses self.folder_id if not provided)
            name_pattern: Optional substring to filter document names (case-insensitive)
            modified_after: Optional date filter in MMDDYYYY format

        Returns:
            List of dicts containing document metadata:
            - id: Document ID
            - name: Document name
            - modified: Last modified timestamp
            - created: Created timestamp
        """
        folder_id = folder_id or self.folder_id

        if not folder_id:
            raise ValueError(
                "No folder_id provided. Set DRIVE_FOLDER_ID in .env or pass folder_id parameter"
            )

        try:
            documents = []

            # Build query
            query_parts = [
                f"'{folder_id}' in parents",
                "mimeType='application/vnd.google-apps.document'",
                "trashed=false"
            ]

            # Add date filter if provided
            if modified_after:
                try:
                    dt = datetime.strptime(modified_after, '%m%d%Y')
                    date_str = dt.strftime('%Y-%m-%dT%H:%M:%S')
                    query_parts.append(f"modifiedTime >= '{date_str}'")
                except ValueError:
                    print(f"Warning: Invalid date format '{modified_after}'. Expected MMDDYYYY")

            query = ' and '.join(query_parts)

            # Fetch documents with pagination
            page_token = None
            while True:
                results = self.service.files().list(
                    q=query,
                    pageSize=100,
                    fields="nextPageToken, files(id, name, modifiedTime, createdTime)",
                    pageToken=page_token
                ).execute()

                items = results.get('files', [])

                # Apply name filter if provided
                for item in items:
                    if name_pattern:
                        if name_pattern.lower() not in item['name'].lower():
                            continue

                    documents.append({
                        'id': item['id'],
                        'name': item['name'],
                        'modified': item.get('modifiedTime', ''),
                        'created': item.get('createdTime', '')
                    })

                page_token = results.get('nextPageToken')
                if not page_token:
                    break

            # Sort by modified date (newest first)
            documents.sort(key=lambda x: x['modified'], reverse=True)

            return documents

        except HttpError as error:
            print(f'An error occurred accessing Drive folder: {error}')
            return []

    def get_documents_recursive(
        self,
        folder_id: Optional[str] = None,
        name_pattern: Optional[str] = None,
        modified_after: Optional[str] = None
    ) -> List[Dict]:
        """
        Get all Google Docs in a folder and its subfolders recursively

        Args:
            folder_id: Google Drive folder ID (uses self.folder_id if not provided)
            name_pattern: Optional substring to filter document names
            modified_after: Optional date filter in MMDDYYYY format

        Returns:
            List of dicts containing document metadata with folder path
        """
        folder_id = folder_id or self.folder_id

        if not folder_id:
            raise ValueError(
                "No folder_id provided. Set DRIVE_FOLDER_ID in .env or pass folder_id parameter"
            )

        all_documents = []
        folders_to_scan = [(folder_id, '')]  # (folder_id, path)

        while folders_to_scan:
            current_folder_id, current_path = folders_to_scan.pop(0)

            # Get documents in current folder
            docs = self.get_documents_in_folder(
                current_folder_id,
                name_pattern,
                modified_after
            )

            # Add folder path to each document
            for doc in docs:
                doc['folder_path'] = current_path
                all_documents.append(doc)

            # Find subfolders
            try:
                query = f"'{current_folder_id}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false"
                results = self.service.files().list(
                    q=query,
                    fields="files(id, name)"
                ).execute()

                for folder in results.get('files', []):
                    subfolder_path = f"{current_path}/{folder['name']}" if current_path else folder['name']
                    folders_to_scan.append((folder['id'], subfolder_path))

            except HttpError as error:
                print(f'Error scanning subfolders: {error}')

        # Sort by modified date (newest first)
        all_documents.sort(key=lambda x: x['modified'], reverse=True)

        return all_documents

    def list_documents(
        self,
        name_pattern: Optional[str] = None,
        modified_after: Optional[str] = None
    ) -> List[Dict]:
        """
        List documents using configured settings (recursive or not)

        Args:
            name_pattern: Optional substring to filter document names
            modified_after: Optional date filter in MMDDYYYY format

        Returns:
            List of document metadata dictionaries
        """
        if self.recursive:
            return self.get_documents_recursive(
                name_pattern=name_pattern,
                modified_after=modified_after
            )
        else:
            return self.get_documents_in_folder(
                name_pattern=name_pattern,
                modified_after=modified_after
            )

    def extract_folder_id_from_url(self, url: str) -> str:
        """
        Extract folder ID from a Google Drive folder URL

        Args:
            url: Google Drive folder URL (e.g., https://drive.google.com/drive/folders/FOLDER_ID)

        Returns:
            str: The folder ID
        """
        import re
        # Pattern: /folders/{FOLDER_ID}
        match = re.search(r'/folders/([a-zA-Z0-9-_]+)', url)
        if match:
            return match.group(1)
        return url  # Return as-is if not a URL pattern
