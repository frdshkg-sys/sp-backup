import os
import sys
import json
import requests

sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
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

# 2. Ensure /sites/CHUNKING/SiteAssets/app and lib folders exist
try:
    session.post(
        f"{SITE_URL}/_api/web/GetFolderByServerRelativeUrl('/sites/CHUNKING/SiteAssets')/Folders/add(url='app')",
        headers={'Accept': 'application/json;odata=verbose', 'X-RequestDigest': digest, 'Content-Type': 'application/json;odata=verbose'}
    )
except Exception:
    pass

try:
    session.post(
        f"{SITE_URL}/_api/web/GetFolderByServerRelativeUrl('/sites/CHUNKING/SiteAssets')/Folders/add(url='lib')",
        headers={'Accept': 'application/json;odata=verbose', 'X-RequestDigest': digest, 'Content-Type': 'application/json;odata=verbose'}
    )
except Exception:
    pass

# Upload lib/pdf-lib.min.js if present
lib_pdf_path = os.path.join(BASE_DIR, "lib", "pdf-lib.min.js")
if os.path.exists(lib_pdf_path):
    with open(lib_pdf_path, 'rb') as f:
        pdf_lib_bytes = f.read()
    up_res = session.post(
        f"{SITE_URL}/_api/web/GetFolderByServerRelativeUrl('/sites/CHUNKING/SiteAssets/lib')/Files/add(url='pdf-lib.min.js',overwrite=true)",
        headers={'Accept': 'application/json;odata=verbose', 'X-RequestDigest': digest},
        data=pdf_lib_bytes
    )
    if up_res.status_code in [200, 201]:
        print("🎉 Successfully uploaded pdf-lib.min.js to /sites/CHUNKING/SiteAssets/lib!")
    else:
        print(f"⚠️ Warning: pdf-lib upload status: {up_res.status_code}")

# 3. Upload smart_forms_app.html to both /SiteAssets/forms and /SiteAssets/app
with open(HTML_PATH, 'rb') as f:
    html_content = f.read()

headers = {
    'Accept': 'application/json;odata=verbose',
    'X-RequestDigest': digest
}

target_folders = ['/sites/CHUNKING/SiteAssets/forms', '/sites/CHUNKING/SiteAssets/app']
target_files = ['app.html', 'smart_forms_app.html']

for folder in target_folders:
    for filename in target_files:
        upload_url = f"{SITE_URL}/_api/web/GetFolderByServerRelativeUrl('{folder}')/Files/add(url='{filename}',overwrite=true)"
        uploaded = False
        for attempt in range(6):
            upload_res = session.post(upload_url, headers=headers, data=html_content)
            if upload_res.status_code in [200, 201]:
                print(f"🎉 Successfully uploaded {filename} to {folder}! Status: {upload_res.status_code}")
                uploaded = True
                break
            elif upload_res.status_code == 429:
                wait_s = (attempt + 1) * 5
                print(f"⚠️ 429 Rate limited uploading {filename} (attempt {attempt+1}), waiting {wait_s}s...")
                time.sleep(wait_s)
            else:
                print(f"❌ Upload failed for {filename} in {folder}: {upload_res.status_code} {upload_res.text}")
                sys.exit(1)
        if not uploaded:
            print(f"❌ Failed to upload {filename} to {folder} after all retries.")
            sys.exit(1)

# 4. Package and upload chrome-extension.zip (Version 1.4)
import zipfile
import io

ext_dir = os.path.join(BASE_DIR, "chrome-extension")
if os.path.exists(ext_dir):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as z:
        for root, dirs, files in os.walk(ext_dir):
            for f in files:
                if f.startswith('.'):
                    continue
                full_path = os.path.join(root, f)
                rel_path = os.path.relpath(full_path, BASE_DIR)
                z.write(full_path, rel_path)
    zip_bytes = buf.getvalue()

    for folder in target_folders:
        zip_url = f"{SITE_URL}/_api/web/GetFolderByServerRelativeUrl('{folder}')/Files/add(url='chrome-extension.zip',overwrite=true)"
        for attempt in range(5):
            res_zip = session.post(zip_url, headers=headers, data=zip_bytes)
            if res_zip.status_code in [200, 201]:
                print(f"🎉 Successfully uploaded chrome-extension.zip to {folder}! Status: {res_zip.status_code}")
                break
            elif res_zip.status_code == 429:
                time.sleep((attempt + 1) * 4)
            else:
                print(f"⚠️ Warning uploading zip to {folder}: {res_zip.status_code}")
                break

# 5. Verify deployed files
for folder in target_folders:
    for filename in target_files:
        subpath = folder.replace('/sites/CHUNKING', '')
        verify_res = session.get(f"{SITE_URL}{subpath}/{filename}")
        print(f"🔍 Verification fetch ({folder}/{filename}) status: {verify_res.status_code}, length: {len(verify_res.content)} bytes")
        if len(verify_res.content) == len(html_content):
            print(f"✅ Verified: {folder}/{filename} size matches local file size exactly!")
        else:
            print(f"⚠️ Size difference detected during verification for {folder}/{filename}.")

# Also verify chrome-extension.zip
for folder in target_folders:
    subpath = folder.replace('/sites/CHUNKING', '')
    v_zip = session.get(f"{SITE_URL}{subpath}/chrome-extension.zip")
    print(f"🔍 Verification fetch ({folder}/chrome-extension.zip) status: {v_zip.status_code}, length: {len(v_zip.content)} bytes")
    if len(v_zip.content) == len(zip_bytes):
        print(f"✅ Verified: {folder}/chrome-extension.zip is latest v1.4!")


