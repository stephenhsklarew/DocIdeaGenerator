import os
import pickle
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

class GoogleDocsClient:
    def __init__(self, credentials_path='token.pickle'):
        """Initialize Google Docs client using existing credentials"""
        self.service = None
        self.drive_service = None
        self.load_credentials(credentials_path)

    def load_credentials(self, credentials_path):
        """Load credentials from pickle file"""
        if not os.path.exists(credentials_path):
            raise FileNotFoundError(
                f"Credentials file '{credentials_path}' not found. "
                "Please authenticate with Gmail first."
            )

        with open(credentials_path, 'rb') as token:
            creds = pickle.load(token)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
                with open(credentials_path, 'wb') as token:
                    pickle.dump(creds, token)

        self.service = build('docs', 'v1', credentials=creds)
        self.drive_service = build('drive', 'v3', credentials=creds)

    def get_plain_document_content(self, document_id: str) -> str:
        """
        Fetch text content from a plain Google Doc (no tabs).
        Optimized for documents without tab structure (e.g., from Drive folders).

        Args:
            document_id: The ID of the Google Doc

        Returns:
            str: The full text content of the document
        """
        try:
            # Get document without tabs content for better performance
            document = self.service.documents().get(
                documentId=document_id
            ).execute()

            # Extract content from document body
            doc_content = document.get('body', {}).get('content', [])
            all_content = self._extract_content_from_elements(doc_content)

            return ''.join(all_content)

        except HttpError as error:
            print(f'An error occurred fetching document {document_id}: {error}')
            return ''

    def get_document_content(self, document_id: str, prefer_transcript: bool = True) -> str:
        """
        Fetch the text content from a Google Doc.
        Prefers the 'Transcript' tab if available, falls back to 'Notes' tab.

        Args:
            document_id: The ID of the Google Doc
            prefer_transcript: If True, prefer the Transcript tab over Notes tab (default: True)

        Returns:
            str: The full text content of the transcript or notes
        """
        try:
            # Get document with tabs content
            document = self.service.documents().get(
                documentId=document_id,
                includeTabsContent=True
            ).execute()

            all_content = []

            # Check if document has tabs (newer format)
            if 'tabs' in document:
                transcript_tab = None
                notes_tab = None

                # Find Transcript and Notes tabs
                for tab in document['tabs']:
                    tab_title = tab.get('tabProperties', {}).get('title', '')

                    if tab_title.lower() == 'transcript':
                        transcript_tab = tab
                    elif tab_title.lower() == 'notes':
                        notes_tab = tab

                # Prefer Transcript tab if available, otherwise use Notes tab
                selected_tab = None
                if prefer_transcript and transcript_tab:
                    selected_tab = transcript_tab
                    print(f'  → Processing Transcript Tab')
                elif notes_tab:
                    selected_tab = notes_tab
                    if transcript_tab:
                        print(f'  → Using Notes tab (Transcript tab exists but prefer_transcript=False)')
                    else:
                        print(f'  → Using Notes tab (no Transcript tab available)')

                if selected_tab:
                    doc_content = selected_tab.get('documentTab', {}).get('body', {}).get('content', [])
                    all_content.extend(self._extract_content_from_elements(doc_content))
                else:
                    # No Transcript or Notes tab found, use first tab
                    print(f'Warning: Neither Transcript nor Notes tab found. Available tabs:')
                    for tab in document['tabs']:
                        tab_title = tab.get('tabProperties', {}).get('title', 'Untitled')
                        print(f'  - {tab_title}')
                    print('Using first tab as fallback...')

                    first_tab = document['tabs'][0]
                    doc_content = first_tab.get('documentTab', {}).get('body', {}).get('content', [])
                    all_content.extend(self._extract_content_from_elements(doc_content))
            else:
                # Legacy format (no tabs)
                doc_content = document.get('body', {}).get('content', [])
                all_content.extend(self._extract_content_from_elements(doc_content))

            return ''.join(all_content)

        except HttpError as error:
            print(f'An error occurred fetching document {document_id}: {error}')
            return ''

    def _extract_content_from_elements(self, elements):
        """Helper method to extract text from document elements"""
        content = []

        for element in elements:
            if 'paragraph' in element:
                paragraph = element['paragraph']
                for text_run in paragraph.get('elements', []):
                    if 'textRun' in text_run:
                        content.append(text_run['textRun']['content'])
            elif 'table' in element:
                # Handle tables
                table = element['table']
                for row in table.get('tableRows', []):
                    for cell in row.get('tableCells', []):
                        for cell_element in cell.get('content', []):
                            if 'paragraph' in cell_element:
                                for text_run in cell_element['paragraph'].get('elements', []):
                                    if 'textRun' in text_run:
                                        content.append(text_run['textRun']['content'])

        return content

    def extract_doc_id_from_url(self, url: str) -> str:
        """
        Extract document ID from a Google Docs URL

        Args:
            url: Google Docs URL (e.g., https://docs.google.com/document/d/DOCUMENT_ID/edit)

        Returns:
            str: The document ID
        """
        import re
        # Pattern: /document/d/{DOCUMENT_ID}/
        match = re.search(r'/document/d/([a-zA-Z0-9-_]+)', url)
        if match:
            return match.group(1)
        return url  # Return as-is if not a URL pattern

    def create_document(self, title: str, content: str, folder_id: str = None) -> dict:
        """
        Create a new Google Doc with markdown-formatted content converted to proper formatting

        Args:
            title: Document title
            content: Markdown content to convert and insert
            folder_id: Optional Google Drive folder ID to place the document

        Returns:
            dict: Document metadata with 'id' and 'url'
        """
        try:
            # Create a new document
            doc = self.service.documents().create(body={'title': title}).execute()
            doc_id = doc.get('documentId')

            # Parse markdown and generate formatting requests
            requests = self._convert_markdown_to_docs_requests(content)

            # Apply all formatting in a single batch
            if requests:
                self.service.documents().batchUpdate(
                    documentId=doc_id,
                    body={'requests': requests}
                ).execute()

            # Move to folder if specified
            if folder_id:
                self._move_to_folder(doc_id, folder_id)

            doc_url = f"https://docs.google.com/document/d/{doc_id}/edit"

            return {
                'id': doc_id,
                'url': doc_url,
                'title': title
            }

        except HttpError as error:
            print(f'An error occurred creating document: {error}')
            return None

    def _convert_markdown_to_docs_requests(self, content: str) -> list:
        """
        Convert markdown content to Google Docs API formatting requests

        Args:
            content: Markdown-formatted string

        Returns:
            list: Google Docs API requests for formatted content
        """
        import re

        requests = []
        lines = content.split('\n')
        current_index = 1  # Google Docs index starts at 1

        # First pass: Insert all text
        full_text = []
        formatting_map = []  # Track (start_index, end_index, format_type, level)

        for line in lines:
            line_start = len(''.join(full_text))

            # Check for headers
            if line.startswith('## '):
                clean_line = line[3:] + '\n'
                full_text.append(clean_line)
                formatting_map.append((line_start, line_start + len(clean_line) - 1, 'heading', 2))
            elif line.startswith('# '):
                clean_line = line[2:] + '\n'
                full_text.append(clean_line)
                formatting_map.append((line_start, line_start + len(clean_line) - 1, 'heading', 1))
            # Check for horizontal rules (skip them or convert to line break)
            elif line.strip() == '---' or line.strip().startswith('────'):
                full_text.append('\n')
            else:
                # Handle inline formatting (bold, quotes, bullets)
                processed_line = line + '\n'

                # Track bold formatting
                bold_pattern = r'\*\*([^*]+)\*\*'
                for match in re.finditer(bold_pattern, line):
                    # Calculate position in full text
                    match_start = line_start + match.start()
                    match_end = line_start + match.end() - 4  # Subtract the ** markers
                    formatting_map.append((match_start, match_end, 'bold', None))

                # Remove markdown syntax for the actual text
                processed_line = re.sub(r'\*\*([^*]+)\*\*', r'\1', processed_line)

                # Handle blockquotes (lines starting with >)
                if line.strip().startswith('>'):
                    processed_line = '    ' + processed_line.lstrip('> ')  # Indent instead

                # Handle bullet points (lines starting with •)
                if line.strip().startswith('•'):
                    # Keep the bullet
                    pass

                full_text.append(processed_line)

        full_text_str = ''.join(full_text)

        # Insert all text at once
        requests.append({
            'insertText': {
                'location': {'index': 1},
                'text': full_text_str
            }
        })

        # Apply formatting (must be done after text insertion)
        # Sort by start position (descending) to apply from end to start
        formatting_map.sort(key=lambda x: x[0], reverse=True)

        for start_idx, end_idx, format_type, level in formatting_map:
            # Adjust indices (Google Docs is 1-indexed)
            start_idx += 1
            end_idx += 1

            if format_type == 'heading':
                requests.append({
                    'updateParagraphStyle': {
                        'range': {
                            'startIndex': start_idx,
                            'endIndex': end_idx
                        },
                        'paragraphStyle': {
                            'namedStyleType': f'HEADING_{level}'
                        },
                        'fields': 'namedStyleType'
                    }
                })
            elif format_type == 'bold':
                requests.append({
                    'updateTextStyle': {
                        'range': {
                            'startIndex': start_idx,
                            'endIndex': end_idx
                        },
                        'textStyle': {
                            'bold': True
                        },
                        'fields': 'bold'
                    }
                })

        return requests

    def _move_to_folder(self, document_id: str, folder_id: str):
        """
        Move a document to a specific folder

        Args:
            document_id: The ID of the document to move
            folder_id: The ID of the destination folder
        """
        try:
            # Get the file's current parents
            file = self.drive_service.files().get(
                fileId=document_id,
                fields='parents'
            ).execute()

            previous_parents = ",".join(file.get('parents', []))

            # Move the file to the new folder
            self.drive_service.files().update(
                fileId=document_id,
                addParents=folder_id,
                removeParents=previous_parents,
                fields='id, parents'
            ).execute()

        except HttpError as error:
            print(f'An error occurred moving document to folder: {error}')
