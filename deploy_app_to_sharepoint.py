import os
import sys
import json
import requests

sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = r"c:\Users\kmk112\Downloads\mitigation"
HTML_PATH = os.path.join(BASE_DIR, "smart_forms_app.html")
COOKIES_PATH = os.path.join(BASE_DIR, "cookies.json")
SITE_URL = "https://k35n.sharepoint.com/sites/CHUNKING"

with open(COOKIES_PATH, 'r', encoding='utf-8') as f:
    raw_cookies = json.load(f)

if isinstance(raw_cookies, list):
    cookies = {c['name']: c['value'] for c in raw_cookies}
else:
    cookies = raw_cookies

session = requests.Session()
session.trust_env = False
session.cookies.update(cookies)

# 1. Fetch FormDigestValue with retry
import time
digest = None
for attempt in range(5):
    res = session.post(
        f"{SITE_URL}/_api/contextinfo",
        headers={'Accept': 'application/json;odata=verbose'}
    )
    if res.status_code == 200:
        digest = res.json()['d']['GetContextWebInformation']['FormDigestValue']
        print("✅ Obtained SharePoint FormDigestValue")
        break
    elif res.status_code == 429:
        print(f"⚠️ 429 Rate limited on attempt {attempt+1}, sleeping 5 seconds...")
        time.sleep(5)
    else:
        print(f"❌ Failed to get digest: {res.status_code} {res.text}")
        sys.exit(1)

if not digest:
    print("❌ Could not obtain digest after retries.")
    sys.exit(1)

# 2. Upload smart_forms_app.html to /sites/CHUNKING/SiteAssets/forms/app.html and smart_forms_app.html
with open(HTML_PATH, 'rb') as f:
    html_content = f.read()

headers = {
    'Accept': 'application/json;odata=verbose',
    'X-RequestDigest': digest
}

target_files = ['app.html', 'smart_forms_app.html']
for filename in target_files:
    upload_url = f"{SITE_URL}/_api/web/GetFolderByServerRelativeUrl('/sites/CHUNKING/SiteAssets/forms')/Files/add(url='{filename}',overwrite=true)"
    uploaded = False
    for attempt in range(6):
        upload_res = session.post(upload_url, headers=headers, data=html_content)
        if upload_res.status_code in [200, 201]:
            print(f"🎉 Successfully uploaded {filename} to SharePoint! Status: {upload_res.status_code}")
            print(f"   Target: /sites/CHUNKING/SiteAssets/forms/{filename} (Size: {len(html_content)} bytes)")
            uploaded = True
            break
        elif upload_res.status_code == 429:
            wait_s = (attempt + 1) * 5
            print(f"⚠️ 429 Rate limited uploading {filename} (attempt {attempt+1}), waiting {wait_s}s...")
            time.sleep(wait_s)
        else:
            print(f"❌ Upload failed for {filename}: {upload_res.status_code} {upload_res.text}")
            sys.exit(1)
    if not uploaded:
        print(f"❌ Failed to upload {filename} after all retries.")
        sys.exit(1)

# 3. Verify deployed files
for filename in target_files:
    verify_res = session.get(f"{SITE_URL}/SiteAssets/forms/{filename}")
    print(f"🔍 Verification fetch ({filename}) status: {verify_res.status_code}, length: {len(verify_res.content)} bytes")
    if len(verify_res.content) == len(html_content):
        print(f"✅ Verified: SharePoint deployed {filename} size matches local file size exactly!")
    else:
        print(f"⚠️ Size difference detected during verification for {filename}.")

