import os
import sys
import time
import json
import threading
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.stdout.reconfigure(encoding='utf-8', line_buffering=True)

SITE_URL = "https://k35n.sharepoint.com/sites/CHUNKING"
GUID_EXPENSES = "a09172c2-2be4-4b12-8dfd-418a6fbe0c6d"
BASE_DIR = r"c:\Users\kmk112\Downloads\mitigation"
COOKIES_FILE = os.path.join(BASE_DIR, "cookies.json")
UPDATE_LIST_FILE = os.path.join(BASE_DIR, "sp_invoice_backfill_updates.json")
CHECKPOINT_FILE = os.path.join(BASE_DIR, "invoice_backfill_checkpoint.json")

# ==============================================================================
# 1. Load Cookies & Updates
# ==============================================================================
with open(COOKIES_FILE, 'r', encoding='utf-8') as f:
    raw_cookies = json.load(f)

if isinstance(raw_cookies, list):
    cookies = {c['name']: c['value'] for c in raw_cookies}
else:
    cookies = raw_cookies

with open(UPDATE_LIST_FILE, 'r', encoding='utf-8') as f:
    all_updates = json.load(f)

print(f"Total updates loaded: {len(all_updates)}")

# ==============================================================================
# 2. Checkpoint Management
# ==============================================================================
def load_checkpoint():
    if os.path.exists(CHECKPOINT_FILE):
        try:
            with open(CHECKPOINT_FILE, 'r', encoding='utf-8') as f:
                return set(json.load(f))
        except Exception as e:
            print(f"Warning reading checkpoint: {e}")
    return set()

def save_checkpoint(done_set):
    tmp = CHECKPOINT_FILE + ".tmp"
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(list(done_set), f)
    os.replace(tmp, CHECKPOINT_FILE)

# ==============================================================================
# 3. Form Digest Management
# ==============================================================================
digest_lock = threading.Lock()
current_digest = ""
digest_time = 0

def get_digest(force=False):
    global current_digest, digest_time
    with digest_lock:
        now = time.time()
        # Form digest is valid for ~25-30 mins; refresh every 10 mins (600s)
        if not force and current_digest and (now - digest_time < 600):
            return current_digest
        
        for attempt in range(5):
            try:
                res = requests.post(
                    f"{SITE_URL}/_api/contextinfo",
                    cookies=cookies,
                    headers={'Accept': 'application/json;odata=verbose'},
                    timeout=20
                )
                if res.status_code == 200:
                    current_digest = res.json()['d']['GetContextWebInformation']['FormDigestValue']
                    digest_time = now
                    print(f"  🔑 FormDigest refreshed at {time.strftime('%H:%M:%S')}", flush=True)
                    return current_digest
                elif res.status_code in (429, 503):
                    sec = int(res.headers.get("Retry-After", 10))
                    print(f"  ⚠️ Digest fetch rate limited, sleeping {sec}s...", flush=True)
                    time.sleep(sec)
                else:
                    time.sleep(2)
            except Exception as e:
                time.sleep(2)
        return current_digest

# ==============================================================================
# 4. Global Throttling Coordinator & Session
# ==============================================================================
thread_local = threading.local()
throttle_lock = threading.Lock()
global_throttle_until = 0.0
throttle_count = 0

def wait_for_throttle():
    global global_throttle_until
    with throttle_lock:
        target = global_throttle_until
    now = time.time()
    if target > now:
        wait_sec = target - now
        time.sleep(wait_sec)

def trigger_throttle(retry_after_sec=10):
    global global_throttle_until, throttle_count
    with throttle_lock:
        throttle_count += 1
        now = time.time()
        target = now + retry_after_sec + 2.0
        if target > global_throttle_until:
            global_throttle_until = target
            print(f"\n  ⚠️ [THROTTLED] M365 rate limit detected! Pausing ALL workers for {retry_after_sec + 2:.1f}s until {time.strftime('%H:%M:%S', time.localtime(target))}...", flush=True)

def get_session():
    if not hasattr(thread_local, "session"):
        s = requests.Session()
        s.trust_env = False
        s.cookies.update(cookies)
        adapter = HTTPAdapter(
            pool_connections=10,
            pool_maxsize=10,
            max_retries=Retry(total=2, backoff_factor=1, status_forcelist=[500, 502, 504])
        )
        s.mount("https://", adapter)
        thread_local.session = s
    return thread_local.session

# ==============================================================================
# 5. Worker Update Function
# ==============================================================================
def update_item(item):
    item_id = item["Id"]
    invoice_no = str(item["InvoiceNo"])
    url = f"{SITE_URL}/_api/web/lists(guid'{GUID_EXPENSES}')/items({item_id})"
    payload = {
        "__metadata": {"type": "SP.Data.TransactionsListItem"},
        "Invoice_x0020_No_x002e_": invoice_no
    }
    
    s = get_session()
    
    for attempt in range(8):
        # 1. Obey global throttle window
        wait_for_throttle()
        
        # 2. Add safe pacing delay (60ms) to ensure smooth request cadence
        time.sleep(0.06)
        
        dig = get_digest()
        try:
            r = s.post(url, json=payload, headers={
                "Accept": "application/json;odata=verbose",
                "Content-Type": "application/json;odata=verbose",
                "X-RequestDigest": dig,
                "X-HTTP-Method": "MERGE",
                "If-Match": "*"
            }, timeout=30)
            
            if r.status_code in (200, 204):
                return True, None
            
            elif r.status_code == 429 or r.status_code == 503:
                # SharePoint Throttling / Service Unavailable
                retry_header = r.headers.get("Retry-After")
                try:
                    retry_sec = int(retry_header) if retry_header else 10
                except (ValueError, TypeError):
                    retry_sec = 10
                trigger_throttle(retry_sec)
                continue
                
            elif r.status_code in (401, 403):
                # Token or digest expired
                get_digest(force=True)
                time.sleep(1)
                continue
                
            else:
                # Unexpected status code
                time.sleep(2)
                
        except Exception as e:
            time.sleep(2)
            
    return False, f"Item {item_id} failed after 8 attempts"

# ==============================================================================
# 6. Main Orchestrator
# ==============================================================================
def main():
    print("=" * 65, flush=True)
    print("🚀 SharePoint Historical Invoice No. Backfill Tool", flush=True)
    print("   Throttling-Aware & Checkpointed Execution", flush=True)
    print(f"   Start Time: {time.strftime('%Y-%m-%d %H:%M:%S')}", flush=True)
    print("=" * 65, flush=True)

    init_dig = get_digest(force=True)
    if not init_dig:
        print("❌ Could not obtain initial SharePoint FormDigest! Exiting.", flush=True)
        return

    checkpoint = load_checkpoint()
    # Add previously verified item ID 27169 if not in checkpoint
    checkpoint.add(27169)
    save_checkpoint(checkpoint)

    remaining = [it for it in all_updates if it["Id"] not in checkpoint]
    total_needed = len(all_updates)
    already_done = total_needed - len(remaining)

    print(f"📊 Total Target Items:     {total_needed}")
    print(f"✅ Already Completed:      {already_done}")
    print(f"⏳ Remaining to Backfill:  {len(remaining)}")

    if not remaining:
        print("\n🎉 All 7,821 items are already up to date! Nothing to do.", flush=True)
        return

    # Use 3 concurrent workers for optimal balance of throughput and throttle safety
    MAX_WORKERS = 3
    print(f"\n⚙️  Worker Configuration: {MAX_WORKERS} threads with pacing & 429 adaptive backoff", flush=True)
    print("=" * 65, flush=True)

    t_start = time.time()
    success_count = 0
    fail_count = 0
    save_lock = threading.Lock()
    last_save_time = time.time()

    try:
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = {executor.submit(update_item, it): it for it in remaining}
            
            for idx, fut in enumerate(as_completed(futures), start=1):
                item = futures[fut]
                ok, err = fut.result()
                
                with save_lock:
                    if ok:
                        checkpoint.add(item["Id"])
                        success_count += 1
                    else:
                        fail_count += 1
                        print(f"  ❌ Error: {err}", flush=True)

                    now = time.time()
                    if now - last_save_time > 5 or idx == len(remaining):
                        save_checkpoint(checkpoint)
                        last_save_time = now

                    if idx % 50 == 0 or idx == len(remaining):
                        elapsed = now - t_start
                        speed = idx / elapsed if elapsed > 0 else 0
                        eta_min = (len(remaining) - idx) / speed / 60 if speed > 0 else 0
                        pct = (already_done + idx) * 100.0 / total_needed
                        print(
                            f"  [{already_done + idx:4d}/{total_needed}] ({pct:5.1f}%) | "
                            f"Done: {success_count:4d} | Failed: {fail_count} | "
                            f"Rate: {speed:4.1f}/s | ETA: {eta_min:4.1f}m | "
                            f"Throttles: {throttle_count}",
                            flush=True
                        )

    except KeyboardInterrupt:
        print("\n⚠️ Interrupted by user! Saving checkpoint...", flush=True)
        save_checkpoint(checkpoint)
        print("Progress saved. You can re-run anytime to resume.", flush=True)
        return

    save_checkpoint(checkpoint)
    total_elapsed = (time.time() - t_start) / 60
    print("\n" + "=" * 65, flush=True)
    print(f"🎉 Backfill Completed in {total_elapsed:.2f} minutes!", flush=True)
    print(f"   Successfully updated: {success_count} items", flush=True)
    print(f"   Failed items:         {fail_count}", flush=True)
    print(f"   Throttle events:      {throttle_count}", flush=True)
    print(f"   Total in checkpoint:  {len(checkpoint)} items", flush=True)
    print("=" * 65, flush=True)

if __name__ == '__main__':
    main()
