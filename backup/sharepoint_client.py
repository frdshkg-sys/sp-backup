"""
SharePoint Online Client for CHUN KING Backup Pipeline
Includes enterprise-grade throttling protection (HTTP 429 / 503 handling,
Retry-After inspection, exponential backoff, request pacing, and circuit breaker).
"""

import os
import sys
import time
import json
import re
import hashlib
import random
import requests
from typing import List, Dict, Any, Optional, Tuple, Callable

# Standard Unicode field decoder from SHAREPOINT_GUID_MAPPING.md
KNOWN_TRUNCATED_FIELDS = {
    '_x9810__x8a08__x65bd__x5de5__x65': '預計施工日期',
    '_x9810__x8a08__x5b8c__x5de5__x65': '預計完工日期'
}

def decode_sharepoint_field(field_name: str) -> str:
    """Decodes hex-encoded SharePoint field names (e.g. OData__x9805__x76ee...) to Traditional Chinese."""
    if not field_name:
        return ""
    clean = re.sub(r'^OData_', '', field_name)
    if clean in KNOWN_TRUNCATED_FIELDS:
        return KNOWN_TRUNCATED_FIELDS[clean]
    
    def hex_to_char(m):
        return chr(int(m.group(1), 16))
        
    decoded = re.sub(r'_x([0-9a-fA-F]{4})_', hex_to_char, clean)
    if decoded.endswith('_Id'):
        decoded = decoded[:-3] + ' (ID)'
    return decoded


class SharePointThrottlingException(Exception):
    """Raised when SharePoint throttling (HTTP 429/503) exceeds maximum retry limits."""
    pass


class SharePointClient:
    def __init__(
        self,
        site_url: str = "https://k35n.sharepoint.com/sites/CHUNKING",
        cookies: Optional[Dict[str, str]] = None,
        entra_token: Optional[str] = None,
        user_agent: str = "NONISV|ChunKing|WeeklyBackup/1.0",
        pacing_delay: float = 0.08,
        max_consecutive_throttles: int = 5
    ):
        self.site_url = site_url.rstrip("/")
        self.user_agent = user_agent
        self.pacing_delay = pacing_delay
        self.max_consecutive_throttles = max_consecutive_throttles
        
        self.session = requests.Session()
        self.session.trust_env = False
        self.session.headers.update({
            "User-Agent": self.user_agent,
            "Accept": "application/json;odata=verbose"
        })
        
        if entra_token:
            self.session.headers.update({"Authorization": f"Bearer {entra_token}"})
        elif cookies:
            self.session.cookies.update(cookies)
        else:
            raise ValueError("Either SharePoint cookies or Entra ID Bearer token must be provided.")
            
        self.consecutive_throttles = 0
        self.total_throttle_events = 0
        self._digest = ""
        self._digest_time = 0

    def get_form_digest(self, force: bool = False) -> str:
        """Retrieves and caches SharePoint FormDigestValue for mutating requests."""
        now = time.time()
        if not force and self._digest and (now - self._digest_time < 900):
            return self._digest

        url = f"{self.site_url}/_api/contextinfo"
        res = self._request_with_guard("POST", url)
        self._digest = res.json()["d"]["GetContextWebInformation"]["FormDigestValue"]
        self._digest_time = now
        return self._digest

    def _request_with_guard(
        self,
        method: str,
        url: str,
        max_attempts: int = 6,
        is_binary_stream: bool = False,
        **kwargs
    ) -> requests.Response:
        """
        Executes an HTTP request with built-in defense against HTTP 429 (Too Many Requests)
        and HTTP 503 (Server Busy) using Retry-After headers, exponential backoff, and circuit breaker.
        """
        # Enforce politeness delay between requests to prevent gateway bursts
        if self.pacing_delay > 0:
            time.sleep(self.pacing_delay)

        for attempt in range(max_attempts):
            try:
                kwargs_copy = dict(kwargs)
                if is_binary_stream:
                    kwargs_copy["stream"] = True
                
                resp = self.session.request(method, url, timeout=kwargs_copy.pop("timeout", 60), **kwargs_copy)
                
                if resp.status_code in (200, 201, 206):
                    # Request succeeded: reset consecutive throttle counter
                    self.consecutive_throttles = 0
                    return resp

                elif resp.status_code in (429, 503):
                    self.total_throttle_events += 1
                    self.consecutive_throttles += 1
                    
                    if self.consecutive_throttles >= self.max_consecutive_throttles:
                        raise SharePointThrottlingException(
                            f"Circuit Breaker Tripped! Received {self.consecutive_throttles} consecutive "
                            f"HTTP {resp.status_code} throttling errors from SharePoint. Halting to protect tenant."
                        )

                    retry_after_hdr = resp.headers.get("Retry-After")
                    if retry_after_hdr and retry_after_hdr.isdigit():
                        wait_seconds = int(retry_after_hdr)
                    else:
                        wait_seconds = min(60, (2 ** attempt))

                    jitter = random.uniform(0.5, 2.0)
                    sleep_time = wait_seconds + jitter
                    print(f"⚠️ [SharePoint Throttling {resp.status_code}] Backing off for {sleep_time:.2f}s (Attempt {attempt+1}/{max_attempts})...")
                    time.sleep(sleep_time)

                elif resp.status_code in (401, 403):
                    print(f"⚠️ Authentication error HTTP {resp.status_code} on {url}. Re-checking digest...")
                    time.sleep(2)
                else:
                    print(f"⚠️ Unexpected HTTP {resp.status_code} from {url}: {resp.text[:300]}")
                    resp.raise_for_status()

            except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as net_err:
                wait_seconds = (2 ** attempt) + random.uniform(1.0, 3.0)
                print(f"⚠️ Network error ({net_err.__class__.__name__}), retrying in {wait_seconds:.2f}s...")
                time.sleep(wait_seconds)

        raise RuntimeError(f"❌ SharePoint request failed after {max_attempts} attempts: {url}")

    def fetch_list_items(self, list_guid: str, select_fields: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Paginates through an entire SharePoint list using $top=5000 and follows __next links.
        Returns the raw item dictionaries.
        """
        all_items: List[Dict[str, Any]] = []
        url = f"{self.site_url}/_api/web/lists(guid'{list_guid}')/items?$top=5000"
        if select_fields:
            url += f"&$select={select_fields}"

        while url:
            resp = self._request_with_guard("GET", url)
            data = resp.json().get("d", {})
            results = data.get("results", [])
            all_items.extend(results)
            url = data.get("__next")
            if url:
                print(f"   ...fetched {len(all_items)} records so far (paging next batch)...")

        return all_items

    def fetch_folder_files_metadata(self, server_relative_folder_url: str) -> List[Dict[str, Any]]:
        """
        Lists metadata of all files in a SharePoint document library folder.
        """
        clean_folder = server_relative_folder_url.strip()
        url = (
            f"{self.site_url}/_api/web/GetFolderByServerRelativeUrl('{clean_folder}')/Files"
            "?$select=Name,ServerRelativeUrl,Length,TimeLastModified,UniqueId&$top=5000"
        )
        files = []
        while url:
            try:
                resp = self._request_with_guard("GET", url)
                data = resp.json().get("d", {})
                files.extend(data.get("results", []))
                url = data.get("__next")
            except Exception as e:
                print(f"⚠️ Could not read folder {clean_folder}: {e}")
                break
        return files

    def fetch_subfolders(self, server_relative_folder_url: str) -> List[str]:
        """Lists server relative URLs of subfolders inside a given folder."""
        clean_folder = server_relative_folder_url.strip()
        url = f"{self.site_url}/_api/web/GetFolderByServerRelativeUrl('{clean_folder}')/Folders?$select=ServerRelativeUrl,Name&$top=5000"
        subfolders = []
        try:
            resp = self._request_with_guard("GET", url)
            data = resp.json().get("d", {})
            for f in data.get("results", []):
                name = f.get("Name", "")
                if name and not name.startswith("_") and name != "Forms":
                    subfolders.append(f.get("ServerRelativeUrl"))
        except Exception as e:
            print(f"⚠️ Could not list subfolders of {clean_folder}: {e}")
        return subfolders

    def download_file(self, server_relative_url: str, local_save_path: str) -> Tuple[bool, str, int]:
        """
        Streams a file from SharePoint and saves it to local disk, returning (success, sha256_hash, byte_size).
        """
        url = f"{self.site_url}/_api/web/GetFileByServerRelativeUrl('{server_relative_url}')/$value"
        os.makedirs(os.path.dirname(local_save_path), exist_ok=True)
        hasher = hashlib.sha256()
        total_bytes = 0

        try:
            resp = self._request_with_guard("GET", url, is_binary_stream=True)
            with open(local_save_path, "wb") as f:
                for chunk in resp.iter_content(chunk_size=64 * 1024):
                    if chunk:
                        f.write(chunk)
                        hasher.update(chunk)
                        total_bytes += len(chunk)
            return True, hasher.hexdigest(), total_bytes
        except Exception as e:
            print(f"❌ Failed to download {server_relative_url}: {e}")
            if os.path.exists(local_save_path):
                try:
                    os.remove(local_save_path)
                except OSError:
                    pass
            return False, "", 0
