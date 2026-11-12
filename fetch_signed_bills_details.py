import json
import sys
from datetime import datetime
import requests

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except:
        pass

with open('C:/Users/fixadmin/TALLY/Haldiram/auth.json', 'r') as f:
    auth_data = json.load(f)

cookies = {c['name']: c['value'] for c in auth_data.get('cookies', [])}
headers = {'Accept': 'application/json, text/plain, */*'}

target_bills = ['13088', '13077', '12719', '12970', '12948', '12963', '12972', '12935', '12700', '12778', '12790', '12751', '12565', '12566', '10111', '10734', '3657']
target_set = set(target_bills)

print("Fetching invoice list from FieldAssist...")
url_recent = 'https://dms-hsfpl.fieldassist.io/api/v1/sales-invoices/?seller-id=19135&from-date=2026-10-01T00:00:00.000Z&to-date=2026-11-12T23:59:59.999Z&has-sku-detail=false'
url_older = 'https://dms-hsfpl.fieldassist.io/api/v1/sales-invoices/?seller-id=19135&from-date=2026-04-01T00:00:00.000Z&to-date=2026-10-01T00:00:00.000Z&has-sku-detail=false'

all_invoices = []
r1 = requests.get(url_recent, cookies=cookies, headers=headers, timeout=30)
if r1.status_code == 200:
    all_invoices.extend(r1.json())

r2 = requests.get(url_older, cookies=cookies, headers=headers, timeout=30)
if r2.status_code == 200:
    all_invoices.extend(r2.json())

matched_headers = {}
for inv in all_invoices:
    inv_no = str(inv.get('invoiceNo', ''))
    for b in target_set:
        if b in inv_no:
            matched_headers[b] = inv

print(f"Matched {len(matched_headers)} / {len(target_bills)} invoices. Now fetching full details...")

full_results = []
for b in target_bills:
    header = matched_headers.get(b)
    if not header:
        print(f"Missing header for bill {b}")
        continue
    inv_id = header['id']
    detail_url = f"https://dms-hsfpl.fieldassist.io/api/v1/sales-invoices/{inv_id}"
    det_resp = requests.get(detail_url, cookies=cookies, headers=headers, timeout=15)
    if det_resp.status_code == 200:
        det = det_resp.json()
        val = det.get('totalValueWithTcs') or det.get('totalValue') or det.get('netAmount') or 0
        party = det.get('buyerFirmName', 'N/A')
        date_str = (det.get('invoiceDate') or det.get('createdAt') or '')[:10]
        beat = det.get('beatName') or det.get('buyerBeatname') or 'N/A'
        inv_no = det.get('invoiceNo', '')
        
        # calculate days ago
        try:
            inv_dt = datetime.strptime(date_str, '%Y-%m-%d')
            days_ago = (datetime.now() - inv_dt).days
        except:
            days_ago = 0
            
        full_results.append({
            'billNo': b,
            'invoiceNo': inv_no,
            'buyerFirmName': party,
            'beatName': beat,
            'amount': round(float(val), 2),
            'date': date_str,
            'daysAgo': days_ago,
            'itemCount': len(det.get('items', [])),
            'raw': det
        })
        print(f"  [OK] Bill {b} | {party[:25]} | Rs.{val:,.2f} | Date: {date_str} ({days_ago} days ago)")
    else:
        print(f"  [ERR] Failed to fetch details for {b} (HTTP {det_resp.status_code})")

with open('C:/Users/fixadmin/TALLY/signed_bills_data.json', 'w', encoding='utf-8') as f:
    # Save without raw to keep clean summary
    clean_summary = [{k: v for k, v in r.items() if k != 'raw'} for r in full_results]
    json.dump(clean_summary, f, indent=2)

print("\nSummary saved to signed_bills_data.json successfully!")
