import sys, csv, re, json, requests
sys.stdout.reconfigure(encoding='utf-8')

# 1. Parse CSV mapping
exp_to_invoice_csv = {}
with open('_archive/SharePoint匯入_2_交易記錄-支出.csv', 'r', encoding='utf-8-sig') as f:
    reader = csv.reader(f)
    header = next(reader)
    for row in reader:
        if not row: continue
        title = row[0]
        m = re.match(r'^(EXP-\d+)', title)
        if m:
            exp_code = m.group(1)
            remarks = row[11] if len(row) > 11 else ''
            if '發票號:' in remarks:
                inv_match = re.search(r'發票號:\s*([^|]+)', remarks)
                if inv_match:
                    exp_to_invoice_csv[exp_code] = inv_match.group(1).strip()

print(f"Total CSV invoice mappings: {len(exp_to_invoice_csv)}")

# 2. Fetch all SharePoint items
with open('cookies.json', 'r', encoding='utf-8') as f:
    raw = json.load(f)
cookies = {c['name']: c['value'] for c in raw} if isinstance(raw, list) else raw
s = requests.Session()
s.trust_env = False
s.cookies.update(cookies)
SITE_URL = 'https://k35n.sharepoint.com/sites/CHUNKING'
GUID_EXPENSES = 'a09172c2-2be4-4b12-8dfd-418a6fbe0c6d'

print("Fetching all items from SharePoint...")
all_items = []
url = f"{SITE_URL}/_api/web/lists(guid'{GUID_EXPENSES}')/items?$select=Id,Title,Invoice_x0020_No_x002e_&$top=5000"
while url:
    r = s.get(url, headers={'Accept': 'application/json;odata=verbose'})
    data = r.json()['d']
    all_items.extend(data['results'])
    url = data.get('__next')

print(f"Total SharePoint items: {len(all_items)}")

# 3. Build updates list
updates = []
already_done = []
no_invoice = []

for it in all_items:
    item_id = it['Id']
    title = str(it.get('Title') or '')
    current_inv = str(it.get('Invoice_x0020_No_x002e_') or '').strip()
    m = re.match(r'^(EXP-\d+)', title)
    if not m:
        no_invoice.append((item_id, title))
        continue
    exp_code = m.group(1)
    num = int(exp_code.split('-')[1])
    target_inv = exp_to_invoice_csv.get(exp_code) or exp_to_invoice_csv.get(f"EXP-{num:05d}")
    if not target_inv:
        no_invoice.append((item_id, title))
        continue
    
    if current_inv == target_inv:
        already_done.append((item_id, title, current_inv))
    else:
        updates.append({
            "Id": item_id,
            "Title": title,
            "InvoiceNo": target_inv
        })

print(f"Total items needing update: {len(updates)}")
print(f"Total items already matching target: {len(already_done)}")
print(f"Total items with no invoice in historical data: {len(no_invoice)}")

out_path = "sp_invoice_backfill_updates.json"
with open(out_path, 'w', encoding='utf-8') as f:
    json.dump(updates, f, ensure_ascii=False, indent=2)

print(f"Saved update list to {out_path} ({len(updates)} records)")
