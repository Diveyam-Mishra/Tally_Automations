import sys
import os
import re
import json
import argparse
from datetime import datetime
import time
import requests

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except:
        pass

def format_date_for_tally(inv):
    # Try ISO strings first (e.g. 2026-10-11T19:30:00.000Z)
    created_at = inv.get('invoiceDate') or inv.get('createdAt')
    if created_at and isinstance(created_at, str):
        try:
            # Parse UTC ISO timestamp and convert to IST (+5:30)
            clean_iso = created_at.replace('Z', '+00:00')
            dt = datetime.fromisoformat(clean_iso)
            if dt.tzinfo is not None:
                # Add 5 hours 30 minutes for Indian Standard Time
                dt_ist = dt.astimezone() if hasattr(dt, 'astimezone') else dt
                from datetime import timezone, timedelta
                dt_ist = dt.astimezone(timezone(timedelta(hours=5, minutes=30)))
                return dt_ist.strftime("%Y%m%d")
            else:
                from datetime import timedelta
                dt_ist = dt + timedelta(hours=5, minutes=30)
                return dt_ist.strftime("%Y%m%d")
        except Exception:
            if len(created_at) >= 10:
                clean_date = created_at[:10].replace('-', '')
                if clean_date.isdigit() and len(clean_date) == 8:
                    return clean_date

    ts = inv.get('timeStamp')
    if ts:
        try:
            ts_num = int(ts)
            if ts_num > 1e11:
                ts_num /= 1000
            dt = datetime.fromtimestamp(ts_num)
            return dt.strftime("%Y%m%d")
        except:
            pass

    return datetime.now().strftime("%Y%m%d")

def escape_xml(s):
    if not s:
        return ""
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;").replace("'", "&apos;")

def get_item_name(it):
    """
    Returns clean name for Tally stock item.
    """
    name = it.get('productDescription') or it.get('name') or "Item"
    return name.strip()

def build_all_masters_xml(invoices, company="ANAND MANGAL_FY26-27"):
    """
    Builds master creation XML for all unique Customers (Sundry Debtors)
    AND all unique Stock Items (under 'Haldiram' group).
    """
    customers = {}
    stock_items = {}

    for inv in invoices:
        cust_name = (inv.get('buyerFirmName') or '').strip()
        if cust_name and cust_name not in customers:
            customers[cust_name] = {
                'name': cust_name,
                'gstin': (inv.get('buyerGstin') or '').strip(),
                'address': (inv.get('buyerShippingAddress') or inv.get('buyerBillingAddress') or '').strip(),
                'pincode': (inv.get('buyerPinCode') or '').strip(),
                'state': (inv.get('buyerState') or 'MADHYA PRADESH').strip()
            }

        for it in inv.get('items', []):
            item_name = get_item_name(it)
            if item_name and item_name not in stock_items:
                stock_items[item_name] = {
                    'name': item_name,
                    'hsn': it.get('hsnCode') or '',
                    'unit': 'PCS' # Tally uses PCS
                }

    messages = []

    # 1. Base Groups and Common Ledgers
    common_masters_xml = """        <TALLYMESSAGE xmlns:UDF="TallyUDF">
          <STOCKGROUP NAME="Haldiram" ACTION="Create">
            <NAME.LIST><NAME>Haldiram</NAME></NAME.LIST>
            <PARENT/>
          </STOCKGROUP>
        </TALLYMESSAGE>
        <TALLYMESSAGE xmlns:UDF="TallyUDF">
          <LEDGER NAME="Sales - Haldiram" ACTION="Create">
            <NAME.LIST><NAME>Sales - Haldiram</NAME></NAME.LIST>
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
    messages.append(common_masters_xml)

    # 2. Customer Ledgers
    for c in customers.values():
        name_esc = escape_xml(c['name'])
        state_esc = escape_xml(c['state'].title() if c['state'] else "Madhya Pradesh")
        gstin_esc = escape_xml(c['gstin'])
        reg_type = "Regular" if c['gstin'] else "Unregistered"

        ledger_xml = [
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
            ledger_xml.append(f'            <PARTYGSTIN>{gstin_esc}</PARTYGSTIN>')

        if c['pincode']:
            ledger_xml.append(f'            <PINCODE>{escape_xml(c["pincode"])}</PINCODE>')

        if c['address']:
            ledger_xml.append(f'            <ADDRESS.LIST><ADDRESS>{escape_xml(c["address"])}</ADDRESS></ADDRESS.LIST>')

        ledger_xml.extend([
            '          </LEDGER>',
            '        </TALLYMESSAGE>'
        ])
        messages.append("\n".join(ledger_xml))

    # 2. Stock Item Masters
    for it in stock_items.values():
        name_esc = escape_xml(it['name'])
        unit_esc = escape_xml(it['unit'])
        hsn_esc = escape_xml(it['hsn'])

        item_xml = [
            '        <TALLYMESSAGE xmlns:UDF="TallyUDF">',
            f'          <STOCKITEM NAME="{name_esc}" ACTION="Create">',
            '            <NAME.LIST>',
            f'              <NAME>{name_esc}</NAME>',
            '            </NAME.LIST>',
            '            <PARENT>Haldiram</PARENT>',
            f'            <BASEUNITS>{unit_esc}</BASEUNITS>',
            '            <ISBATCHWISEON>Yes</ISBATCHWISEON>',
            '            <GSTAPPLICABLE>&#47; Applicable</GSTAPPLICABLE>',
        ]
        if hsn_esc:
            item_xml.append(f'            <HSNCODE>{hsn_esc}</HSNCODE>')

        item_xml.extend([
            '          </STOCKITEM>',
            '        </TALLYMESSAGE>'
        ])
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

def build_sales_voucher_xml(inv, company="ANAND MANGAL_FY26-27", sales_ledger="Sales - Haldiram"):
    inv_no = inv.get('invoiceNo', 'SALES_INV')
    tally_date = format_date_for_tally(inv)
    customer_name = inv.get('buyerFirmName', 'Cash')
    customer_gstin = inv.get('buyerGstin') or ""

    total_val = float(inv.get('totalValueWithTcs') or inv.get('totalValue') or 0.0)
    cgst_val = float(inv.get('totalCGST') or 0.0)
    sgst_val = float(inv.get('totalSGST') or 0.0)
    igst_val = float(inv.get('totalIGST') or 0.0)
    
    items = inv.get('items', [])
    taxable_sum = sum(float(it.get('netValue') or it.get('grossValue') or 0.0) for it in items)
    
    computed_total = taxable_sum + cgst_val + sgst_val + igst_val
    round_off = round(total_val - computed_total, 2)

    xml_lines = [
        '        <TALLYMESSAGE xmlns:UDF="TallyUDF">',
        '          <VOUCHER VCHTYPE="Sales" ACTION="Create" OBJVIEW="Invoice Voucher View">',
        f'            <DATE>{tally_date}</DATE>',
        f'            <REFERENCEDATE>{tally_date}</REFERENCEDATE>',
        '            <VOUCHERTYPENAME>Sales</VOUCHERTYPENAME>',
        f'            <VOUCHERNUMBER>{escape_xml(inv_no)}</VOUCHERNUMBER>',
        f'            <REFERENCE>{escape_xml(inv_no)}</REFERENCE>',
        f'            <PARTYLEDGERNAME>{escape_xml(customer_name)}</PARTYLEDGERNAME>',
        f'            <BASICBUYERNAME>{escape_xml(customer_name)}</BASICBUYERNAME>',
        '            <PERSISTEDVIEW>Invoice Voucher View</PERSISTEDVIEW>',
        '            <ISINVOICE>Yes</ISINVOICE>',
    ]

    if customer_gstin:
        xml_lines.append(f'            <PARTYGSTIN>{escape_xml(customer_gstin)}</PARTYGSTIN>')

    xml_lines.append(f'            <AMOUNT>-{total_val:.2f}</AMOUNT>')

    # 1. Inventory Line Items (Credited: Outward Stock)
    for it in items:
        name_clean = escape_xml(get_item_name(it))
        qty = float(it.get('quantity') or 1.0)
        rate = float(it.get('price') or 0.0)
        taxable_item = float(it.get('netValue') or it.get('grossValue') or 0.0)
        batch = escape_xml(it.get('batchNo') or "Primary Batch")
        unit = "PCS" # Tally base unit is PCS

        xml_lines.extend([
            '            <ALLINVENTORYENTRIES.LIST>',
            f'              <STOCKITEMNAME>{name_clean}</STOCKITEMNAME>',
            '              <ISDEEMEDPOSITIVE>No</ISDEEMEDPOSITIVE>',
            f'              <RATE>{rate:.4f}/{unit}</RATE>',
            f'              <AMOUNT>{taxable_item:.2f}</AMOUNT>',
            f'              <ACTUALQTY> {qty:.1f} {unit}</ACTUALQTY>',
            f'              <BILLEDQTY> {qty:.1f} {unit}</BILLEDQTY>',
            '              <BATCHALLOCATIONS.LIST>',
            f'                <BATCHNAME>{batch}</BATCHNAME>',
            '                <GODOWNNAME>Main Location</GODOWNNAME>',
            f'                <AMOUNT>{taxable_item:.2f}</AMOUNT>',
            f'                <ACTUALQTY> {qty:.1f} {unit}</ACTUALQTY>',
            f'                <BILLEDQTY> {qty:.1f} {unit}</BILLEDQTY>',
            f'                <BATCHRATE>{rate:.4f}/{unit}</BATCHRATE>',
            '              </BATCHALLOCATIONS.LIST>',
            '              <ACCOUNTINGALLOCATIONS.LIST>',
            f'                <LEDGERNAME>{escape_xml(sales_ledger)}</LEDGERNAME>',
            '                <ISDEEMEDPOSITIVE>No</ISDEEMEDPOSITIVE>',
            f'                <AMOUNT>{taxable_item:.2f}</AMOUNT>',
            '              </ACCOUNTINGALLOCATIONS.LIST>',
            '            </ALLINVENTORYENTRIES.LIST>'
        ])

    # 2. Customer Ledger Entry (Debit)
    xml_lines.extend([
        '            <LEDGERENTRIES.LIST>',
        f'              <LEDGERNAME>{escape_xml(customer_name)}</LEDGERNAME>',
        '              <ISDEEMEDPOSITIVE>Yes</ISDEEMEDPOSITIVE>',
        f'              <AMOUNT>-{total_val:.2f}</AMOUNT>',
        '              <BILLALLOCATIONS.LIST>',
        f'                <NAME>{escape_xml(inv_no)}</NAME>',
        '                <BILLTYPE>New Ref</BILLTYPE>',
        f'                <AMOUNT>-{total_val:.2f}</AMOUNT>',
        '              </BILLALLOCATIONS.LIST>',
        '            </LEDGERENTRIES.LIST>'
    ])

    # Taxes (Credited in Sales)
    if cgst_val > 0.0:
        xml_lines.extend([
            '            <LEDGERENTRIES.LIST>',
            '              <LEDGERNAME>CGST</LEDGERNAME>',
            '              <ISDEEMEDPOSITIVE>No</ISDEEMEDPOSITIVE>',
            f'              <AMOUNT>{cgst_val:.2f}</AMOUNT>',
            '            </LEDGERENTRIES.LIST>'
        ])

    if sgst_val > 0.0:
        xml_lines.extend([
            '            <LEDGERENTRIES.LIST>',
            '              <LEDGERNAME>SGST</LEDGERNAME>',
            '              <ISDEEMEDPOSITIVE>No</ISDEEMEDPOSITIVE>',
            f'              <AMOUNT>{sgst_val:.2f}</AMOUNT>',
            '            </LEDGERENTRIES.LIST>'
        ])

    if igst_val > 0.0:
        xml_lines.extend([
            '            <LEDGERENTRIES.LIST>',
            '              <LEDGERNAME>IGST</LEDGERNAME>',
            '              <ISDEEMEDPOSITIVE>No</ISDEEMEDPOSITIVE>',
            f'              <AMOUNT>{igst_val:.2f}</AMOUNT>',
            '            </LEDGERENTRIES.LIST>'
        ])

    # Round Off
    if abs(round_off) >= 0.01:
        is_positive = "Yes" if round_off < 0 else "No"
        sign = "-" if round_off < 0 else ""
        xml_lines.extend([
            '            <LEDGERENTRIES.LIST>',
            '              <LEDGERNAME>Roundoff</LEDGERNAME>',
            f'              <ISDEEMEDPOSITIVE>{is_positive}</ISDEEMEDPOSITIVE>',
            f'              <AMOUNT>{sign}{abs(round_off):.2f}</AMOUNT>',
            '            </LEDGERENTRIES.LIST>'
        ])

    xml_lines.extend([
        '          </VOUCHER>',
        '        </TALLYMESSAGE>'
    ])

    return "\n".join(xml_lines)

def build_full_envelope(voucher_xmls, company="ANAND MANGAL_FY26-27"):
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
{chr(10).join(voucher_xmls)}
      </REQUESTDATA>
    </IMPORTDATA>
  </BODY>
</ENVELOPE>"""

def post_to_tally(tally_url, xml_data):
    headers = {'Content-Type': 'application/xml; charset=utf-8'}
    try:
        response = requests.post(tally_url, data=xml_data.encode('utf-8'), headers=headers, timeout=90)
        return response.status_code, response.text
    except requests.exceptions.RequestException as e:
        return None, str(e)

def fetch_existing_references(tally_url, company="ANAND MANGAL_FY26-27"):
    xml_request = f"""<ENVELOPE>
  <HEADER>
    <VERSION>1</VERSION>
    <TALLYREQUEST>Export</TALLYREQUEST>
    <TYPE>Collection</TYPE>
    <ID>AllRefsColl</ID>
  </HEADER>
  <BODY>
    <DESC>
      <STATICVARIABLES>
        <SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>
        <SVCURRENTCOMPANY>{company}</SVCURRENTCOMPANY>
      </STATICVARIABLES>
      <TDL>
        <TDLMESSAGE>
          <COLLECTION NAME="AllRefsColl">
            <TYPE>Voucher</TYPE>
            <FETCH>VOUCHERNUMBER,REFERENCE</FETCH>
          </COLLECTION>
        </TDLMESSAGE>
      </TDL>
    </DESC>
  </BODY>
</ENVELOPE>"""
    try:
        resp = requests.post(tally_url, data=xml_request.encode('utf-8'), headers={'Content-Type': 'application/xml; charset=utf-8'}, timeout=20)
        if resp.status_code == 200:
            refs = set(re.findall(r'<REFERENCE[^>]*>([^<]+)</REFERENCE>', resp.text))
            vchs = set(re.findall(r'<VOUCHERNUMBER[^>]*>([^<]+)</VOUCHERNUMBER>', resp.text))
            return refs | vchs
    except Exception as e:
        print(f"⚠️ Could not check existing vouchers in Tally: {e}")
    return set()

def main():
    parser = argparse.ArgumentParser(description="Generate and import FieldAssist Sales Invoices into Tally as Sales Vouchers.")
    parser.add_argument("--json", default="invoices_02-10-2026_sample_77.json", help="Path to fetched JSON file")
    parser.add_argument("--company", default="ANAND MANGAL_FY26-27", help="Tally Company Name")
    parser.add_argument("--sales-ledger", default="Sales - Haldiram", help="Sales Ledger Name (default: 'Sales - Haldiram')")
    parser.add_argument("--tally-ip", default="192.168.10.110", help="Tally Server IP (default: 192.168.10.110)")
    parser.add_argument("--tally-port", default="9000", help="Tally Server Port (default: 9000)")
    parser.add_argument("--save-xml", default="sales_tally_import.xml", help="Path to save generated XML")
    parser.add_argument("--dry-run", action="store_true", help="Generate XML and inspect without sending to Tally")
    parser.add_argument("--start-index", type=int, default=0, help="Start index for vouchers (default: 0)")

    args = parser.parse_args()

    if not os.path.exists(args.json):
        print(f"❌ JSON file not found: {args.json}")
        sys.exit(1)

    with open(args.json, encoding="utf-8") as f:
        invoices = json.load(f)

    print(f"\n=============================================================")
    print(f"🚀 Tally Sales Voucher & Masters Auto-Sync Pipeline")
    print(f"📂 Source JSON   : {args.json} ({len(invoices)} invoices)")
    print(f"🏢 Company       : {args.company}")
    print(f"📈 Sales Ledger  : {args.sales_ledger}")
    print(f"=============================================================\n")

    tally_url = f"http://{args.tally_ip}:{args.tally_port}/"

    # Step 0: Check for invoices already in Tally
    print("🔍 Checking for invoices that already exist in Tally...")
    existing_tally_refs = fetch_existing_references(tally_url, company=args.company)
    print(f"   Found {len(existing_tally_refs)} existing references/vouchers in Tally.")

    already_in_tally_list = []
    to_import_list = []

    for inv in invoices:
        inv_no = inv.get('invoiceNo')
        if inv_no in existing_tally_refs:
            already_in_tally_list.append(inv)
        else:
            to_import_list.append(inv)

    os.makedirs("already_in_tally", exist_ok=True)
    base_json_name = os.path.basename(args.json)
    already_path = os.path.join("already_in_tally", f"already_in_tally_{base_json_name}")

    if already_in_tally_list:
        with open(already_path, "w", encoding="utf-8") as f:
            json.dump(already_in_tally_list, f, indent=2)
        print(f"   💾 Saved {len(already_in_tally_list)} already-existing invoices -> {already_path}")

    print(f"   📊 Breakdown: Total Fetched={len(invoices)} | Already in Tally={len(already_in_tally_list)} | New to Import={len(to_import_list)}")

    if not to_import_list:
        print(f"\n🎉 All {len(invoices)} invoices already exist in Tally! Skipping import.")
        return

    invoices = to_import_list

    # Step 1: Build Customer and Stock Item Masters XML
    print("[1/2] Building Master Entities (Customers + Stock Items)...")
    masters_xml, cust_count, items_count = build_all_masters_xml(invoices, company=args.company)
    masters_xml_path = "sales_all_masters.xml"
    with open(masters_xml_path, "w", encoding="utf-8") as f:
        f.write(masters_xml)
    print(f"      Generated {cust_count} Customers + {items_count} Stock Items -> {masters_xml_path}")

    # Step 2: Build Sales Vouchers XML
    print("\n[2/2] Building Sales Vouchers...")
    voucher_xml_list = []
    total_batch_value = 0.0

    for idx, inv in enumerate(invoices, 1):
        inv_no = inv.get('invoiceNo')
        customer = inv.get('buyerFirmName')
        grand_total = float(inv.get('totalValueWithTcs') or inv.get('totalValue') or 0.0)
        total_batch_value += grand_total
        vch_xml = build_sales_voucher_xml(inv, company=args.company, sales_ledger=args.sales_ledger)
        voucher_xml_list.append(vch_xml)

    full_vouchers_xml = build_full_envelope(voucher_xml_list, company=args.company)
    with open(args.save_xml, "w", encoding="utf-8") as f:
        f.write(full_vouchers_xml)

    print(f"      Generated {len(voucher_xml_list)} sales vouchers -> {args.save_xml}")
    print(f"      Batch Grand Total: ₹{total_batch_value:,.2f}")

    if args.dry_run:
        print("\n🔍 DRY-RUN mode enabled. Files written, skipping push to Tally.")
        return

    # PUSH STEP 1: Push All Masters
    print(f"\n📡 [Step 1/2] Pushing {cust_count} Customers + {items_count} Stock Items to Tally at {tally_url}...")
    status, response = post_to_tally(tally_url, masters_xml)
    if status == 200:
        print("      Tally Response (Masters):")
        print("      " + response.replace("\n", "\n      "))
    else:
        print(f"❌ Failed to push masters ({status}): {response}")
        return

    # PUSH STEP 2: Push Sales Vouchers in Batches of 5
    BATCH_SIZE = 5
    if args.start_index > 0:
        print(f"⏩ Resuming from index {args.start_index} (skipping first {args.start_index} vouchers)...")
        voucher_xml_list = voucher_xml_list[args.start_index:]
        invoices = invoices[args.start_index:]

    total_chunks = (len(voucher_xml_list) + BATCH_SIZE - 1) // BATCH_SIZE
    print(f"\n📡 [Step 2/2] Pushing {len(voucher_xml_list)} Sales Vouchers to Tally in {total_chunks} batches (size={BATCH_SIZE})...")

    created_total = 0
    errors_total = 0
    exceptions_total = 0

    for chunk_idx in range(0, len(voucher_xml_list), BATCH_SIZE):
        batch = voucher_xml_list[chunk_idx:chunk_idx + BATCH_SIZE]
        batch_invoices = invoices[chunk_idx:chunk_idx + BATCH_SIZE]
        batch_num = (chunk_idx // BATCH_SIZE) + 1
        
        inv_summary = ", ".join([f"{inv.get('invoiceNo')} ({inv.get('buyerFirmName', '')[:15]})" for inv in batch_invoices])
        print(f"\n   📤 Sending Batch {batch_num}/{total_chunks} ({len(batch)} vouchers)...")
        print(f"      Invoices: {inv_summary}")

        batch_envelope = build_full_envelope(batch, company=args.company)
        status, response = post_to_tally(tally_url, batch_envelope)
        
        if status == 200:
            created_m = re.search(r'<CREATED>(\d+)</CREATED>', response)
            errors_m = re.search(r'<ERRORS>(\d+)</ERRORS>', response)
            exceptions_m = re.search(r'<EXCEPTIONS>(\d+)</EXCEPTIONS>', response)

            c_count = int(created_m.group(1)) if created_m else 0
            err_count = int(errors_m.group(1)) if errors_m else 0
            exc_count = int(exceptions_m.group(1)) if exceptions_m else 0

            created_total += c_count
            errors_total += err_count
            exceptions_total += exc_count

            print(f"      ✅ Batch {batch_num} Result: Created={c_count}, Errors={err_count}, Exceptions={exc_count} (Total Created: {created_total})")
            
            if exc_count > 0 or err_count > 0:
                print(f"      ❌ STOPPING! Tally reported exceptions/errors on Batch {batch_num}!")
                print(f"      Tally response details:\n{response}")
                break
        else:
            print(f"      ❌ Batch {batch_num} Failed with HTTP status {status}: {response}")
            errors_total += len(batch)
            print(f"      ❌ STOPPING pipeline due to network error.")
            break

        time.sleep(0.5)

    print("\n=============================================================")
    print(f"🎉 Sales Voucher Push Summary:")
    print(f"   Total Vouchers Attempted : {created_total + errors_total}")
    print(f"   Total Created Cleanly    : {created_total}/{len(voucher_xml_list)}")
    print(f"   Total Exceptions         : {exceptions_total}")
    print(f"   Total Errors             : {errors_total}")
    print("=============================================================")
    print("=============================================================")

if __name__ == "__main__":
    main()
