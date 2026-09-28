import os
import sys
import json
import re
import openpyxl
import requests
from collections import defaultdict
from datetime import datetime

sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = r"c:\Users\kmk112\Downloads\mitigation"
COOKIES_PATH = os.path.join(BASE_DIR, "cookies.json")
EXCEL_PATH = os.path.join(BASE_DIR, "cheque-new.xlsx")
SITE_URL = "https://k35n.sharepoint.com/sites/CHUNKING"
GUID_PROJECTS = "1958fe5e-336d-43a0-beb2-4da48df59f7b"
GUID_EXPENSES = "a09172c2-2be4-4b12-8dfd-418a6fbe0c6d"

def norm_str(s):
    if not s:
        return ''
    s = str(s).strip().replace('（', '(').replace('）', ')').replace('　', ' ')
    return re.sub(r'\s+', ' ', s).strip().lower()

def clean_payee_key(s):
    if not s:
        return ('', frozenset())
    s = str(s).strip().replace('（', '(').replace('）', ')').replace('　', ' ')
    # remove spaces between Chinese characters
    s = re.sub(r'(?<=[\u4e00-\u9fa5])\s+(?=[\u4e00-\u9fa5])', '', s)
    s = re.sub(r'\s+', ' ', s).strip().lower()
    zh = ''.join(re.findall(r'[\u4e00-\u9fa5]', s))
    en = set(re.findall(r'[a-zA-Z0-9]+', s))
    return (zh, frozenset(en))

def parse_num(val):
    if val is None:
        return None
    if isinstance(val, (int, float)):
        return round(float(val), 2)
    s = str(val).replace(',', '').strip()
    if not s:
        return None
    try:
        return round(float(s), 2)
    except:
        return None

def parse_date_str(val):
    if not val:
        return ''
    if isinstance(val, datetime):
        return val.strftime('%Y-%m-%d')
    s = str(val).strip()
    m = re.search(r'(\d{4})[-/](\d{1,2})[-/](\d{1,2})', s)
    if m:
        return f"{int(m.group(1)):04d}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
    return ''

def norm_chq(val):
    if not val:
        return ''
    s = str(val).strip().upper()
    s = re.sub(r'[^A-Z0-9]', '', s)
    return s

def main():
    print("1. Loading SharePoint cookies...")
    with open(COOKIES_PATH, 'r', encoding='utf-8') as f:
        raw_cookies = json.load(f)
    cookies = {c['name']: c['value'] for c in raw_cookies} if isinstance(raw_cookies, list) else raw_cookies

    session = requests.Session()
    session.trust_env = False
    session.cookies.update(cookies)

    print("2. Fetching all Projects from SharePoint...")
    all_projects = []
    url = f"{SITE_URL}/_api/web/lists(guid'{GUID_PROJECTS}')/items?$select=Id,Title&$top=5000"
    while url:
        res = session.get(url, headers={'Accept': 'application/json;odata=verbose'})
        data = res.json()['d']
        all_projects.extend(data['results'])
        url = data.get('__next')
    proj_map = {p['Id']: norm_str(p.get('Title')) for p in all_projects}
    print(f"Loaded {len(proj_map)} projects from SharePoint.")

    print("3. Fetching all Transactions from SharePoint...")
    all_sp = []
    url = f"{SITE_URL}/_api/web/lists(guid'{GUID_EXPENSES}')/items?$select=Id,Title,OData__x91d1__x984d_,OData__x5b50__x9805__x76ee_,OData__x6536__x6b3e__x4eba_,OData__x6240__x5c6c__x9805__x76ee_Id,OData__x652f__x7968__x7de8__x865f_,OData__x4ea4__x6613__x6642__x9593_,Invoice_x0020_No_x002e_,RecordStatus&$top=5000"
    while url:
        res = session.get(url, headers={'Accept': 'application/json;odata=verbose'})
        data = res.json()['d']
        all_sp.extend(data['results'])
        url = data.get('__next')
    print(f"Loaded {len(all_sp)} SharePoint transactions.")

    print("4. Loading Excel sheet '支出' from cheque-new.xlsx...")
    wb = openpyxl.load_workbook(EXCEL_PATH, read_only=True, data_only=True)
    sheet = wb['支出']

    excel_rows = []
    for i, row in enumerate(sheet.iter_rows(values_only=True)):
        if i < 2:
            continue
        chq_val = row[0]
        chq10 = row[10]
        date_val = row[6]
        payee = row[8] if row[8] is not None else row[7]
        proj = row[13]
        subcat = row[15]
        amt = parse_num(row[16]) if row[16] is not None else parse_num(row[9])
        inv = str(row[18] or '').strip()

        if any([chq_val, chq10, payee, proj, subcat, amt, inv]):
            excel_rows.append({
                'row_idx': i + 1,
                'chq': norm_chq(chq_val) or norm_chq(chq10),
                'date': parse_date_str(date_val),
                'proj': norm_str(proj),
                'payee_str': norm_str(payee),
                'payee_key': clean_payee_key(payee),
                'amt': amt,
                'subcat': norm_str(subcat),
                'inv': inv,
                'used': False
            })
    print(f"Loaded {len(excel_rows)} rows from Excel sheet '支出'.")

    # Index Excel rows
    # Tier 1: (proj, payee_key, amt, subcat)
    excel_t1 = defaultdict(list)
    # Tier 2: (payee_key, amt, subcat) for unassigned / empty proj
    excel_t2_unassigned = defaultdict(list)

    for idx, r in enumerate(excel_rows):
        k1 = (r['proj'], r['payee_key'], r['amt'], r['subcat'])
        excel_t1[k1].append(idx)
        k2 = (r['payee_key'], r['amt'], r['subcat'])
        excel_t2_unassigned[k2].append(idx)

    # Perform Matching
    matched_count = 0
    updates = []
    unchanged_count = 0
    emptied_count = 0

    for sp in all_sp:
        sp_id = sp['Id']
        pid = sp.get('OData__x6240__x5c6c__x9805__x76ee_Id')
        sp_proj = proj_map.get(pid, '')
        sp_payee_str = norm_str(sp.get('OData__x6536__x6b3e__x4eba_'))
        sp_payee_key = clean_payee_key(sp.get('OData__x6536__x6b3e__x4eba_'))
        sp_amt = parse_num(sp.get('OData__x91d1__x984d_'))
        sp_subcat = norm_str(sp.get('OData__x5b50__x9805__x76ee_'))
        sp_chq = norm_chq(sp.get('OData__x652f__x7968__x7de8__x865f_')) or norm_chq(sp.get('Title'))
        sp_date = parse_date_str(sp.get('OData__x4ea4__x6613__x6642__x9593_'))
        current_inv = str(sp.get('Invoice_x0020_No_x002e_') or '').strip()

        # Step A: Exact 4-field match
        k1 = (sp_proj, sp_payee_key, sp_amt, sp_subcat)
        candidate_indices = excel_t1.get(k1, [])
        
        # Step B: If unassigned in SP, match on 3 fields
        if not candidate_indices and (sp_proj == 'unassigned' or not sp_proj):
            k2 = (sp_payee_key, sp_amt, sp_subcat)
            candidate_indices = excel_t2_unassigned.get(k2, [])

        chosen_idx = None
        if candidate_indices:
            # Filter unused first
            unused = [idx for idx in candidate_indices if not excel_rows[idx]['used']]
            pool = unused if unused else candidate_indices

            # Try to disambiguate by cheque number or date if multiple
            if len(pool) == 1:
                chosen_idx = pool[0]
            else:
                # Disambiguate by cheque
                chq_matches = [idx for idx in pool if sp_chq and excel_rows[idx]['chq'] and (sp_chq == excel_rows[idx]['chq'] or sp_chq in excel_rows[idx]['chq'] or excel_rows[idx]['chq'] in sp_chq)]
                if len(chq_matches) == 1:
                    chosen_idx = chq_matches[0]
                elif len(chq_matches) > 1:
                    # Disambiguate by date
                    date_matches = [idx for idx in chq_matches if sp_date and excel_rows[idx]['date'] == sp_date]
                    chosen_idx = date_matches[0] if date_matches else chq_matches[0]
                else:
                    # Disambiguate by date
                    date_matches = [idx for idx in pool if sp_date and excel_rows[idx]['date'] == sp_date]
                    chosen_idx = date_matches[0] if date_matches else pool[0]

        if chosen_idx is not None:
            excel_rows[chosen_idx]['used'] = True
            matched_inv = excel_rows[chosen_idx]['inv']
            matched_count += 1
        else:
            # "If there is no matching items in the excel sheet, just leave the invoice number empty."
            matched_inv = ""

        # Check if SharePoint needs update
        if current_inv != matched_inv:
            updates.append({
                'Id': sp_id,
                'Title': sp.get('Title'),
                'CurrentInvoice': current_inv,
                'TargetInvoice': matched_inv,
                'Matched': (chosen_idx is not None)
            })
            if not matched_inv:
                emptied_count += 1
        else:
            unchanged_count += 1

    print("\n=== MATCHING AUDIT SUMMARY ===")
    print(f"Total SharePoint Items: {len(all_sp)}")
    print(f"Total Successfully Matched to Excel: {matched_count} ({matched_count/len(all_sp)*100:.2f}%)")
    print(f"Items with no Excel Match (Invoice emptied): {len(all_sp) - matched_count}")
    print(f"Items requiring SharePoint update: {len(updates)}")
    print(f"Items already matching target: {unchanged_count}")
    print(f"Items where invoice will be cleared: {emptied_count}")

    # Inspect Sample Updates
    print("\nSample 10 updates where invoice is being changed or corrected:")
    changed = [u for u in updates if u['CurrentInvoice'] and u['TargetInvoice'] and u['CurrentInvoice'] != u['TargetInvoice']]
    for u in changed[:10]:
        print(f"  ID {u['Id']} ({u['Title']}): '{u['CurrentInvoice']}' -> '{u['TargetInvoice']}'")

    print("\nSample 10 updates where wrong invoice is being cleared (no excel match):")
    cleared = [u for u in updates if u['CurrentInvoice'] and not u['TargetInvoice']]
    for u in cleared[:10]:
        print(f"  ID {u['Id']} ({u['Title']}): '{u['CurrentInvoice']}' -> EMPTY")

    out_file = os.path.join(BASE_DIR, "sp_invoice_rematch_plan.json")
    with open(out_file, 'w', encoding='utf-8') as f:
        json.dump(updates, f, ensure_ascii=False, indent=2)
    print(f"\nSaved rematch update plan to {out_file} ({len(updates)} records).")

if __name__ == '__main__':
    main()
