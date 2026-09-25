"""
Google Drive REST API Client for CHUN KING Backup Pipeline
Supports both:
1. OAuth2 User Credentials (recommended for Personal Google Drive @gmail.com to use your own storage quota)
2. Service Account Credentials (supports Google Workspace Shared Drives with supportsAllDrives=True)
"""

import os
import sys
import json
import time
import socket
import random
import mimetypes
from typing import Optional, Dict, Any, List

# Set socket timeout to 120s to prevent premature socket read timeouts during large chunked uploads
socket.setdefaulttimeout(120.0)

try:
    from google.oauth2 import service_account
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
    GOOGLE_CLIENT_AVAILABLE = True
except ImportError:
    GOOGLE_CLIENT_AVAILABLE = False


class GoogleDriveClient:
    def __init__(
        self,
        service_account_json_content: Optional[str] = None,
        service_account_file_path: Optional[str] = None,
        oauth_json_content: Optional[str] = None,
        oauth_file_path: Optional[str] = None,
        root_folder_id: Optional[str] = None
    ):
        self.root_folder_id = root_folder_id
        self.service = None
        self._folder_cache: Dict[str, str] = {}
        self.auth_mode = "NONE"

        if not GOOGLE_CLIENT_AVAILABLE:
            print("⚠️ google-api-python-client is not installed in current environment.")
            return

        scopes = ["https://www.googleapis.com/auth/drive"]

        # 1. Try OAuth2 User Credentials first (uses the user's actual Google Drive quota)
        oauth_data = None
        if oauth_json_content:
            try:
                oauth_data = json.loads(oauth_json_content)
            except Exception as e:
                print(f"⚠️ Could not parse GDRIVE_OAUTH_TOKEN_JSON: {e}")
        elif oauth_file_path and os.path.exists(oauth_file_path):
            try:
                with open(oauth_file_path, "r", encoding="utf-8") as f:
                    oauth_data = json.load(f)
            except Exception as e:
                print(f"⚠️ Could not read {oauth_file_path}: {e}")

        if oauth_data:
            try:
                creds = Credentials(
                    token=oauth_data.get("token"),
                    refresh_token=oauth_data.get("refresh_token"),
                    token_uri=oauth_data.get("token_uri", "https://oauth2.googleapis.com/token"),
                    client_id=oauth_data.get("client_id"),
                    client_secret=oauth_data.get("client_secret"),
                    scopes=scopes
                )
                if not creds.valid and creds.refresh_token:
                    creds.refresh(Request())
                self.service = build("drive", "v3", credentials=creds)
                self.auth_mode = "OAUTH2_USER"
                print("✅ Authenticated via OAuth2 User Credentials (Files will be owned by your Google Account).")
                return
            except Exception as e:
                print(f"❌ Failed to initialize OAuth2 credentials: {e}")

        # 2. Try Service Account (Supported for Google Workspace Shared Drives)
        if service_account_json_content:
            try:
                info = json.loads(service_account_json_content)
                creds = service_account.Credentials.from_service_account_info(info, scopes=scopes)
                self.service = build("drive", "v3", credentials=creds)
                self.auth_mode = "SERVICE_ACCOUNT"
                print("✅ Successfully authenticated to Google Drive API via Service Account JSON Secret.")
                return
            except Exception as e:
                print(f"❌ Failed to initialize Google Drive service from JSON secret: {e}")

        elif service_account_file_path and os.path.exists(service_account_file_path):
            try:
                creds = service_account.Credentials.from_service_account_file(service_account_file_path, scopes=scopes)
                self.service = build("drive", "v3", credentials=creds)
                self.auth_mode = "SERVICE_ACCOUNT"
                print(f"✅ Successfully authenticated to Google Drive API via {service_account_file_path}")
                return
            except Exception as e:
                print(f"❌ Failed to initialize Google Drive service from file: {e}")

    @property
    def is_connected(self) -> bool:
        return self.service is not None

    def find_or_create_folder(self, folder_name: str, parent_id: Optional[str] = None) -> str:
        """
        Finds an existing folder by name under parent_id, or creates it if missing.
        Supports both personal drives and Google Workspace Shared Drives (supportsAllDrives=True).
        """
        if not self.is_connected:
            raise RuntimeError("Google Drive client is not connected.")

        parent = parent_id or self.root_folder_id
        cache_key = f"{parent}/{folder_name}"
        if cache_key in self._folder_cache:
            return self._folder_cache[cache_key]

        query = (
            f"mimeType = 'application/vnd.google-apps.folder' and "
            f"name = '{folder_name}' and trashed = false"
        )
        if parent:
            query += f" and '{parent}' in parents"

        results = self.service.files().list(
            q=query,
            spaces="drive",
            fields="files(id, name)",
            supportsAllDrives=True,
            includeItemsFromAllDrives=True
        ).execute()
        files = results.get("files", [])

        if files:
            folder_id = files[0]["id"]
        else:
            folder_metadata = {
                "name": folder_name,
                "mimeType": "application/vnd.google-apps.folder",
            }
            if parent:
                folder_metadata["parents"] = [parent]

            folder = self.service.files().create(
                body=folder_metadata,
                fields="id",
                supportsAllDrives=True
            ).execute()
            folder_id = folder.get("id")
            print(f"📁 Created new Google Drive folder: '{folder_name}' (ID: {folder_id})")

        self._folder_cache[cache_key] = folder_id
        return folder_id

    def upload_file(
        self,
        local_file_path: str,
        destination_folder_id: Optional[str] = None,
        remote_file_name: Optional[str] = None,
        overwrite: bool = True,
        max_retries: int = 4
    ) -> Optional[str]:
        """
        Uploads a local file to Google Drive using resumable chunked upload.
        Includes supportsAllDrives=True for Shared Drives compatibility and exponential backoff retry.
        """
        if not self.is_connected:
            raise RuntimeError("Google Drive client is not connected.")

        target_parent = destination_folder_id or self.root_folder_id
        fname = remote_file_name or os.path.basename(local_file_path)
        mime_type, _ = mimetypes.guess_type(local_file_path)
        if not mime_type:
            mime_type = "application/octet-stream"

        existing_file_id = None
        if target_parent:
            try:
                q = f"name = '{fname}' and '{target_parent}' in parents and trashed = false"
                res = self.service.files().list(
                    q=q,
                    spaces="drive",
                    fields="files(id, name)",
                    supportsAllDrives=True,
                    includeItemsFromAllDrives=True
                ).execute()
                files = res.get("files", [])
                if files:
                    existing_file_id = files[0]["id"]
            except Exception as e:
                print(f"⚠️ Warning checking existing file {fname} in Google Drive: {e}")

        for attempt in range(max_retries):
            try:
                media = MediaFileUpload(local_file_path, mimetype=mime_type, resumable=True)

                if existing_file_id and overwrite:
                    # Update existing file in-place
                    updated = self.service.files().update(
                        fileId=existing_file_id,
                        media_body=media,
                        fields="id",
                        supportsAllDrives=True
                    ).execute()
                    return updated.get("id")
                else:
                    # Create new file
                    metadata = {"name": fname}
                    if target_parent:
                        metadata["parents"] = [target_parent]
                    created = self.service.files().create(
                        body=metadata,
                        media_body=media,
                        fields="id",
                        supportsAllDrives=True
                    ).execute()
                    return created.get("id")

            except Exception as err:
                wait_sec = min(30, (2 ** attempt) + random.uniform(1.0, 3.0))
                print(f"⚠️ [Google Drive Upload Retry {attempt+1}/{max_retries}] {fname} failed ({err.__class__.__name__}: {err}). Retrying in {wait_sec:.1f}s...")
                time.sleep(wait_sec)

        print(f"❌ Failed to upload {fname} to Google Drive after {max_retries} attempts.")
        return None

    def fetch_manifest(self) -> Dict[str, Any]:
        """Downloads the remote manifest.json from the root backup folder on Google Drive."""
        if not self.is_connected or not self.root_folder_id:
            return {}

        try:
            q = f"name = 'manifest.json' and '{self.root_folder_id}' in parents and trashed = false"
            res = self.service.files().list(
                q=q,
                spaces="drive",
                fields="files(id, name)",
                supportsAllDrives=True,
                includeItemsFromAllDrives=True
            ).execute()
            files = res.get("files", [])
            if not files:
                return {}

            file_id = files[0]["id"]
            content = self.service.files().get_media(fileId=file_id, supportsAllDrives=True).execute()
            return json.loads(content.decode("utf-8"))
        except Exception as e:
            print(f"⚠️ Could not load remote manifest.json: {e}")
            return {}

    def save_manifest(self, manifest_data: Dict[str, Any]) -> bool:
        """Saves updated manifest.json to the root backup folder on Google Drive."""
        if not self.is_connected or not self.root_folder_id:
            return False

        temp_manifest_path = "temp_manifest.json"
        try:
            with open(temp_manifest_path, "w", encoding="utf-8") as f:
                json.dump(manifest_data, f, ensure_ascii=False, indent=2)

            self.upload_file(temp_manifest_path, destination_folder_id=self.root_folder_id, remote_file_name="manifest.json", overwrite=True)
            return True
        except Exception as e:
            print(f"❌ Failed to save manifest.json to Google Drive: {e}")
            return False
        finally:
            if os.path.exists(temp_manifest_path):
                os.remove(temp_manifest_path)

    def list_files_in_folder(self, folder_id: str) -> Dict[str, int]:
        """
        Enumerates all files in a Google Drive folder and returns a dict mapping {filename: size_in_bytes}.
        Supports large folders via pageToken.
        """
        if not self.is_connected or not folder_id:
            return {}

        results = {}
        page_token = None
        while True:
            try:
                q = f"'{folder_id}' in parents and trashed = false and mimeType != 'application/vnd.google-apps.folder'"
                res = self.service.files().list(
                    q=q,
                    spaces="drive",
                    fields="nextPageToken, files(id, name, size)",
                    pageSize=1000,
                    pageToken=page_token,
                    supportsAllDrives=True,
                    includeItemsFromAllDrives=True
                ).execute()
                for f in res.get("files", []):
                    name = f.get("name")
                    size = int(f.get("size", 0)) if f.get("size") else 0
                    if name:
                        results[name] = size
                page_token = res.get("nextPageToken")
                if not page_token:
                    break
            except Exception as e:
                print(f"⚠️ Error listing files in Google Drive folder {folder_id}: {e}")
                break
        return results
