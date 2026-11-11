import os
import sys
import re
import csv
import glob
import time
import argparse
import difflib
import requests
from datetime import datetime

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except:
        pass

# Known 84 Cream Bell items in Tally for instant, accurate matching
TALLY_ITEMS = [
  "American Nuts 700ml", "American Nuts 700ml 2P", "American Nuts Cup 110ml",
  "Baby Chocho 30ml", "Belgian Chocolate 700ml", "Belgian Chocolate 700ml 2p",
  "Belgian Cookie Fudge Cup 110ml", "Black Current 700ml 2p", "Black Current  Cone 105ml",
  "Butter Crunch 70ml", "Butter Scotch 700ml", "Butter Scotch 700ml 2P",
  "Butter Scotch BP 5000ml 1P", "Butter Scotch Cup 85ml", "Caramel B/S Tub 750ml",
  "Cassata Chops 150ml", "Centre Treat 70ml", "Chocho Crrunch 30ml",
  "Chocholate Cup 85ml", "Choco Crrunch 30ml", "Chocolate BP 5000ml 1P",
  "Chocolate Cup 85ml", "Choco Vanilla Mini Choc 30ml", "Cookies & Cream Disc Cone 105ml",
  "Cotton Candy 80ml", "Cotton Candy Cone 105ml", "Creamy Vanilla 700ml",
  "Creamy Vanilla 700ml 2P", "Crunchy Butterscotch Cone 105ml", "Crunchy Butterscotch Cone 60ml",
  "Double Chocolate Cone 105ml", "Double Chocolate Cone 60ml", "French Vanilla Cup 90ml",
  "Icy Licks Milky Mango 50ml", "Icy Orange Lick 50ml", "Kaju Kishmish 700ml",
  "Kaju Kishmish 700ml 2P", "Kaju Pista Kulfi 70ml", "Kesar Badam 700ml 2P",
  "Kesar Badam Kulfi 55ml", "Kesar Mawa Kulfi 65ml", "Kesar Pista 700ml",
  "Kesar Pista 700ml 2P", "Kesar Pista Cup 110ml", "Lagoon Slush Lick 50ml",
  "Mango 700ml", "Mango 700ml 2P", "Mango BP 5000ml 1P", "Mango Dolly 60ml",
  "Matka Kulfi 110ml", "Mawa Malai 40ml", "Maxxum Caramel B/S 80ml",
  "Maxxum Choco Almond 80ml", "Maxxum Choco Brownie Cone 110ml", "Maxxum Choco Hazelnut Cone 110ml",
  "Maxxum Silky Chocolate 80ml", "No Added Sugar Chocolate Cup 110ml", "No Added Sugar Vanilla Cup 110ml",
  "Nutty Chocolate Disc Cone 105ml", "Pista Cone 105ml", "Rabri Malai 700ml 2P",
  "Rabri Malai Kulfi 55ml", "Raj Bhog Kulfi 55ml", "Rasmalai Kulfi 55ml",
  "Royal Dry Fruit Cup 110ml", "Royal RajBhog 700ml", "Royal RajBhog 700ml 2P",
  "Royal Rajwadi 40ml", "Sacch Mucch Aam 65ml", "Sandwich Vanilla 80ml",
  "Shahi Kulfi 55ml", "Strawberry 700ml", "Strawberry 700ml 2P",
  "Strawberry BP 5000ml 1P", "Strawberry Cup 50ml", "Strawberry Dolly 60ml",
  "Sundae Multi Ripple 125ml", "Tutty Fruity 700ml", "Tutty Fruity 700ml 2P",
  "Vanilla BP 5000ml 1P", "Vanilla Choc 65ml", "Vanilla Choco Cone 100ml",
  "Vanilla Choco Cone 35ml", "Vanilla Cup 50ml"
]

def escape_xml(s):
    if not s:
        return ""
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;").replace("'", "&apos;")

def match_stock_item(raw_name, tally_items):
    cleaned = re.sub(r'^\d+[- ]+', '', raw_name)
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    c_lower = cleaned.lower()
    
    # 100ML normalization
    c_lower = re.sub(r'\b[io0]{3}ml', '100ml', c_lower)
    
    vol_match = re.search(r'(\d+)\s*ml', c_lower)
    vol = vol_match.group(1) if vol_match else ""
    
    candidates = list(tally_items or TALLY_ITEMS)
    if vol:
        vol_c = [it for it in candidates if f"{vol}ml" in it.lower()]
        if vol_c:
            candidates = vol_c

    best_match = None
    best_score = 0.0
    for it in candidates:
        i_lower = it.lower()
        if i_lower == c_lower:
            return it
        ratio = difflib.SequenceMatcher(None, c_lower, i_lower).ratio()
        if ratio > best_score:
            best_score = ratio
            best_match = it
            
    if best_score >= 0.40:
        return best_match
    return cleaned

def get_tally_masters(tally_url, company):
    stock_items = set()
    existing_vouchers = set()

    # Query Cream Bell Stock Items
    xml_items = f"""<ENVELOPE>
  <HEADER><VERSION>1</VERSION><TALLYREQUEST>Export</TALLYREQUEST><TYPE>Collection</TYPE><ID>StockColl</ID></HEADER>
  <BODY>
    <DESC>
      <STATICVARIABLES><SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT><SVCURRENTCOMPANY>{company}</SVCURRENTCOMPANY></STATICVARIABLES>
      <TDL>
        <TDLMESSAGE>
          <COLLECTION NAME="StockColl">
            <TYPE>StockItem</TYPE>
            <FETCH>Name,Parent</FETCH>
            <FILTER>IsCB</FILTER>
          </COLLECTION>
          <SYSTEM TYPE="Formulae" NAME="IsCB">$Parent = "Cream Bell"</SYSTEM>
        </TDLMESSAGE>
      </TDL>
    </DESC>
  </BODY>
</ENVELOPE>"""
    try:
        r = requests.post(tally_url, data=xml_items.encode('utf-8'), headers={'Content-Type': 'application/xml'}, timeout=6)
        stock_items = set(re.findall(r'<NAME[^>]*>([^<]+)</NAME>', r.text))
    except Exception as e:
        print(f"⚠️ Warning: Could not fetch stock items from Tally: {e}")

    # Query Existing Vouchers for Deduplication
    xml_vch = f"""<ENVELOPE>
  <HEADER><VERSION>1</VERSION><TALLYREQUEST>Export</TALLYREQUEST><TYPE>Collection</TYPE><ID>VchColl</ID></HEADER>
  <BODY>
    <DESC>
      <STATICVARIABLES><SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT><SVCURRENTCOMPANY>{company}</SVCURRENTCOMPANY></STATICVARIABLES>
      <TDL>
        <TDLMESSAGE>
          <COLLECTION NAME="VchColl">
            <TYPE>Voucher</TYPE>
            <FETCH>VoucherNumber,Reference</FETCH>
          </COLLECTION>
        </TDLMESSAGE>
      </TDL>
    </DESC>
  </BODY>
</ENVELOPE>"""
    try:
        r = requests.post(tally_url, data=xml_vch.encode('utf-8'), headers={'Content-Type': 'application/xml'}, timeout=6)
        for v in re.findall(r'<VOUCHERNUMBER[^>]*>([^<]+)</VOUCHERNUMBER>', r.text):
            existing_vouchers.add(v.strip().upper())
        for ref in re.findall(r'<REFERENCE[^>]*>([^<]+)</REFERENCE>', r.text):
            existing_vouchers.add(ref.strip().upper())
    except Exception as e:
        print(f"⚠️ Warning: Could not fetch existing vouchers: {e}")

    return stock_items, existing_vouchers

def parse_creambell_csv(csv_path, tally_stock_items):
    with open(csv_path, 'r', encoding='utf-8', errors='ignore') as f:
        rows = list(csv.DictReader(f))

    invoices = {}
    for r in rows:
        inv_id = (r.get('invoice id') or '').strip()
        if not inv_id:
            continue
            
        if inv_id not in invoices:
            dt_raw = (r.get('invoice date') or '').strip()
            # Convert 2026-10-31 to 20261031
            tally_date = dt_raw.replace('-', '') if dt_raw else datetime.now().strftime('%Y%m%d')
            
            invoices[inv_id] = {
                'invoiceNo': inv_id,
                'tallyDate': tally_date,
                'dateStr': dt_raw,
                'buyerName': (r.get('customer name') or 'Retailer').strip(),
                'gstin': (r.get('gstn') or '').strip(),
                'state': 'Madhya Pradesh',
                'items': []
            }

        item_raw_name = (r.get('item name') or '').strip()
        matched_item = match_stock_item(item_raw_name, tally_stock_items)

        try:
            qty = float(r.get('total outer') or 1.0)
            rate = float(r.get('outer price') or 0.0)
            disc = float(r.get('discount (line + bill level)') or 0.0)
            tax_amt = float(r.get('tax amount') or 0.0)
            inv_val = float(r.get('invoice value') or (qty * rate + tax_amt))
            taxable = round(qty * rate - disc, 2)
        except:
            qty, rate, disc, tax_amt, inv_val, taxable = 1.0, 0.0, 0.0, 0.0, 0.0, 0.0

        invoices[inv_id]['items'].append({
            'raw_name': item_raw_name,
            'name': matched_item,
            'qty': qty,
            'rate': rate,
            'discount': disc,
            'taxable': taxable,
            'tax_amt': tax_amt,
            'inv_val': inv_val,
            'unit': 'BX'
        })

    return list(invoices.values())

def build_masters_xml(invoices, company="ANAND MANGAL_FY26-27"):
    customers = {}
    stock_items = {}

    for inv in invoices:
        c_name = inv['buyerName']
        if c_name and c_name not in customers:
            customers[c_name] = {
                'name': c_name,
                'gstin': inv.get('gstin', ''),
                'state': inv.get('state', 'Madhya Pradesh')
            }

        for it in inv['items']:
            i_name = it['name']
            if i_name and i_name not in stock_items:
                stock_items[i_name] = {
                    'name': i_name,
                    'unit': it.get('unit', 'BX')
                }

    messages = []
    # 1. Base groups & common ledgers
    common_xml = """        <TALLYMESSAGE xmlns:UDF="TallyUDF">
          <STOCKGROUP NAME="Cream Bell" ACTION="Create">
            <NAME.LIST><NAME>Cream Bell</NAME></NAME.LIST>
            <PARENT/>
          </STOCKGROUP>
        </TALLYMESSAGE>
        <TALLYMESSAGE xmlns:UDF="TallyUDF">
          <LEDGER NAME="Sales - Cream Bell" ACTION="Create">
            <NAME.LIST><NAME>Sales - Cream Bell</NAME></NAME.LIST>
            <PARENT>Sales Accounts</PARENT>
            <ISBILLWISEON>No</ISBILLWISEON>
            <AFFECTSSTOCK>Yes</AFFECTSSTOCK>
          </LEDGER>
        </TALLYMESSAGE>
        <TALLYMESSAGE xmlns:UDF="TallyUDF">
          <LEDGER NAME="CGST" ACTION="Create">
            <NAME.LIST><NAME>CGST</NAME></NAME.LIST>
            <PARENT>Duties &amp; Taxes</PARENT>
            <TAXTYPE>GST</TAXTYPE>
            <GSTDUTYHEAD>Central Tax</GSTDUTYHEAD>
          </LEDGER>
        </TALLYMESSAGE>
        <TALLYMESSAGE xmlns:UDF="TallyUDF">
          <LEDGER NAME="SGST" ACTION="Create">
            <NAME.LIST><NAME>SGST</NAME></NAME.LIST>
            <PARENT>Duties &amp; Taxes</PARENT>
            <TAXTYPE>GST</TAXTYPE>
            <GSTDUTYHEAD>State Tax</GSTDUTYHEAD>
          </LEDGER>
        </TALLYMESSAGE>
        <TALLYMESSAGE xmlns:UDF="TallyUDF">
          <LEDGER NAME="Roundoff" ACTION="Create">
            <NAME.LIST><NAME>Roundoff</NAME></NAME.LIST>
            <PARENT>Indirect Expenses</PARENT>
          </LEDGER>
        </TALLYMESSAGE>"""
    messages.append(common_xml)

    # 2. Customers
    for c in customers.values():
        name_esc = escape_xml(c['name'])
        state_esc = escape_xml(c['state'])
        gstin_esc = escape_xml(c['gstin'])
        reg_type = "Regular" if gstin_esc else "Unregistered"

        cust_xml = [
            '        <TALLYMESSAGE xmlns:UDF="TallyUDF">',
            f'          <LEDGER NAME="{name_esc}" ACTION="Create">',
            '            <NAME.LIST>',
            f'              <NAME>{name_esc}</NAME>',
            '            </NAME.LIST>',
            '            <PARENT>Sundry Debtors</PARENT>',
            '            <ISBILLWISEON>Yes</ISBILLWISEON>',
            '            <AFFECTSSTOCK>No</AFFECTSSTOCK>',
            '            <COUNTRYNAME>India</COUNTRYNAME>',
            f'            <LEDSTATENAME>{state_esc}</LEDSTATENAME>',
            f'            <GSTREGISTRATIONTYPE>{reg_type}</GSTREGISTRATIONTYPE>',
        ]
        if gstin_esc:
            cust_xml.append(f'            <PARTYGSTIN>{gstin_esc}</PARTYGSTIN>')
        cust_xml.extend([
            '          </LEDGER>',
            '        </TALLYMESSAGE>'
        ])
        messages.append("\n".join(cust_xml))

    # 3. Stock Items
    for it in stock_items.values():
        name_esc = escape_xml(it['name'])
        unit_esc = escape_xml(it['unit'])
        item_xml = [
            '        <TALLYMESSAGE xmlns:UDF="TallyUDF">',
            f'          <STOCKITEM NAME="{name_esc}" ACTION="Create">',
            '            <NAME.LIST>',
            f'              <NAME>{name_esc}</NAME>',
            '            </NAME.LIST>',
            '            <PARENT>Cream Bell</PARENT>',
            f'            <BASEUNITS>{unit_esc}</BASEUNITS>',
            '            <ISBATCHWISEON>No</ISBATCHWISEON>',
            '            <GSTAPPLICABLE>&#47; Applicable</GSTAPPLICABLE>',
            '            <HSNCODE>21050000</HSNCODE>',
            '          </STOCKITEM>',
            '        </TALLYMESSAGE>'
        ]
        messages.append("\n".join(item_xml))

    envelope = f"""<ENVELOPE>
  <HEADER>
    <TALLYREQUEST>Import Data</TALLYREQUEST>
  </HEADER>
  <BODY>
    <IMPORTDATA>
      <REQUESTDESC>
        <REPORTNAME>All Masters</REPORTNAME>
        <STATICVARIABLES>
          <SVCURRENTCOMPANY>{company}</SVCURRENTCOMPANY>
        </STATICVARIABLES>
      </REQUESTDESC>
      <REQUESTDATA>
{chr(10).join(messages)}
      </REQUESTDATA>
    </IMPORTDATA>
  </BODY>
</ENVELOPE>"""
    return envelope, len(customers), len(stock_items)

def build_voucher_tallymessage(inv, sales_ledger="Sales - Cream Bell"):
    inv_no = inv['invoiceNo']
    tally_date = inv['tallyDate']
    c_name = escape_xml(inv['buyerName'])
    c_gstin = escape_xml(inv.get('gstin', ''))
    items = inv['items']

    taxable_sum = sum(it['taxable'] for it in items)
    tax_amt_sum = sum(it['tax_amt'] for it in items)
    cgst_val = round(tax_amt_sum / 2.0, 2)
    sgst_val = round(tax_amt_sum / 2.0, 2)
    
    computed_total = taxable_sum + cgst_val + sgst_val
    rounded_total = round(computed_total)
    round_off = round(rounded_total - computed_total, 2)
    total_val = float(rounded_total)

    xml_lines = [
        '        <TALLYMESSAGE xmlns:UDF="TallyUDF">',
        '          <VOUCHER VCHTYPE="Sales" ACTION="Create" OBJVIEW="Invoice Voucher View">',
        f'            <DATE>{tally_date}</DATE>',
        f'            <REFERENCEDATE>{tally_date}</REFERENCEDATE>',
        '            <VOUCHERTYPENAME>Sales</VOUCHERTYPENAME>',
        f'            <VOUCHERNUMBER>{escape_xml(inv_no)}</VOUCHERNUMBER>',
        f'            <REFERENCE>{escape_xml(inv_no)}</REFERENCE>',
        f'            <PARTYLEDGERNAME>{c_name}</PARTYLEDGERNAME>',
        f'            <BASICBUYERNAME>{c_name}</BASICBUYERNAME>',
        f'            <NARRATION>Cream Bell Invoice {escape_xml(inv_no)}</NARRATION>',
        '            <PERSISTEDVIEW>Invoice Voucher View</PERSISTEDVIEW>',
        '            <ISINVOICE>Yes</ISINVOICE>',
    ]
    if c_gstin:
        xml_lines.append(f'            <PARTYGSTIN>{c_gstin}</PARTYGSTIN>')

    xml_lines.append(f'            <AMOUNT>-{total_val:.2f}</AMOUNT>')

    # 1. Line Items
    for it in items:
        name_clean = escape_xml(it['name'])
        qty = float(it['qty'])
        rate = float(it['rate'])
        taxable = float(it['taxable'])
        unit = it.get('unit', 'BX')

        xml_lines.extend([
            '            <ALLINVENTORYENTRIES.LIST>',
            f'              <STOCKITEMNAME>{name_clean}</STOCKITEMNAME>',
            '              <ISDEEMEDPOSITIVE>No</ISDEEMEDPOSITIVE>',
            f'              <RATE>{rate:.2f}/{unit}</RATE>',
            f'              <AMOUNT>{taxable:.2f}</AMOUNT>',
            f'              <ACTUALQTY> {qty:.1f} {unit}</ACTUALQTY>',
            f'              <BILLEDQTY> {qty:.1f} {unit}</BILLEDQTY>',
            '              <BATCHALLOCATIONS.LIST>',
            '                <GODOWNNAME>Main Location</GODOWNNAME>',
            '                <BATCHNAME>Primary Batch</BATCHNAME>',
            f'                <AMOUNT>{taxable:.2f}</AMOUNT>',
            f'                <ACTUALQTY> {qty:.1f} {unit}</ACTUALQTY>',
            f'                <BILLEDQTY> {qty:.1f} {unit}</BILLEDQTY>',
            f'                <BATCHRATE>{rate:.2f}/{unit}</BATCHRATE>',
            '              </BATCHALLOCATIONS.LIST>',
            '              <ACCOUNTINGALLOCATIONS.LIST>',
            f'                <LEDGERNAME>{escape_xml(sales_ledger)}</LEDGERNAME>',
            '                <ISDEEMEDPOSITIVE>No</ISDEEMEDPOSITIVE>',
            f'                <AMOUNT>{taxable:.2f}</AMOUNT>',
            '              </ACCOUNTINGALLOCATIONS.LIST>',
            '            </ALLINVENTORYENTRIES.LIST>'
        ])

    # 2. Customer Debit Entry
    xml_lines.extend([
        '            <LEDGERENTRIES.LIST>',
        f'              <LEDGERNAME>{c_name}</LEDGERNAME>',
        '              <ISDEEMEDPOSITIVE>Yes</ISDEEMEDPOSITIVE>',
        f'              <AMOUNT>-{total_val:.2f}</AMOUNT>',
        '              <BILLALLOCATIONS.LIST>',
        f'                <NAME>{escape_xml(inv_no)}</NAME>',
        '                <BILLTYPE>New Ref</BILLTYPE>',
        f'                <AMOUNT>-{total_val:.2f}</AMOUNT>',
        '              </BILLALLOCATIONS.LIST>',
        '            </LEDGERENTRIES.LIST>'
    ])

    # 3. Taxes
    if cgst_val > 0:
        xml_lines.extend([
            '            <LEDGERENTRIES.LIST>',
            '              <LEDGERNAME>CGST</LEDGERNAME>',
            '              <ISDEEMEDPOSITIVE>No</ISDEEMEDPOSITIVE>',
            f'              <AMOUNT>{cgst_val:.2f}</AMOUNT>',
            '            </LEDGERENTRIES.LIST>'
        ])
    if sgst_val > 0:
        xml_lines.extend([
            '            <LEDGERENTRIES.LIST>',
            '              <LEDGERNAME>SGST</LEDGERNAME>',
            '              <ISDEEMEDPOSITIVE>No</ISDEEMEDPOSITIVE>',
            f'              <AMOUNT>{sgst_val:.2f}</AMOUNT>',
            '            </LEDGERENTRIES.LIST>'
        ])

    # 4. Roundoff
    if abs(round_off) > 0.001:
        is_deemed = "No" if round_off > 0 else "Yes"
        # In Tally XML, Debit entries (ISDEEMEDPOSITIVE=Yes) must have negative amounts
        val_str = f"{round_off:.2f}" if round_off > 0 else f"-{abs(round_off):.2f}"
        xml_lines.extend([
            '            <LEDGERENTRIES.LIST>',
            '              <LEDGERNAME>Roundoff</LEDGERNAME>',
            f'              <ISDEEMEDPOSITIVE>{is_deemed}</ISDEEMEDPOSITIVE>',
            f'              <AMOUNT>{val_str}</AMOUNT>',
            '            </LEDGERENTRIES.LIST>'
        ])

    xml_lines.extend([
        '          </VOUCHER>',
        '        </TALLYMESSAGE>'
    ])
    return "\n".join(xml_lines)

def build_vouchers_envelope(tallymessages_xml, company="ANAND MANGAL_FY26-27"):
    return f"""<ENVELOPE>
  <HEADER>
    <TALLYREQUEST>Import Data</TALLYREQUEST>
  </HEADER>
  <BODY>
    <IMPORTDATA>
      <REQUESTDESC>
        <REPORTNAME>Vouchers</REPORTNAME>
        <STATICVARIABLES>
          <SVCURRENTCOMPANY>{company}</SVCURRENTCOMPANY>
        </STATICVARIABLES>
      </REQUESTDESC>
      <REQUESTDATA>
{tallymessages_xml}
      </REQUESTDATA>
    </IMPORTDATA>
  </BODY>
</ENVELOPE>"""

def import_csv_to_tally(csv_file, tally_ip="192.168.10.110", tally_port=9000, company="ANAND MANGAL_FY26-27", batch_size=5):
    tally_url = f"http://{tally_ip}:{tally_port}/"

    print("=" * 65)
    print("CREAM BELL CSV TO TALLYPRIME IMPORTER")
    print(f"Source CSV   : {csv_file}")
    print(f"Target Tally : {tally_url} ({company})")
    print("=" * 65)

    if not os.path.exists(csv_file):
        print(f"[!] Error: CSV file '{csv_file}' not found!")
        return

    print("\n[*] Connecting to Tally to query existing masters and vouchers...")
    stock_items, existing_vouchers = get_tally_masters(tally_url, company)
    print(f"   * Cream Bell items in Tally: {len(stock_items)}")
    print(f"   * Existing vouchers in Tally: {len(existing_vouchers)}")

    print(f"\n[*] Reading and parsing CSV: {os.path.basename(csv_file)}...")
    all_invoices = parse_creambell_csv(csv_file, stock_items)
    print(f"[+] Total invoices found in CSV: {len(all_invoices)}")

    # Deduplication
    new_invoices = []
    already_in_tally = []
    for inv in all_invoices:
        if inv['invoiceNo'].upper() in existing_vouchers:
            already_in_tally.append(inv['invoiceNo'])
        else:
            new_invoices.append(inv)

    print(f"\n[*] Deduplication Check:")
    print(f"   * Already in Tally : {len(already_in_tally)} (will skip)")
    print(f"   * New to Import    : {len(new_invoices)}")

    if not new_invoices:
        print("\n[+] All invoices from this CSV are ALREADY in Tally! Nothing to import.")
        return

    # 1. Push Masters
    print(f"\n[*] Step 1: Checking and Auto-Creating Masters for {len(new_invoices)} invoices...")
    m_xml, n_cust, n_items = build_masters_xml(new_invoices, company)
    try:
        r_m = requests.post(tally_url, data=m_xml.encode('utf-8'), headers={'Content-Type': 'application/xml'}, timeout=15)
        created = re.findall(r'<CREATED>(\d+)</CREATED>', r_m.text)
        altered = re.findall(r'<ALTERED>(\d+)</ALTERED>', r_m.text)
        errors = re.findall(r'<ERRORS>(\d+)</ERRORS>', r_m.text)
        print(f"   Masters Sync -> Created: {created or ['0']}, Altered: {altered or ['0']}, Errors: {errors or ['0']}")
    except Exception as e:
        print(f"   [!] Tally connection error during masters creation: {e}")
        return

    # 2. Push Vouchers in safe batches of 5
    print(f"\n[*] Step 2: Pushing {len(new_invoices)} Vouchers in batches of {batch_size}...")
    total_batches = (len(new_invoices) + batch_size - 1) // batch_size
    success_count = 0
    fail_count = 0

    for b_idx in range(total_batches):
        batch = new_invoices[b_idx * batch_size : (b_idx + 1) * batch_size]
        msg_xmls = [build_voucher_tallymessage(inv) for inv in batch]
        combined_msgs = "\n".join(msg_xmls)
        envelope_xml = build_vouchers_envelope(combined_msgs, company)

        batch_inv_nos = ", ".join(inv['invoiceNo'] for inv in batch)
        sys.stdout.write(f"   Batch [{b_idx + 1}/{total_batches}] ({len(batch)} vouchers): {batch_inv_nos}... ")
        sys.stdout.flush()

        try:
            r_v = requests.post(tally_url, data=envelope_xml.encode('utf-8'), headers={'Content-Type': 'application/xml'}, timeout=15)
            created = re.findall(r'<CREATED>(\d+)</CREATED>', r_v.text)
            altered = re.findall(r'<ALTERED>(\d+)</ALTERED>', r_v.text)
            errors = re.findall(r'<ERRORS>(\d+)</ERRORS>', r_v.text)
            exceptions = re.findall(r'<EXCEPTIONS>(\d+)</EXCEPTIONS>', r_v.text)

            n_created = int(created[0]) if created else 0
            n_altered = int(altered[0]) if altered else 0
            n_err = int(errors[0]) if errors else 0
            n_exc = int(exceptions[0]) if exceptions else 0

            if n_created > 0 or n_altered > 0:
                success_count += (n_created + n_altered)
                print(f"[OK] ({n_created} created, {n_altered} altered)")
            else:
                fail_count += len(batch)
                print(f"[FAILED] (Errors: {n_err}, Exceptions: {n_exc})")
                line_err = re.findall(r'<LINEERROR[^>]*>(.*?)</LINEERROR>', r_v.text)
                if line_err:
                    print(f"      Details: {line_err}")

        except Exception as e:
            fail_count += len(batch)
            print(f"[ERROR] {e}")

        time.sleep(0.4)

    print("\n" + "=" * 65)
    print("IMPORT SUMMARY:")
    print(f"   [+] Successfully Imported : {success_count} vouchers")
    print(f"   [-] Skipped (Already in)  : {len(already_in_tally)} vouchers")
    print(f"   [!] Failed to Import      : {fail_count} vouchers")
    print("=" * 65 + "\n")

def main():
    parser = argparse.ArgumentParser(description="Cream Bell CSV to Tally Automatic Importer")
    parser.add_argument("--file", help="Path to Cream Bell CSV file")
    parser.add_argument("--tally-ip", default="192.168.10.110", help="Tally PC IP (default: 192.168.10.110)")
    parser.add_argument("--tally-port", type=int, default=9000, help="Tally Port (default: 9000)")
    parser.add_argument("--company", default="ANAND MANGAL_FY26-27", help="Tally Company")
    parser.add_argument("--batch-size", type=int, default=5, help="Batch size (default: 5)")

    args = parser.parse_args()

    csv_file = args.file
    if not csv_file:
        # Auto-detect CSV files in current folder or parent
        cb_dir = os.path.dirname(__file__)
        csv_candidates = glob.glob(os.path.join(cb_dir, "*.csv"))
        if not csv_candidates:
            csv_candidates = glob.glob(os.path.join(os.path.dirname(cb_dir), "*.csv"))
            
        if not csv_candidates:
            print("❌ No CSV files found. Please place your Cream Bell CSV here and run again.")
            return

        # Sort by modification time, newest first
        csv_candidates.sort(key=lambda x: os.path.getmtime(x), reverse=True)
        if len(csv_candidates) == 1:
            csv_file = csv_candidates[0]
        else:
            print("\n📋 Available Cream Bell CSV files:")
            for idx, c in enumerate(csv_candidates[:5], 1):
                print(f"  [{idx}] {os.path.basename(c)}")
            prompt = f"\n👉 Select CSV [1-{min(5, len(csv_candidates))}] or press ENTER for latest [{os.path.basename(csv_candidates[0])}]: "
            try:
                choice = input(prompt).strip()
            except EOFError:
                choice = ""
            if choice.isdigit() and 1 <= int(choice) <= len(csv_candidates):
                csv_file = csv_candidates[int(choice) - 1]
            else:
                csv_file = csv_candidates[0]

    import_csv_to_tally(
        csv_file=csv_file,
        tally_ip=args.tally_ip,
        tally_port=args.tally_port,
        company=args.company,
        batch_size=args.batch_size
    )

if __name__ == "__main__":
    main()
