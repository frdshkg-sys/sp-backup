import os
import sys
import json
import requests

sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = r"c:\Users\kmk112\Downloads\mitigation"
HTML_PATH = os.path.join(BASE_DIR, "dashboard.html")
COOKIES_PATH = os.path.join(BASE_DIR, "cookies.json")
SITE_URL = "https://k35n.sharepoint.com/sites/CHUNKING"

with open(COOKIES_PATH, 'r', encoding='utf-8') as f:
    cookies = json.load(f)

import time

# 1. Fetch FormDigestValue with retry
digest = None
for attempt in range(6):
    res = requests.post(
        f"{SITE_URL}/_api/contextinfo",
        cookies=cookies,
        headers={'Accept': 'application/json;odata=verbose'}
    )
    if res.status_code == 200:
        digest = res.json()['d']['GetContextWebInformation']['FormDigestValue']
        print("✅ Obtained SharePoint FormDigestValue")
        break
    elif res.status_code == 429:
        wait_s = (attempt + 1) * 5
        print(f"⚠️ 429 Rate limited getting digest (attempt {attempt+1}), waiting {wait_s}s...")
        time.sleep(wait_s)
    else:
        print(f"❌ Failed to get digest: {res.status_code} {res.text}")
        sys.exit(1)

if not digest:
    print("❌ Failed to obtain digest.")
    sys.exit(1)

# 2. Upload dashboard.html to /sites/CHUNKING/SiteAssets/forms/dashboard.html
upload_url = f"{SITE_URL}/_api/web/GetFolderByServerRelativeUrl('/sites/CHUNKING/SiteAssets/forms')/Files/add(url='dashboard.html',overwrite=true)"

with open(HTML_PATH, 'rb') as f:
    html_content = f.read()

headers = {
    'Accept': 'application/json;odata=verbose',
    'X-RequestDigest': digest
}

uploaded = False
for attempt in range(6):
    upload_res = requests.post(upload_url, cookies=cookies, headers=headers, data=html_content)
    if upload_res.status_code in [200, 201]:
        print(f"🎉 Successfully uploaded dashboard.html to SharePoint! Status: {upload_res.status_code}")
        print(f"   Target: /sites/CHUNKING/SiteAssets/forms/dashboard.html (Size: {len(html_content)} bytes)")
        uploaded = True
        break
    elif upload_res.status_code == 429:
        wait_s = (attempt + 1) * 5
        print(f"⚠️ 429 Rate limited uploading dashboard.html (attempt {attempt+1}), waiting {wait_s}s...")
        time.sleep(wait_s)
    else:
        print(f"❌ Upload failed: {upload_res.status_code} {upload_res.text}")
        sys.exit(1)

if not uploaded:
    print("❌ Upload failed after all retries.")
    sys.exit(1)

# 3. Verify deployed file
verify_res = requests.get(f"{SITE_URL}/SiteAssets/forms/dashboard.html", cookies=cookies)
print(f"🔍 Verification fetch status: {verify_res.status_code}, length: {len(verify_res.content)} bytes")
if len(verify_res.content) == len(html_content):
    print("✅ Verified: SharePoint deployed file size matches local file size exactly!")
else:
    print("⚠️ Size difference detected during verification.")
