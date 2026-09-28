import os
import sys
import json
import requests
import urllib.parse

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
COOKIES_PATH = os.path.join(BASE_DIR, "cookies.json")
SITE_URL = "https://k35n.sharepoint.com/sites/CHUNKING"

def parse_cookie_input(raw: str):
    raw = raw.strip()
    # Case 1: JSON (dictionary or Cookie-Editor array)
    if raw.startswith('{') or raw.startswith('['):
        try:
            data = json.loads(raw)
            if isinstance(data, list):
                return {item['name']: item['value'] for item in data if 'name' in item and 'value' in item}
            elif isinstance(data, dict):
                return data
        except Exception as e:
            print(f"Warning: JSON parse failed ({e}), falling back to header parsing.")

    # Case 2: Header string "Cookie: name=val; name2=val2" or "name=val; name2=val2"
    if raw.lower().startswith('cookie:'):
        raw = raw[7:].strip()

    cookies = {}
    for part in raw.split(';'):
        part = part.strip()
        if '=' in part:
            k, v = part.split('=', 1)
            # Some cookies may be percent-encoded or raw
            cookies[k.strip()] = urllib.parse.unquote(v.strip())
    return cookies

def test_and_save(raw_input: str):
    cookies = parse_cookie_input(raw_input)
    if not cookies:
        print("❌ Could not parse any cookies from the input!")
        return False

    print(f"🔍 Found {len(cookies)} cookies: {list(cookies.keys())}")
    
    # Verify critical SharePoint cookies
    if 'FedAuth' not in cookies and 'rtFa' not in cookies:
        print("⚠️ Warning: Neither 'FedAuth' nor 'rtFa' was found in the input. SharePoint authentication will likely fail.")

    # Test against SharePoint
    session = requests.Session()
    session.trust_env = False
    session.cookies.update(cookies)
    try:
        res = session.post(
            f"{SITE_URL}/_api/contextinfo",
            headers={'Accept': 'application/json;odata=verbose'},
            timeout=10
        )
        if res.status_code == 200:
            print("✅ Success! SharePoint accepted the cookies (HTTP 200 FormDigestValue obtained).")
            with open(COOKIES_PATH, 'w', encoding='utf-8') as f:
                json.dump(cookies, f, indent=2, ensure_ascii=False)
            print(f"💾 Updated {COOKIES_PATH} successfully!")
            return True
        else:
            print(f"❌ SharePoint returned status {res.status_code}: {res.text[:200]}")
            return False
    except Exception as e:
        print(f"❌ Connection error: {e}")
        return False

if __name__ == "__main__":
    if len(sys.argv) > 1:
        raw = " ".join(sys.argv[1:])
        test_and_save(raw)
    else:
        print("Paste your cookie string or JSON below, then press Enter:")
        try:
            line = sys.stdin.read().strip()
            if line:
                test_and_save(line)
            else:
                print("No input provided.")
        except KeyboardInterrupt:
            pass
