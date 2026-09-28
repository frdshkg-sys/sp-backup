import os
import sys
import time
import json
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

sys.stdout.reconfigure(encoding='utf-8', line_buffering=True)

SITE_URL = "https://k35n.sharepoint.com/sites/CHUNKING"
GUID_EXPENSES = "a09172c2-2be4-4b12-8dfd-418a6fbe0c6d"
BASE_DIR = r"c:\Users\kmk112\Downloads\mitigation"
COOKIES_FILE = os.path.join(BASE_DIR, "cookies.json")
PLAN_FILE = os.path.join(BASE_DIR, "sp_invoice_rematch_plan.json")
CHECKPOINT_FILE = os.path.join(BASE_DIR, "rematch_backfill_checkpoint.json")

def load_checkpoint():
    if os.path.exists(CHECKPOINT_FILE):
        try:
            with open(CHECKPOINT_FILE, 'r', encoding='utf-8') as f:
                return set(json.load(f))
        except Exception:
            pass
    return set()

def save_checkpoint(done_set):
    tmp = CHECKPOINT_FILE + ".tmp"
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(list(done_set), f)
    os.replace(tmp, CHECKPOINT_FILE)

def main():
    print("=== STARTING REMATCH BACKFILL EXECUTION ===")
    with open(COOKIES_FILE, 'r', encoding='utf-8') as f:
        raw = json.load(f)
    cookies = {c['name']: c['value'] for c in raw} if isinstance(raw, list) else raw

    session = requests.Session()
    session.trust_env = False
    session.cookies.update(cookies)
    adapter = HTTPAdapter(
        pool_connections=5,
        pool_maxsize=5,
        max_retries=Retry(total=3, backoff_factor=1, status_forcelist=[500, 502, 504])
    )
    session.mount("https://", adapter)

    # 1. Fetch FormDigest
    res = session.post(f"{SITE_URL}/_api/contextinfo", headers={"Accept": "application/json;odata=verbose"})
    digest = res.json()["d"]["GetContextWebInformation"]["FormDigestValue"]
    digest_time = time.time()
    print("✅ Successfully acquired FormDigestValue")

    # 2. Load Plan
    with open(PLAN_FILE, 'r', encoding='utf-8') as f:
        plan = json.load(f)
    print(f"Total plan items: {len(plan)}")

    done_ids = load_checkpoint()
    remaining = [item for item in plan if item["Id"] not in done_ids]
    print(f"Already done: {len(done_ids)}, Remaining: {len(remaining)}")

    success_count = 0
    fail_count = 0

    for i, item in enumerate(remaining, 1):
        item_id = item["Id"]
        target_inv = item["TargetInvoice"] or ""
        
        # Refresh digest if older than 20 mins
        if time.time() - digest_time > 1200:
            res = session.post(f"{SITE_URL}/_api/contextinfo", headers={"Accept": "application/json;odata=verbose"})
            digest = res.json()["d"]["GetContextWebInformation"]["FormDigestValue"]
            digest_time = time.time()

        url = f"{SITE_URL}/_api/web/lists(guid'{GUID_EXPENSES}')/items({item_id})"
        payload = {
            "__metadata": {"type": "SP.Data.TransactionsListItem"},
            "Invoice_x0020_No_x002e_": target_inv
        }

        updated = False
        for attempt in range(6):
            time.sleep(0.12) # Safe 120ms cadence between requests
            try:
                r = session.post(url, json=payload, headers={
                    "Accept": "application/json;odata=verbose",
                    "Content-Type": "application/json;odata=verbose",
                    "X-RequestDigest": digest,
                    "X-HTTP-Method": "MERGE",
                    "If-Match": "*"
                }, timeout=30)

                if r.status_code in (200, 204):
                    updated = True
                    break
                elif r.status_code in (429, 503):
                    retry_after = int(r.headers.get("Retry-After", 5))
                    print(f"⚠️ 429/503 Throttle on ID {item_id}. Backing off for {retry_after}s...")
                    time.sleep(retry_after)
                else:
                    print(f"❌ Error updating ID {item_id}: {r.status_code} {r.text}")
                    time.sleep(2)
            except Exception as e:
                print(f"⚠️ Exception on ID {item_id}: {e}")
                time.sleep(2)

        if updated:
            done_ids.add(item_id)
            success_count += 1
            action_desc = f"'{item['CurrentInvoice']}' -> '{target_inv}'" if target_inv else f"'{item['CurrentInvoice']}' -> [CLEARED]"
            if i % 25 == 0 or i == len(remaining):
                save_checkpoint(done_ids)
                print(f"[{i}/{len(remaining)}] ID {item_id} ({item['Title']}): {action_desc} (Total Success: {success_count})")
        else:
            fail_count += 1
            print(f"❌ FAILED to update ID {item_id}")

    save_checkpoint(done_ids)
    print("\n=== EXECUTION COMPLETED ===")
    print(f"Successfully updated: {success_count}")
    print(f"Failed: {fail_count}")

if __name__ == '__main__':
    main()
