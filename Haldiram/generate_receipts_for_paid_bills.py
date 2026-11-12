"""
Generate Receipt Vouchers in Tally for Paid Bills (Excluding Signed Udhaari Bills)
================================================================================
Rule:
  - User provides list of signed/unpaid bills in SIGNED_BILLS_INPUT.xlsx (Haldiram bill format).
  - Program excludes those bills (leaving them as open market receivables).
  - Program generates Receipt Vouchers for all other delivered bills in the period.
  - Safe by default: runs in --dry-run / preview mode unless --post is explicitly passed.
"""

import os
import sys
import json
import argparse
import re
from datetime import datetime
import openpyxl
import requests

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except:
        pass

def load_signed_bill_numbers(excel_path):
    """
    Reads SIGNED_BILLS_INPUT.xlsx and returns a set of normalized bill numbers.
    Supports both short digits ('13088') and full format ('IN/19136/13088').
    """
    if not os.path.exists(excel_path):
        print(f"❌ Excel file not found: {excel_path}")
        return set()

    wb = openpyxl.load_workbook(excel_path, data_only=True)
    ws = wb.active
    
    signed_bills = set()
    for row in range(5, ws.max_row + 1):
        val = ws.cell(row=row, column=1).value
        if val is not None:
            clean_str = str(val).strip()
            if clean_str and not clean_str.lower().startswith('bill number'):
                # Extract digits or clean format
                signed_bills.add(clean_str)
                # Also store trailing digits if format like IN/19136/13088
                match = re.search(r'(\d+)$', clean_str)
                if match:
                    signed_bills.add(match.group(1))

    return signed_bills

def get_fieldassist_invoices(from_date_iso, to_date_iso, auth_path):
    """
    Fetches invoice headers from FieldAssist DMS for the target period.
    """
    if not os.path.exists(auth_path):
        print(f"⚠️ Auth file not found at {auth_path}. Cannot fetch from portal.")
        return []

    with open(auth_path, 'r', encoding='utf-8') as f:
        auth_data = json.load(f)

    cookies = {c['name']: c['value'] for c in auth_data.get('cookies', [])}
    headers = {'Accept': 'application/json, text/plain, */*'}

    url = (
        f"https://dms-hsfpl.fieldassist.io/api/v1/sales-invoices/?"
        f"seller-id=19135&from-date={from_date_iso}&to-date={to_date_iso}&has-sku-detail=false"
    )

    try:
        resp = requests.get(url, cookies=cookies, headers=headers, timeout=30)
        if resp.status_code == 200:
            return resp.json()
        else:
            print(f"⚠️ FieldAssist API error (HTTP {resp.status_code}): {resp.text[:200]}")
    except Exception as e:
        print(f"⚠️ FieldAssist request error: {e}")

    return []

def escape_xml(s):
    if not s:
        return ""
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;").replace("'", "&apos;")

def format_date_for_tally(dt_str):
    if not dt_str:
        return datetime.now().strftime("%Y%m%d")
    clean = dt_str[:10].replace('-', '')
    if len(clean) == 8 and clean.isdigit():
        return clean
    return datetime.now().strftime("%Y%m%d")

def get_inv_amount(inv):
    for key in ['totalValueWithTcs', 'totalValue', 'totalNetValue', 'totalGrossValue', 'netAmount', 'totalAmount']:
        val = inv.get(key)
        if val is not None:
            try:
                fval = float(val)
                if fval > 0:
                    return fval
            except:
                pass
    return 0.0

def build_receipt_xml(invoices_to_pay, company="ANAND MANGAL_FY26-27", cash_ledger="Cash"):
    """
    Generates Tally XML payload for Receipt Vouchers.
    Each voucher credits the Customer Ledger and debits Cash.
    """
    xml_msg = []
    for inv in invoices_to_pay:
        inv_no = inv.get('invoiceNo', '')
        party = escape_xml(inv.get('buyerFirmName', 'Sundry Debtors'))
        date_tally = format_date_for_tally(inv.get('invoiceDate') or inv.get('createdAt'))
        amt = get_inv_amount(inv)
        if amt <= 0:
            continue

        narration = escape_xml(f"Payment received against Bill {inv_no}")

        vch = f"""    <TALLYMESSAGE xmlns:UDF="TallyUDF">
      <VOUCHER VCHTYPE="Receipt" ACTION="Create">
        <DATE>{date_tally}</DATE>
        <VOUCHERTYPENAME>Receipt</VOUCHERTYPENAME>
        <PARTYLEDGERNAME>{party}</PARTYLEDGERNAME>
        <PERSISTEDVIEW>Accounting Voucher View</PERSISTEDVIEW>
        <NARRATION>{narration}</NARRATION>
        <ALLLEDGERENTRIES.LIST>
          <LEDGERNAME>{escape_xml(cash_ledger)}</LEDGERNAME>
          <ISDEEMEDPOSITIVE>Yes</ISDEEMEDPOSITIVE>
          <AMOUNT>-{amt:.2f}</AMOUNT>
        </ALLLEDGERENTRIES.LIST>
        <ALLLEDGERENTRIES.LIST>
          <LEDGERNAME>{party}</LEDGERNAME>
          <ISDEEMEDPOSITIVE>No</ISDEEMEDPOSITIVE>
          <AMOUNT>{amt:.2f}</AMOUNT>
          <BILLALLOCATIONS.LIST>
            <NAME>{escape_xml(inv_no)}</NAME>
            <BILLTYPE>Agst Ref</BILLTYPE>
            <AMOUNT>{amt:.2f}</AMOUNT>
          </BILLALLOCATIONS.LIST>
        </ALLLEDGERENTRIES.LIST>
      </VOUCHER>
    </TALLYMESSAGE>"""
        xml_msg.append(vch)

    full_xml = f"""<ENVELOPE>
  <HEADER>
    <VERSION>1</VERSION>
    <TALLYREQUEST>Import Data</TALLYREQUEST>
    <TYPE>Data</TYPE>
    <ID>Vouchers</ID>
  </HEADER>
  <BODY>
    <DESC>
      <STATICVARIABLES>
        <SVCURRENTCOMPANY>{company}</SVCURRENTCOMPANY>
      </STATICVARIABLES>
    </DESC>
    <DATA>
{chr(10).join(xml_msg)}
    </DATA>
  </BODY>
</ENVELOPE>"""
    return full_xml

def main():
    parser = argparse.ArgumentParser(description="Automate Tally Receipt Vouchers excluding Signed Bills.")
    parser.add_argument("--excel", default="SIGNED_BILLS_INPUT.xlsx", help="Path to signed bills Excel exclusion list")
    parser.add_argument("--month", default="10-2026", help="Month to process (MM-YYYY), e.g. 10-2026")
    parser.add_argument("--from-date", default=None, help="Custom start date (YYYY-MM-DD)")
    parser.add_argument("--to-date", default=None, help="Custom end date (YYYY-MM-DD)")
    parser.add_argument("--tally-ip", default="100.103.81.73", help="Tally server IP (Tailscale)")
    parser.add_argument("--tally-port", default="9000", help="Tally port")
    parser.add_argument("--company", default="ANAND MANGAL_FY26-27", help="Tally company name")
    parser.add_argument("--cash-ledger", default="Cash", help="Cash or Bank ledger for receipts")
    parser.add_argument("--post", action="store_true", help="Actually post receipts to Tally (default is DRY-RUN preview)")
    parser.add_argument("--save-xml", default="generated_receipts.xml", help="Path to save generated XML")

    args = parser.parse_args()

    # Determine date range
    if args.from_date and args.to_date:
        from_iso = f"{args.from_date}T00:00:00.000Z"
        to_iso = f"{args.to_date}T23:59:59.999Z"
        period_label = f"{args.from_date} to {args.to_date}"
    else:
        # Parse MM-YYYY
        parts = args.month.split('-')
        mm = int(parts[0])
        yyyy = int(parts[1])
        from_iso = f"{yyyy:04d}-{mm:02d}-01T00:00:00.000Z"
        # Determine last day
        import calendar
        last_day = calendar.monthrange(yyyy, mm)[1]
        to_iso = f"{yyyy:04d}-{mm:02d}-{last_day:02d}T23:59:59.999Z"
        period_label = f"{args.month} (01 to {last_day:02d})"

    script_dir = os.path.dirname(os.path.abspath(__file__))
    excel_path = args.excel if os.path.isabs(args.excel) else os.path.join(script_dir, args.excel)
    auth_path = os.path.join(script_dir, "auth.json")

    print("=" * 75)
    print("   RECEIPT VOUCHER AUTOMATION PROGRAM (EXCLUDING SIGNED BILLS)")
    print("=" * 75)
    print(f"📅 Target Period   : {period_label}")
    print(f"📋 Exclusion Sheet : {os.path.basename(excel_path)}")
    print(f"🏢 Tally Company   : {args.company} @ {args.tally_ip}:{args.tally_port}")
    print(f"💰 Receipt Ledger  : {args.cash_ledger}")
    print(f"⚙️  Execution Mode  : {'🔴 LIVE POST TO TALLY' if args.post else '🟡 DRY-RUN PREVIEW (No Changes)'}")
    print("=" * 75)

    # 1. Load signed bills from Excel
    signed_bills = load_signed_bill_numbers(excel_path)
    print(f"\n[Step 1/4] Loaded {len(signed_bills)} signed bill references to EXCLUDE from receipts.")

    # 2. Fetch all invoices from FieldAssist
    print(f"\n[Step 2/4] Fetching all delivered sales invoices for {period_label} from FieldAssist...")
    all_invoices = get_fieldassist_invoices(from_iso, to_iso, auth_path)
    print(f"  -> Found {len(all_invoices)} total sales invoices in this period.")

    if not all_invoices:
        print("❌ No invoices found to process. Exiting.")
        return

    # 3. Categorize into Paid vs Excluded
    excluded_bills = []
    paid_bills = []

    for inv in all_invoices:
        inv_no = str(inv.get('invoiceNo', ''))
        # Check if inv_no or trailing digits match exclusion set
        match = re.search(r'(\d+)$', inv_no)
        trailing_digits = match.group(1) if match else None

        is_signed = (inv_no in signed_bills) or (trailing_digits and trailing_digits in signed_bills)

        if is_signed:
            excluded_bills.append(inv)
        else:
            paid_bills.append(inv)

    tot_sales_val = sum(get_inv_amount(i) for i in all_invoices)
    tot_excl_val = sum(get_inv_amount(i) for i in excluded_bills)
    tot_paid_val = sum(get_inv_amount(i) for i in paid_bills)

    print("\n[Step 3/4] Reconciliation Breakdown:")
    print("-" * 75)
    print(f"  • Total Invoices in Period : {len(all_invoices):4d}  |  Value: ₹{tot_sales_val:>12,.2f}")
    print(f"  • Signed / Excluded Bills  : {len(excluded_bills):4d}  |  Value: ₹{tot_excl_val:>12,.2f} (Kept as Udhaari)")
    print(f"  • Eligible for Receipts    : {len(paid_bills):4d}  |  Value: ₹{tot_paid_val:>12,.2f} (Marked as PAID)")
    print("-" * 75)

    if excluded_bills:
        print(f"\nSample Excluded Bills (Will NOT have receipts):")
        for b in excluded_bills[:5]:
            print(f"   ⛔ {b.get('invoiceNo')} | {b.get('buyerFirmName', 'N/A')[:28]} | ₹{float(b.get('netAmount') or 0):,.2f}")

    if not paid_bills:
        print("\nAll bills are marked as signed udhaari. No receipts to generate.")
        return

    # 4. Generate XML Payload
    print(f"\n[Step 4/4] Building Tally Receipt XML payload for {len(paid_bills)} vouchers...")
    xml_payload = build_receipt_xml(paid_bills, company=args.company, cash_ledger=args.cash_ledger)
    xml_out_path = os.path.join(script_dir, args.save_xml)
    with open(xml_out_path, 'w', encoding='utf-8') as f:
        f.write(xml_payload)
    print(f"  -> XML saved to {os.path.basename(xml_out_path)} ({len(xml_payload):,} bytes)")

    if not args.post:
        print("\n" + "=" * 75)
        print("🟡 DRY-RUN COMPLETE: No changes were made in Tally.")
        print(f"   To push these {len(paid_bills)} receipts to Tally, run:")
        print(f"   python generate_receipts_for_paid_bills.py --post --month {args.month}")
        print("=" * 75)
        return

    # If --post was explicitly requested
    print(f"\n🚀 Posting {len(paid_bills)} Receipt Vouchers to Tally at http://{args.tally_ip}:{args.tally_port}/ ...")
    tally_url = f"http://{args.tally_ip}:{args.tally_port}/"
    headers = {'Content-Type': 'application/xml; charset=utf-8'}
    try:
        resp = requests.post(tally_url, data=xml_payload.encode('utf-8'), headers=headers, timeout=120)
        print(f"  -> Tally Server Response: HTTP {resp.status_code}")
        if resp.status_code == 200:
            created = len(re.findall(r'<CREATED>([1-9]\d*)</CREATED>', resp.text))
            errors = re.findall(r'<LINEERROR[^>]*>(.*?)</LINEERROR>', resp.text)
            if errors:
                print(f"⚠️ Tally reported {len(errors)} errors:")
                for e in errors[:5]:
                    print("   -", e)
            else:
                print("🎉 SUCCESS! Receipts successfully imported into Tally!")
    except Exception as e:
        print(f"❌ Failed to connect to Tally: {e}")

if __name__ == '__main__':
    main()
