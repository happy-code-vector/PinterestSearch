"""
Google Drive Uploader Module
Uploads scraped Pinterest content to Google Drive with proper folder structure.
"""

import os
import logging
from pathlib import Path
from typing import Optional, Dict
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import pickle

logger = logging.getLogger(__name__)

# Scopes for Google Drive API
SCOPES = ['https://www.googleapis.com/auth/drive']


class DriveUploader:
    """Handle Google Drive uploads with proper folder structure."""

    def __init__(self, credentials_path: str = 'credentials.json', token_path: str = 'token.pkl'):
        """
        Initialize Drive uploader.

        Args:
            credentials_path: Path to OAuth 2.0 credentials JSON from Google Cloud Console
            token_path: Path to store authenticated token
        """
        self.credentials_path = credentials_path
        self.token_path = token_path
        self.service = None
        self.folder_cache: Dict[str, str] = {}  # Cache folder IDs

    def authenticate(self) -> bool:
        """
        Authenticate with Google Drive API.

        Returns:
            True if authentication successful, False otherwise
        """
        creds = None

        # Load existing token if available
        if os.path.exists(self.token_path):
            try:
                with open(self.token_path, 'rb') as token:
                    creds = pickle.load(token)
                logger.info("Loaded existing credentials from token")
            except Exception as e:
                logger.warning(f"Could not load token: {e}")

        # If no valid credentials, get new ones
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                    logger.info("Refreshed expired credentials")
                except Exception as e:
                    logger.error(f"Failed to refresh credentials: {e}")
                    creds = None

            if not creds:
                if not os.path.exists(self.credentials_path):
                    logger.error(f"Credentials file not found: {self.credentials_path}")
                    logger.error("Please download credentials.json from Google Cloud Console")
                    return False

                try:
                    flow = InstalledAppFlow.from_client_secrets_file(
                        self.credentials_path, SCOPES
                    )
                    creds = flow.run_local_server(port=0)
                    logger.info("Authenticated via OAuth flow")
                except Exception as e:
                    logger.error(f"Authentication failed: {e}")
                    return False

            # Save credentials for future use
            with open(self.token_path, 'wb') as token:
                pickle.dump(creds, token)

        try:
            self.service = build('drive', 'v3', credentials=creds)
            logger.info("Google Drive service initialized successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to build Drive service: {e}")
            return False

    def find_or_create_folder(self, folder_name: str, parent_id: Optional[str] = None) -> Optional[str]:
        """
        Find existing folder or create new one.

        Args:
            folder_name: Name of the folder
            parent_id: Parent folder ID (None for root level in target folder)

        Returns:
            Folder ID if successful, None otherwise
        """
        # Check cache first
        cache_key = f"{parent_id}/{folder_name}" if parent_id else f"root/{folder_name}"
        if cache_key in self.folder_cache:
            return self.folder_cache[cache_key]

        try:
            # Search for existing folder
            query = f"mimeType='application/vnd.google-apps.folder' and name='{folder_name}' and trashed=false"
            if parent_id:
                query += f" and '{parent_id}' in parents"

            results = self.service.files().list(q=query, fields="files(id, name)").execute()
            folders = results.get('files', [])

            if folders:
                folder_id = folders[0]['id']
                logger.debug(f"Found existing folder: {folder_name} ({folder_id})")
                self.folder_cache[cache_key] = folder_id
                return folder_id

            # Create new folder
            folder_metadata = {
                'name': folder_name,
                'mimeType': 'application/vnd.google-apps.folder'
            }
            if parent_id:
                folder_metadata['parents'] = [parent_id]

            folder = self.service.files().create(body=folder_metadata, fields='id').execute()
            folder_id = folder.get('id')
            logger.info(f"Created new folder: {folder_name} ({folder_id})")
            self.folder_cache[cache_key] = folder_id
            return folder_id

        except Exception as e:
            logger.error(f"Failed to find/create folder '{folder_name}': {e}")
            return None

    def upload_file(self, file_path: Path, folder_id: str, file_name: Optional[str] = None) -> bool:
        """
        Upload a file to Google Drive.

        Args:
            file_path: Local path to the file
            folder_id: Destination folder ID in Drive
            file_name: Optional custom name (defaults to file_path name)

        Returns:
            True if successful, False otherwise
        """
        if not file_path.exists():
            logger.warning(f"File not found: {file_path}")
            return False

        name = file_name or file_path.name

        try:
            # Check if file already exists
            query = f"name='{name}' and '{folder_id}' in parents and trashed=false"
            results = self.service.files().list(q=query, fields="files(id, name)").execute()
            existing = results.get('files', [])

            if existing:
                logger.debug(f"File already exists in Drive: {name}")
                return True

            # Upload file
            media = MediaFileUpload(str(file_path), resumable=True)

            file_metadata = {
                'name': name,
                'parents': [folder_id]
            }

            logger.info(f"Uploading: {name}")
            self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id'
            ).execute()

            logger.debug(f"Successfully uploaded: {name}")
            return True

        except Exception as e:
            logger.error(f"Failed to upload '{name}': {e}")
            return False

    def upload_category(self, category_path: Path, parent_folder_id: str) -> bool:
        """
        Upload an entire category folder with all subcategories.

        Args:
            category_path: Local path to category folder
            parent_folder_id: Google Drive parent folder ID

        Returns:
            True if successful, False otherwise
        """
        if not category_path.exists() or not category_path.is_dir():
            logger.warning(f"Category folder not found: {category_path}")
            return False

        category_name = category_path.name
        logger.info(f"Processing category: {category_name}")

        # Create or find category folder in Drive
        category_folder_id = self.find_or_create_folder(category_name, parent_folder_id)
        if not category_folder_id:
            return False

        success_count = 0
        fail_count = 0

        # Upload each subcategory (topic)
        for topic_path in category_path.iterdir():
            if not topic_path.is_dir():
                # Upload JSON files directly to category folder
                if topic_path.suffix == '.json':
                    if self.upload_file(topic_path, category_folder_id):
                        success_count += 1
                    else:
                        fail_count += 1
                continue

            topic_name = topic_path.name

            # Create or find topic subfolder in Drive
            topic_folder_id = self.find_or_create_folder(topic_name, category_folder_id)
            if not topic_folder_id:
                fail_count += 1
                continue

            # Upload all files in topic folder
            for item in topic_path.rglob('*'):
                if item.is_file():
                    if self.upload_file(item, topic_folder_id):
                        success_count += 1
                    else:
                        fail_count += 1

        logger.info(f"Category '{category_name}' complete: {success_count} uploaded, {fail_count} failed")
        return fail_count == 0

    def upload_all(self, base_path: Path, target_folder_id: str) -> Dict[str, bool]:
        """
        Upload all categories to Google Drive.

        Args:
            base_path: Base local path containing category folders
            target_folder_id: Google Drive folder ID to upload to

        Returns:
            Dictionary mapping category names to success status
        """
        if not self.service:
            logger.error("Not authenticated. Call authenticate() first.")
            return {}

        if not base_path.exists():
            logger.error(f"Base path not found: {base_path}")
            return {}

        results = {}

        for category_path in base_path.iterdir():
            if category_path.is_dir() and not category_path.name.startswith('.'):
                category_name = category_path.name
                results[category_name] = self.upload_category(category_path, target_folder_id)

        return results


def get_folder_id_from_url(folder_url: str) -> str:
    """
    Extract folder ID from Google Drive folder URL.

    Args:
        folder_url: Google Drive folder URL

    Returns:
        Folder ID string

    Examples:
        https://drive.google.com/drive/folders/1C9WuerzHjYkV5gka6EsB1p9_1bRlAPZy
        Returns: 1C9WuerzHjYkV5gka6EsB1p9_1bRlAPZy
    """
    # Extract ID from URL
    # Handles various Google Drive URL formats
    if '/folders/' in folder_url:
        return folder_url.split('/folders/')[-1].split('?')[0]
    elif '?id=' in folder_url:
        return folder_url.split('?id=')[-1].split('&')[0]
    else:
        # Assume it's already an ID
        return folder_url.strip('/')


if __name__ == "__main__":
    # Test the uploader
    import sys

    logging.basicConfig(level=logging.INFO)

    uploader = DriveUploader()

    if not uploader.authenticate():
        print("Authentication failed!")
        sys.exit(1)

    # Example usage
    folder_url = "https://drive.google.com/drive/folders/1C9WuerzHjYkV5gka6EsB1p9_1bRlAPZy"
    target_id = get_folder_id_from_url(folder_url)

    print(f"Target folder ID: {target_id}")

    # Upload all categories
    base_path = Path("pinterest_downloads")
    results = uploader.upload_all(base_path, target_id)

    print("\nUpload Summary:")
    for category, success in results.items():
        status = "✓ Success" if success else "✗ Failed"
        print(f"  {category}: {status}")
