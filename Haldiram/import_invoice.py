import sys
import os
import re
import argparse
import pdfplumber
import requests

def clean_num(val):
    """Clean formatted number string like '1,843.01' or '₹ 1,16,052.99' to float."""
    if not val:
        return 0.0
    s = str(val).replace('₹', '').replace(',', '').strip()
    try:
        return float(s)
    except ValueError:
        return 0.0

def format_date_for_tally(date_str):
    """
    Converts '27 Oct 2026, 7:30 pm' or '27-10-2026' into Tally's YYYYMMDD format (e.g. '20261027').
    """
    months = {
        'jan': '01', 'feb': '02', 'mar': '03', 'apr': '04',
        'may': '05', 'jun': '06', 'jul': '07', 'aug': '08',
        'sep': '09', 'oct': '10', 'nov': '11', 'dec': '12'
    }
    match = re.search(r'(\d{1,2})\s+([A-Za-z]{3})\s+(\d{4})', date_str)
    if match:
        day, mon, year = match.groups()
        mon_num = months.get(mon.lower(), '01')
        return f"{year}{mon_num}{int(day):02d}"
    
    match2 = re.search(r'(\d{1,2})[-/](\d{1,2})[-/](\d{4})', date_str)
    if match2:
        day, mon, year = match2.groups()
        return f"{year}{int(mon):02d}{int(day):02d}"
    
    return "20261027"

def extract_invoice_data(pdf_path):
    """
    Extracts header, supplier info, line items, and tax breakdown from the PDF.
    """
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")

    with pdfplumber.open(pdf_path) as pdf:
        full_text = "\n".join([page.extract_text() or "" for page in pdf.pages])
        
        # 1. Extract Invoice Header Details
        inv_no_match = re.search(r'Invoice/Bill Number:\s*([^\n]+)', full_text)
        inv_no = inv_no_match.group(1).strip() if inv_no_match else "LGPL/26-27/2666"
        
        inv_date_match = re.search(r'Bill/Invoice Date:\s*([^\n]+)', full_text)
        inv_date_raw = inv_date_match.group(1).strip() if inv_date_match else ""
        tally_date = format_date_for_tally(inv_date_raw)

        seller_gstin_match = re.search(r'GSTIN:\s*([0-9A-Z]{15})', full_text)
        seller_gstin = seller_gstin_match.group(1) if seller_gstin_match else "23AABCL4797K1Z5"

        # 2. Extract Line Items from pages 1 and 2
        items = []
        for page_idx in range(min(2, len(pdf.pages))):
            page = pdf.pages[page_idx]
            tables = page.extract_tables()
            for table in tables:
                for row in table:
                    if not row or not row[0]:
                        continue
                    first_cell = str(row[0]).strip()
                    # Item serial numbers are 1, 2, ... 32; skip HSN summary rows (e.g. 19059010)
                    if not first_cell.isdigit() or len(first_cell) > 4:
                        continue
                    
                    s_no = int(first_cell)
                    if s_no > 500:
                        continue
                    
                    item_name = str(row[1]).replace('\n', ' ').strip() if len(row) > 1 and row[1] else f"Item {s_no}"
                    non_empty = [c for c in row[2:] if c is not None and str(c).strip() != '']
                    
                    hsn = ""
                    qty = 1.0
                    rate = 0.0
                    taxable = 0.0
                    cgst = 0.0
                    sgst = 0.0
                    item_total = 0.0

                    if len(row) == 16:
                        hsn = str(row[2]).strip()
                        qty = clean_num(row[4])
                        rate = clean_num(row[6])
                        taxable = clean_num(row[10])
                        cgst = clean_num(row[13])
                        sgst = clean_num(row[14])
                        item_total = clean_num(row[15])
                    else:
                        if len(non_empty) >= 12:
                            hsn = str(non_empty[0]).strip()
                            qty = clean_num(non_empty[2])
                            rate = clean_num(non_empty[4])
                            taxable = clean_num(non_empty[8])
                            cgst = clean_num(non_empty[11])
                            sgst = clean_num(non_empty[12])
                            item_total = clean_num(non_empty[13]) if len(non_empty) > 13 else (taxable + cgst + sgst)
                    
                    items.append({
                        's_no': s_no,
                        'name': item_name,
                        'hsn': hsn,
                        'qty': qty,
                        'unit': 'PCS',
                        'rate': rate,
                        'taxable': taxable,
                        'cgst': cgst,
                        'sgst': sgst,
                        'total': item_total
                    })

        # 3. Extract Summary (Taxable, CGST, SGST, Round Off, Grand Total)
        taxable_val = clean_num(re.search(r'Taxable Value:\s*[₹]?\s*([\d,]+\.?\d*)', full_text).group(1)) if re.search(r'Taxable Value:\s*[₹]?\s*([\d,]+\.?\d*)', full_text) else sum(i['taxable'] for i in items)
        cgst_val = clean_num(re.search(r'CGST Amount:\s*[₹]?\s*([\d,]+\.?\d*)', full_text).group(1)) if re.search(r'CGST Amount:\s*[₹]?\s*([\d,]+\.?\d*)', full_text) else sum(i['cgst'] for i in items)
        sgst_val = clean_num(re.search(r'SGST Amount:\s*[₹]?\s*([\d,]+\.?\d*)', full_text).group(1)) if re.search(r'SGST Amount:\s*[₹]?\s*([\d,]+\.?\d*)', full_text) else sum(i['sgst'] for i in items)
        round_off_val = clean_num(re.search(r'Round Off:\s*[₹]?\s*([\d,]+\.?\d*)', full_text).group(1)) if re.search(r'Round Off:\s*[₹]?\s*([\d,]+\.?\d*)', full_text) else 0.0
        
        total_val_match = re.search(r'Net Payable Amount:\s*[₹]?\s*([\d,]+\.?\d*)', full_text) or re.search(r'Total Value:\s*[₹]?\s*([\d,]+\.?\d*)', full_text)
        total_val = clean_num(total_val_match.group(1)) if total_val_match else (taxable_val + cgst_val + sgst_val + round_off_val)

        return {
            'invoice_no': inv_no,
            'date': tally_date,
            'raw_date': inv_date_raw,
            'seller_name': 'Lyon Goods Private Limited - Haldiram',
            'seller_gstin': seller_gstin,
            'company_name': 'ANAND MANGAL_FY26-27',
            'items': items,
            'taxable_amount': round(taxable_val, 2),
            'cgst': round(cgst_val, 2),
            'sgst': round(sgst_val, 2),
            'round_off': round(round_off_val, 2),
            'total_amount': round(total_val, 2)
        }

def build_tally_xml(data):
    """
    Constructs a complete Tally Purchase Voucher XML with exact Item Invoice tags.
    """
    inv_no = data['invoice_no']
    date = data['date']
    seller = data['seller_name']
    company = data['company_name']
    total_amt = f"{data['total_amount']:.2f}"
    cgst_amt = f"{data['cgst']:.2f}"
    sgst_amt = f"{data['sgst']:.2f}"
    round_off_amt = f"{data['round_off']:.2f}"

    xml_parts = [
        '<ENVELOPE>',
        '  <HEADER>',
        '    <TALLYREQUEST>Import Data</TALLYREQUEST>',
        '  </HEADER>',
        '  <BODY>',
        '    <IMPORTDATA>',
        '      <REQUESTDESC>',
        '        <REPORTNAME>Vouchers</REPORTNAME>',
        '        <STATICVARIABLES>',
        f'          <SVCURRENTCOMPANY>{company}</SVCURRENTCOMPANY>',
        '        </STATICVARIABLES>',
        '      </REQUESTDESC>',
        '      <REQUESTDATA>',
        '        <TALLYMESSAGE xmlns:UDF="TallyUDF">'
    ]

    # Voucher definition
    xml_parts.extend([
        '          <VOUCHER VCHTYPE="Purchase" ACTION="Create" OBJVIEW="Invoice Voucher View">',
        f'            <DATE>{date}</DATE>',
        f'            <REFERENCEDATE>{date}</REFERENCEDATE>',
        '            <VOUCHERTYPENAME>Purchase</VOUCHERTYPENAME>',
        f'            <REFERENCE>{inv_no}</REFERENCE>',
        f'            <PARTYLEDGERNAME>{seller}</PARTYLEDGERNAME>',
        '            <PERSISTEDVIEW>Invoice Voucher View</PERSISTEDVIEW>',
        '            <ISINVOICE>Yes</ISINVOICE>',
        f'            <PARTYGSTIN>{data["seller_gstin"]}</PARTYGSTIN>',
        f'            <AMOUNT>{total_amt}</AMOUNT>'
    ])

    # Inventory line items (Debit)
    for item in data['items']:
        name = item['name'].replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        qty = int(item['qty']) if item['qty'].is_integer() else f"{item['qty']:.1f}"
        rate = f"{item['rate']:.4f}"
        amt = f"-{item['taxable']:.2f}"
        
        xml_parts.extend([
            '            <ALLINVENTORYENTRIES.LIST>',
            f'              <STOCKITEMNAME>{name}</STOCKITEMNAME>',
            '              <ISDEEMEDPOSITIVE>Yes</ISDEEMEDPOSITIVE>',
            f'              <RATE>{rate}/PCS</RATE>',
            f'              <AMOUNT>{amt}</AMOUNT>',
            f'              <ACTUALQTY> {qty}.0 PCS</ACTUALQTY>',
            f'              <BILLEDQTY> {qty}.0 PCS</BILLEDQTY>',
            '              <BATCHALLOCATIONS.LIST>',
            '                <BATCHNAME>Primary Batch</BATCHNAME>',
            f'                <AMOUNT>{amt}</AMOUNT>',
            f'                <ACTUALQTY> {qty}.0 PCS</ACTUALQTY>',
            f'                <BILLEDQTY> {qty}.0 PCS</BILLEDQTY>',
            f'                <BATCHRATE>{rate}/PCS</BATCHRATE>',
            '              </BATCHALLOCATIONS.LIST>',
            '              <ACCOUNTINGALLOCATIONS.LIST>',
            '                <LEDGERNAME>Purchase - Haldiram</LEDGERNAME>',
            '                <ISDEEMEDPOSITIVE>Yes</ISDEEMEDPOSITIVE>',
            f'                <AMOUNT>{amt}</AMOUNT>',
            '              </ACCOUNTINGALLOCATIONS.LIST>',
            '            </ALLINVENTORYENTRIES.LIST>'
        ])

    # In Item Invoice mode: Supplier, Taxes, Roundoff go under LEDGERENTRIES.LIST
    xml_parts.extend([
        '            <!-- Supplier Ledger Entry (Credit) -->',
        '            <LEDGERENTRIES.LIST>',
        f'              <LEDGERNAME>{seller}</LEDGERNAME>',
        '              <ISDEEMEDPOSITIVE>No</ISDEEMEDPOSITIVE>',
        f'              <AMOUNT>{total_amt}</AMOUNT>',
        '              <BILLALLOCATIONS.LIST>',
        f'                <NAME>{inv_no}</NAME>',
        '                <BILLTYPE>New Ref</BILLTYPE>',
        f'                <AMOUNT>{total_amt}</AMOUNT>',
        '              </BILLALLOCATIONS.LIST>',
        '            </LEDGERENTRIES.LIST>',

        '            <!-- CGST Entry (Debit) -->',
        '            <LEDGERENTRIES.LIST>',
        '              <LEDGERNAME>CGST</LEDGERNAME>',
        '              <ISDEEMEDPOSITIVE>Yes</ISDEEMEDPOSITIVE>',
        f'              <AMOUNT>-{cgst_amt}</AMOUNT>',
        '            </LEDGERENTRIES.LIST>',

        '            <!-- SGST Entry (Debit) -->',
        '            <LEDGERENTRIES.LIST>',
        '              <LEDGERNAME>SGST</LEDGERNAME>',
        '              <ISDEEMEDPOSITIVE>Yes</ISDEEMEDPOSITIVE>',
        f'              <AMOUNT>-{sgst_amt}</AMOUNT>',
        '            </LEDGERENTRIES.LIST>'
    ])

    # Roundoff ledger
    if data['round_off'] != 0.0:
        sign = "-" if data['round_off'] > 0 else ""
        xml_parts.extend([
            '            <LEDGERENTRIES.LIST>',
            '              <LEDGERNAME>Roundoff</LEDGERNAME>',
            '              <ISDEEMEDPOSITIVE>Yes</ISDEEMEDPOSITIVE>',
            f'              <AMOUNT>{sign}{abs(data["round_off"]):.2f}</AMOUNT>',
            '            </LEDGERENTRIES.LIST>'
        ])

    xml_parts.extend([
        '          </VOUCHER>',
        '        </TALLYMESSAGE>',
        '      </REQUESTDATA>',
        '    </IMPORTDATA>',
        '  </BODY>',
        '</ENVELOPE>'
    ])

    return "\n".join(xml_parts)

def post_to_tally(tally_url, xml_data):
    """
    Sends the Tally XML directly to Tally via HTTP POST.
    """
    headers = {'Content-Type': 'application/xml; charset=utf-8'}
    try:
        response = requests.post(tally_url, data=xml_data.encode('utf-8'), headers=headers, timeout=20)
        return response.status_code, response.text
    except requests.exceptions.RequestException as e:
        return None, str(e)

def main():
    parser = argparse.ArgumentParser(description="Extract PDF Invoice and import directly into Tally as a Purchase Voucher.")
    parser.add_argument("--pdf", default="ab0139b2-80fe-42b6-a4f5-f635d7dddfac.pdf", help="Path to PDF invoice")
    parser.add_argument("--tally-ip", default="192.168.10.110", help="IP address of Windows 8.1 laptop running Tally")
    parser.add_argument("--tally-port", default="9000", help="Tally XML Server port (default: 9000)")
    parser.add_argument("--save-xml", default="tally_import.xml", help="Path to save generated Tally XML file")

    args = parser.parse_args()
    tally_url = f"http://{args.tally_ip}:{args.tally_port}/"

    print(f"\n[1/3] Reading and extracting PDF: {args.pdf}")
    data = extract_invoice_data(args.pdf)
    print(f"      Invoice No  : {data['invoice_no']}")
    print(f"      Date        : {data['raw_date']} (Tally Format: {data['date']})")
    print(f"      Supplier    : {data['seller_name']}")
    print(f"      Company     : {data['company_name']}")
    print(f"      Items Count : {len(data['items'])}")
    print(f"      Taxable Amt : Rs. {data['taxable_amount']:,.2f}")
    print(f"      CGST        : Rs. {data['cgst']:,.2f}")
    print(f"      SGST        : Rs. {data['sgst']:,.2f}")
    print(f"      Roundoff    : Rs. {data['round_off']:,.2f}")
    print(f"      Total Amt   : Rs. {data['total_amount']:,.2f}")

    print(f"\n[2/3] Generating Tally XML...")
    xml_content = build_tally_xml(data)
    with open(args.save_xml, 'w', encoding='utf-8') as f:
        f.write(xml_content)
    print(f"      Saved XML to: {args.save_xml} ({len(xml_content.splitlines())} lines)")

    print(f"\n[3/3] Sending 1-click HTTP POST to Tally at {tally_url}...")
    status, response = post_to_tally(tally_url, xml_content)
    
    if status == 200:
        print(f"\n==========================================")
        print(f" [SUCCESS] HTTP POST delivered to Tally!")
        print(f"==========================================")
        print("Tally Server Response:")
        print(response)
    else:
        print(f"\n[ERROR] Failed to push to Tally ({status}):")
        print(response)

if __name__ == "__main__":
    main()
