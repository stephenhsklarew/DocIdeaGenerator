import os
import pickle
import re
from datetime import datetime
from typing import List, Dict, Optional
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import base64
from dotenv import load_dotenv
from google_docs_client import GoogleDocsClient

load_dotenv()

SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/drive.readonly',
    'https://www.googleapis.com/auth/documents',  # For creating/editing Google Docs
    'https://www.googleapis.com/auth/drive.file'   # For creating files in Drive
]

class GmailClient:
    def __init__(self, start_date: Optional[str] = None, label: Optional[str] = None):
        self.service = None
        self.start_date = start_date or os.getenv('START_DATE')
        self.label = label
        self.docs_client = None
        self.authenticate()

    def authenticate(self):
        """Authenticate with Gmail API"""
        creds = None

        if os.path.exists('token.pickle'):
            with open('token.pickle', 'rb') as token:
                creds = pickle.load(token)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not os.path.exists('credentials.json'):
                    raise FileNotFoundError(
                        "credentials.json not found. Please download it from Google Cloud Console.\n"
                        "See README for instructions."
                    )
                flow = InstalledAppFlow.from_client_secrets_file(
                    'credentials.json', SCOPES)
                creds = flow.run_local_server(port=0)

            with open('token.pickle', 'wb') as token:
                pickle.dump(creds, token)

        self.service = build('gmail', 'v1', credentials=creds)
        # Initialize Google Docs client with same credentials
        try:
            self.docs_client = GoogleDocsClient()
        except Exception as e:
            print(f"Warning: Could not initialize Google Docs client: {e}")

    def parse_subject_line(self, subject: str) -> Optional[Dict[str, str]]:
        """Parse subject line matching pattern: Notes: "Topic" MMM DD, YYYY"""
        # Pattern for Gemini format: Notes: "Topic" Oct 23, 2025
        # Support both straight quotes (") and curly quotes ("")
        # U+201C = " (left double quotation mark)
        # U+201D = " (right double quotation mark)
        pattern = r'^Notes:\s*["""\u201C]([^"""\u201C\u201D]+)["""\u201D]\s+([A-Za-z]+\s+\d{1,2},\s+\d{4})'
        match = re.match(pattern, subject)

        if match:
            return {
                'topic': match.group(1),
                'date': match.group(2)
            }
        return None

    def _parse_start_date(self) -> Optional[datetime]:
        """Parse START_DATE from MMDDYYYY format to datetime"""
        if not self.start_date:
            return None

        try:
            # Parse MMDDYYYY format
            return datetime.strptime(self.start_date, '%m%d%Y')
        except ValueError:
            print(f"Warning: Invalid START_DATE format '{self.start_date}'. Expected MMDDYYYY (e.g., 10232025)")
            return None

    def _build_date_query(self) -> str:
        """Build Gmail search query with date filter, sender filter, and optional label filter"""
        query = 'subject:"Notes:" from:gemini-notes@google.com'

        # Add label filter to query if specified
        # Use Gmail's label search to narrow results at the API level
        if self.label:
            # Normalize label name: replace hyphens/underscores with spaces
            label_normalized = self.label.replace('-', ' ').replace('_', ' ')
            # Quote the label if it contains spaces
            if ' ' in label_normalized:
                query += f' label:"{label_normalized}"'
            else:
                query += f' label:{label_normalized}'
            # When filtering by label, don't add date filter
            # This allows finding labeled emails regardless of date
        else:
            # Only add date filter if no label is specified
            start_dt = self._parse_start_date()
            if start_dt:
                # Gmail uses YYYY/MM/DD format for date queries
                date_str = start_dt.strftime('%Y/%m/%d')
                query += f' after:{date_str}'

        return query

    def get_transcripts(self, max_results: int = 50) -> List[Dict]:
        """Fetch emails with subject lines matching the transcript pattern"""
        try:
            query = self._build_date_query()

            results = self.service.users().messages().list(
                userId='me',
                q=query,
                maxResults=max_results
            ).execute()

            messages = results.get('messages', [])
            transcripts = []

            for message in messages:
                msg_data = self.service.users().messages().get(
                    userId='me',
                    id=message['id'],
                    format='full'
                ).execute()

                # Gmail API has already filtered by label in the query, so no need to verify again

                headers = msg_data['payload']['headers']
                subject = next((h['value'] for h in headers if h['name'] == 'Subject'), '')

                parsed = self.parse_subject_line(subject)
                if not parsed:
                    continue

                # Extract Google Docs link from email body
                email_body = self._get_message_body(msg_data)
                doc_id = self._extract_google_doc_id(email_body)

                if doc_id and self.docs_client:
                    # Fetch transcript content from Google Doc
                    transcript_content = self.docs_client.get_document_content(doc_id)
                    if transcript_content:
                        transcripts.append({
                            'id': message['id'],
                            'subject': subject,
                            'topic': parsed['topic'],
                            'date': parsed['date'],
                            'body': transcript_content,
                            'doc_id': doc_id
                        })
                elif email_body:
                    # Fallback to email body if no doc found
                    transcripts.append({
                        'id': message['id'],
                        'subject': subject,
                        'topic': parsed['topic'],
                        'date': parsed['date'],
                        'body': email_body
                    })

            return transcripts

        except HttpError as error:
            print(f'An error occurred: {error}')
            return []

    def _email_has_label(self, label_ids: List[str], target_label: str) -> bool:
        """
        Check if an email has a specific label by comparing label names.

        Args:
            label_ids: List of label IDs from the email
            target_label: The label name to search for (case-insensitive)
                         Can use spaces or hyphens (e.g., "Blog potential" or "blog-potential")

        Returns:
            bool: True if the email has the label, False otherwise
        """
        try:
            # Get all labels for the user (cached to avoid repeated API calls)
            if not hasattr(self, '_label_cache'):
                labels_result = self.service.users().labels().list(userId='me').execute()
                self._label_cache = {label['id']: label['name'] for label in labels_result.get('labels', [])}

            # Normalize target label: convert to lowercase and normalize separators
            target_normalized = target_label.lower().replace('-', ' ').replace('_', ' ')

            # Check if any of the email's labels match the target label (case-insensitive)
            for label_id in label_ids:
                label_name = self._label_cache.get(label_id, '')
                label_normalized = label_name.lower().replace('-', ' ').replace('_', ' ')

                if label_normalized == target_normalized:
                    return True

            return False

        except Exception as e:
            print(f'Error checking labels: {e}')
            return False  # If there's an error, skip the label check

    def _get_message_body(self, message: Dict) -> str:
        """Extract the message body from the email (text and HTML)"""
        try:
            if 'parts' in message['payload']:
                parts = message['payload']['parts']
                body = ''
                for part in parts:
                    # Get both plain text and HTML
                    if part['mimeType'] in ['text/plain', 'text/html']:
                        if 'data' in part['body']:
                            decoded = base64.urlsafe_b64decode(
                                part['body']['data']
                            ).decode('utf-8', errors='ignore')
                            body += decoded + '\n\n'
                    elif 'parts' in part:
                        body += self._extract_nested_parts(part['parts'])
                return body
            else:
                if 'data' in message['payload']['body']:
                    return base64.urlsafe_b64decode(
                        message['payload']['body']['data']
                    ).decode('utf-8', errors='ignore')
        except Exception as e:
            print(f"Error extracting body: {e}")
        return ''

    def _extract_nested_parts(self, parts: List) -> str:
        """Recursively extract text from nested email parts"""
        body = ''
        for part in parts:
            if part['mimeType'] == 'text/plain' and 'data' in part['body']:
                body += base64.urlsafe_b64decode(
                    part['body']['data']
                ).decode('utf-8')
            elif 'parts' in part:
                body += self._extract_nested_parts(part['parts'])
        return body

    def _extract_google_doc_id(self, email_body: str) -> Optional[str]:
        """
        Extract Google Docs document ID from email body

        Args:
            email_body: The email body text

        Returns:
            str: Document ID if found, None otherwise
        """
        if not email_body:
            return None

        # Pattern for Google Docs URLs
        # https://docs.google.com/document/d/DOCUMENT_ID/edit
        pattern = r'https://docs\.google\.com/document/d/([a-zA-Z0-9-_]+)'
        match = re.search(pattern, email_body)

        if match:
            return match.group(1)

        return None
