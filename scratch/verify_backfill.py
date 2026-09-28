import json, requests, random, sys
sys.stdout.reconfigure(encoding='utf-8')

with open('cookies.json', 'r', encoding='utf-8') as f:
    raw = json.load(f)
cookies = {c['name']: c['value'] for c in raw} if isinstance(raw, list) else raw
s = requests.Session()
s.trust_env = False
s.cookies.update(cookies)
SITE_URL = 'https://k35n.sharepoint.com/sites/CHUNKING'
GUID_EXPENSES = 'a09172c2-2be4-4b12-8dfd-418a6fbe0c6d'

with open('sp_invoice_backfill_updates.json', 'r', encoding='utf-8') as f:
    updates = json.load(f)

# Sample 10 items across different index ranges
random.seed(42)
indices = [0, 500, 1000, 2000, 3000, 4500, 6000, 7000, 7500, len(updates)-1]
samples = [updates[i] for i in indices]

print(f"Checking {len(samples)} representative items from SharePoint live list...\n")
all_correct = True
for item in samples:
    item_id = item['Id']
    expected_inv = item['InvoiceNo']
    r = s.get(f"{SITE_URL}/_api/web/lists(guid'{GUID_EXPENSES}')/items({item_id})?$select=Id,Title,Invoice_x0020_No_x002e_,OData__x91d1__x984d_", headers={'Accept': 'application/json;odata=verbose'})
    d = r.json()['d']
    actual_inv = d.get('Invoice_x0020_No_x002e_')
    match = (actual_inv == expected_inv)
    status_icon = "✅" if match else "❌"
    print(f"{status_icon} ID {item_id:5d} ({d.get('Title')}): Expected='{expected_inv}' | Actual='{actual_inv}'")
    if not match:
        all_correct = False

print("\n" + "=" * 50)
if all_correct:
    print("🎉 ALL SAMPLE ITEMS VERIFIED SUCCESSFULLY!")
else:
    print("❌ Discrepancy found.")
print("=" * 50)
