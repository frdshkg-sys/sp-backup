"""
OAuth Token Generator for Personal Google Drive (@gmail.com)
Allows the backup pipeline to upload files directly into your personal Google Drive
using your actual Google storage quota (bypassing the 0-byte Service Account quota limitation).
"""

import os
import sys
import json

try:
    from google_auth_oauthlib.flow import InstalledAppFlow
    OAUTHLIB_AVAILABLE = True
except ImportError:
    OAUTHLIB_AVAILABLE = False

SCOPES = ["https://www.googleapis.com/auth/drive"]


def main():
    if not OAUTHLIB_AVAILABLE:
        print("❌ google-auth-oauthlib is not installed.")
        print("   Please run: pip install google-auth-oauthlib")
        sys.exit(1)

    print("==================================================================")
    print("🔑 Google Drive OAuth2 User Token Generator")
    print("==================================================================")
    print("This will authorize the backup script to upload files as YOUR Google Account,")
    print("ensuring it uses your Google Drive storage quota (bypassing Service Account limits).\n")

    script_dir = os.path.dirname(os.path.abspath(__file__))
    client_secret_path = os.path.join(script_dir, "client_secret.json")

    if os.path.exists(client_secret_path):
        print(f"📄 Found {client_secret_path}, loading credentials...")
        flow = InstalledAppFlow.from_client_secrets_file(client_secret_path, SCOPES)
    else:
        print("💡 Step: In Google Cloud Console:")
        print("   1. Go to: https://console.cloud.google.com/apis/credentials")
        print("   2. Click 'Create Credentials' > 'OAuth client ID'")
        print("   3. Application type: 'Desktop app' -> Name: 'Backup Bot' -> Create")
        print("   4. Paste the Client ID and Client Secret below:\n")

        client_id = input("Enter Client ID: ").strip()
        client_secret = input("Enter Client Secret: ").strip()

        if not client_id or not client_secret:
            print("❌ Client ID and Client Secret cannot be empty.")
            sys.exit(1)

        client_config = {
            "installed": {
                "client_id": client_id,
                "client_secret": client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": ["http://localhost:8088/"]
            }
        }
        flow = InstalledAppFlow.from_client_config(client_config, SCOPES)

    print("\n🌐 Opening browser for authorization... (Please sign in and click 'Continue/Allow')")
    creds = flow.run_local_server(port=8088)

    token_data = {
        "token": creds.token,
        "refresh_token": creds.refresh_token,
        "token_uri": creds.token_uri,
        "client_id": creds.client_id,
        "client_secret": creds.client_secret,
        "scopes": creds.scopes
    }

    out_file = os.path.join(script_dir, "oauth_token.json")
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(token_data, f, indent=2)

    print("\n==================================================================")
    print(f"🎉 SUCCESS! Token saved to: {out_file}")
    print("==================================================================")
    print("For GitHub Actions Secrets, add a secret named 'GDRIVE_OAUTH_TOKEN_JSON'")
    print("with the following content:\n")
    print(json.dumps(token_data))
    print("\n==================================================================")


if __name__ == "__main__":
    main()
