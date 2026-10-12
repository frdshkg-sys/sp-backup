"""
Credential Verification Script for CHUN KING Backup Pipeline
Tests both SharePoint cookies and Google Drive OAuth credentials.
"""

import os
import sys
import json

# Ensure UTF-8 output in Windows terminal
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE_URL = os.environ.get("SP_SITE_URL", "https://k35n.sharepoint.com/sites/CHUNKING")


def verify_sharepoint() -> bool:
    print("\n--- [1/2] 正在驗證 SharePoint Cookies ---")
    import requests

    # 1. 取得 Cookies (優先讀取環境變數，若無則讀取本地 cookies.json)
    env_cookies = os.environ.get("SP_COOKIES_JSON")
    cookies = {}

    if env_cookies:
        env_cookies = env_cookies.strip()
        if env_cookies.startswith("{") or env_cookies.startswith("["):
            try:
                parsed = json.loads(env_cookies)
                if isinstance(parsed, list):
                    cookies = {c["name"]: c["value"] for c in parsed if "name" in c and "value" in c}
                else:
                    cookies = parsed
            except Exception as e:
                print(f"[!] 無法將 SP_COOKIES_JSON 解析為 JSON: {e}")
        else:
            try:
                import urllib.parse
                raw = env_cookies[7:].strip() if env_cookies.lower().startswith("cookie:") else env_cookies
                for part in raw.split(";"):
                    if "=" in part:
                        k, v = part.split("=", 1)
                        cookies[k.strip()] = urllib.parse.unquote(v.strip())
            except Exception as e:
                print(f"[!] 無法解析 Cookie 標頭字串: {e}")
    else:
        local_path = os.path.join(PROJECT_DIR, "cookies.json")
        if os.path.exists(local_path):
            print(f"[*] 讀取本地檔案: {local_path}")
            with open(local_path, "r", encoding="utf-8") as f:
                parsed = json.load(f)
                if isinstance(parsed, list):
                    cookies = {c["name"]: c["value"] for c in parsed if "name" in c and "value" in c}
                else:
                    cookies = parsed
        else:
            print("[X] 找不到 cookies.json 或 SP_COOKIES_JSON 環境變數！")
            return False

    if not cookies:
        print("[X] Cookies 內容為空！")
        return False

    session = requests.Session()
    session.trust_env = False
    session.cookies.update(cookies)
    session.headers.update({
        "Accept": "application/json;odata=verbose",
        "User-Agent": "NONISV|ChunKing|WeeklyBackup/1.0"
    })

    try:
        res = session.post(f"{SITE_URL}/_api/contextinfo", timeout=12)
        if res.status_code == 200:
            digest = res.json().get("d", {}).get("GetContextWebInformation", {}).get("FormDigestValue", "")
            print(f"[OK] SharePoint 驗證成功！(HTTP 200)")
            print(f"     FormDigest: {digest[:24]}...")
            return True
        else:
            print(f"[X] SharePoint 驗證失敗: HTTP {res.status_code}")
            if res.status_code in (401, 403):
                print("     原因: Cookies 已過期或權限不足，請重新登入複製。")
            return False
    except Exception as e:
        print(f"[X] 連線至 SharePoint 時發生錯誤: {e}")
        return False


def verify_gdrive() -> bool:
    print("\n--- [2/2] 正在驗證 Google Drive OAuth 憑證 ---")
    try:
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request
        from googleapiclient.discovery import build
    except ImportError:
        print("[!] 尚未安裝 Google API 用戶端套件 (請執行: pip install google-api-python-client google-auth-oauthlib)")
        return False

    token_data = None
    env_oauth = os.environ.get("GDRIVE_OAUTH_TOKEN_JSON")
    if env_oauth:
        try:
            token_data = json.loads(env_oauth)
        except Exception as e:
            print(f"[!] 無法解析 GDRIVE_OAUTH_TOKEN_JSON: {e}")
    else:
        oauth_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "oauth_token.json")
        if os.path.exists(oauth_file):
            print(f"[*] 讀取本地檔案: {oauth_file}")
            with open(oauth_file, "r", encoding="utf-8") as f:
                token_data = json.load(f)
        else:
            print("[X] 找不到 oauth_token.json 或 GDRIVE_OAUTH_TOKEN_JSON 環境變數！")
            return False

    if not token_data:
        print("[X] OAuth Token 資料為空！")
        return False

    try:
        creds = Credentials(
            token=token_data.get("token"),
            refresh_token=token_data.get("refresh_token"),
            token_uri=token_data.get("token_uri", "https://oauth2.googleapis.com/token"),
            client_id=token_data.get("client_id"),
            client_secret=token_data.get("client_secret"),
            scopes=["https://www.googleapis.com/auth/drive"]
        )

        if not creds.valid and creds.refresh_token:
            print("[*] 正在透過 refresh_token 刷新存取金鑰...")
            creds.refresh(Request())

        service = build("drive", "v3", credentials=creds)
        about = service.about().get(fields="user, storageQuota").execute()
        user_email = about.get("user", {}).get("emailAddress", "未知")
        limit = int(about.get("storageQuota", {}).get("limit", 0)) / (1024 ** 3)
        usage = int(about.get("storageQuota", {}).get("usage", 0)) / (1024 ** 3)

        print(f"[OK] Google Drive 驗證成功！")
        print(f"     登入帳號: {user_email}")
        if limit > 0:
            print(f"     儲存空間: {usage:.2f} GB / {limit:.2f} GB")
        else:
            print(f"     儲存空間: {usage:.2f} GB (無上限/機構配額)")

        folder_id = os.environ.get("GDRIVE_FOLDER_ID")
        if folder_id:
            try:
                folder_meta = service.files().get(fileId=folder_id, fields="id, name").execute()
                print(f"[OK] 目標資料夾已確認: {folder_meta.get('name')} (ID: {folder_id})")
            except Exception as e:
                print(f"[!] 無法存取目標資料夾 ID {folder_id}: {e}")

        return True
    except Exception as e:
        print(f"[X] Google Drive 驗證失敗: {e}")
        return False


if __name__ == "__main__":
    sp_ok = verify_sharepoint()
    gd_ok = verify_gdrive()
    print("\n==================================================")
    if sp_ok and gd_ok:
        print("ALL PASS: 兩份 JSON 憑證皆正常可用！可以安心貼入 GitHub Secrets。")
    else:
        print("FAIL: 有部分憑證驗證未通過，請檢查上方錯誤訊息。")
    print("==================================================\n")
