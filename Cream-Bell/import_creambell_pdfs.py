import os
import sys
import re
import glob
import asyncio
import difflib
import argparse
from datetime import datetime
import requests
from PIL import Image
import pypdfium2 as pdfium
import winocr

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except:
        pass

# Known Cream Bell items in Tally for instant, accurate matching
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

def get_tally_state(tally_url, company):
    """
    Fetches all existing Cream Bell stock items and all existing voucher references for deduplication.
    """
    stock_items = set()
    existing_vouchers = set()

    # 1. Stock Items
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
        print(f"   [!] Warning: Could not query Tally stock items: {e}")

    # 2. Existing Voucher numbers & references
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
        print(f"   [!] Warning: Could not query existing vouchers in Tally: {e}")

    return stock_items, existing_vouchers

def match_stock_item(raw_name, tally_items):
    cleaned = re.sub(r'^\d+[- ]+', '', raw_name)
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    c_lower = cleaned.lower()
    
    # OCR normalization for 100ML
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

async def parse_creambell_invoice(pdf_path, tally_stock_items):
    pdf = pdfium.PdfDocument(pdf_path)
    if len(pdf) == 0:
        return None
    img = pdf[0].render(scale=2).to_pil()
    ocr = await winocr.recognize_pil(img, 'en')
    lines = ocr.lines
    full_text = "\n".join(l.text for l in lines)
    
    # 1. Invoice No & Date
    inv_no = ""
    inv_date = ""
    m_inv = re.search(r'Invoice\s*No\s*&\s*Date\s*:\s*([A-Za-z0-9_-]+)[,\s]+(\d{2}-\d{2}-\d{4})', full_text, re.I)
    if m_inv:
        inv_no = m_inv.group(1).strip()
        inv_date = m_inv.group(2).strip()
        # Fix OCR prefix for Sales Invoice (e.g. 320182627 -> SI20182627)
        if inv_no.startswith('320') or inv_no.startswith('32'):
            inv_no = 'SI2' + inv_no[2:] if inv_no.startswith('32') else 'SI' + inv_no[1:]
        elif inv_no.startswith('3'):
            inv_no = 'SI' + inv_no[1:]
        elif inv_no.startswith('S1') or inv_no.startswith('51'):
            inv_no = 'SI' + inv_no[2:]
            
    # Order No & Date
    order_no = ""
    m_ord = re.search(r'Order\s*No\s*&\s*Date\s*:\s*([A-Za-z0-9_/-]+)[,\s]+(\d{2}-\d{2}-\d{4})', full_text, re.I)
    if m_ord:
        order_no = m_ord.group(1).strip()
        
    # Buyer Firm Name
    buyer_name = ""
    for idx, l in enumerate(lines):
        if "Details of Receiver" in l.text:
            for next_l in lines[idx+1:idx+5]:
                if "Name :" in next_l.text:
                    b = next_l.text.split("Name :")[1].split("Name :")[0].strip()
                    buyer_name = b
                    break
            break
    if not buyer_name:
        m = re.search(r'Name\s*:\s*([A-Za-z0-9\s.&_-]+)', full_text)
        if m:
            buyer_name = m.group(1).strip()

    # Address & Pincode
    buyer_address = ""
    buyer_pincode = ""
    m_addr = re.search(r'Address\s*:\s*([^\n]+)', full_text, re.I)
    if m_addr:
        addr_raw = m_addr.group(1).split("Address :")[0].strip()
        buyer_address = re.sub(r'[\s,]+', ' ', addr_raw).strip()
    m_pin = re.search(r'\b(4\d{5})\b', full_text)
    if m_pin:
        buyer_pincode = m_pin.group(1)

    buyer_gstin = ""
    # Avoid picking seller's GSTIN (23AKUPM4082G1ZW)
    gst_matches = re.findall(r'GSTIN\s*:\s*([0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1})', full_text)
    for g in gst_matches:
        if "AKUPM4082" not in g:
            buyer_gstin = g
            break

    # Totals by matching Y coordinates
    total_amount = 0.0
    taxable_before_tax = 0.0
    total_gst = 0.0
    roundoff = 0.0
    cgst_val = 0.0
    sgst_val = 0.0
    
    for l in lines:
        text = l.text.strip()
        y = l.words[0].bounding_rect.y if l.words else 0
        x = l.words[0].bounding_rect.x if l.words else 0
        
        if 1320 <= y <= 1510 and x >= 1050:
            matching_label = next((lbl.text for lbl in lines if abs(lbl.words[0].bounding_rect.y - y) <= 6 and lbl.words[0].bounding_rect.x < 1000), "")
            val_clean = re.sub(r'[^\d.-]', '', text)
            if '(' in text and ')' in text:
                val_clean = '-' + val_clean
            try:
                fval = float(val_clean)
                if "Total Bill Amount" in matching_label:
                    total_amount = fval
                elif "Total Amount Before Tax" in matching_label:
                    taxable_before_tax = fval
                elif "Total GST Amount" in matching_label:
                    total_gst = fval
                elif "Rounded Off" in matching_label:
                    roundoff = fval
            except:
                pass

    # CGST & SGST from tax summary table (Y ~ 1500)
    for l in lines:
        y = l.words[0].bounding_rect.y if l.words else 0
        x = l.words[0].bounding_rect.x if l.words else 0
        if 1485 <= y <= 1520:
            if 600 <= x < 680 and re.match(r'^\d+\.\d{2}$', l.text.strip()):
                cgst_val = float(l.text.strip())
            elif 850 <= x < 930 and re.match(r'^\d+\.\d{2}$', l.text.strip()):
                sgst_val = float(l.text.strip())

    # Line Items
    prod_lines = []
    qty_lines = []
    rate_lines = []
    taxable_lines = []
    net_lines = []
    all_desc_words = []
    
    for l in lines:
        text = l.text.strip()
        y = l.words[0].bounding_rect.y if l.words else 0
        x = l.words[0].bounding_rect.x if l.words else 0
        
        if 530 <= y < 1240:
            if x < 350:
                all_desc_words.append((y, text))
            if x < 350 and re.search(r'^\d{5}-', text):
                prod_lines.append((y, text))
            elif 440 <= x < 510 and re.match(r'^\d+\.\d{2}$', text):
                qty_lines.append((y, float(text)))
            elif 620 <= x < 685 and re.match(r'^\d+\.\d{2}$', text):
                rate_lines.append((y, float(text)))
            elif 850 <= x < 915 and re.match(r'^\d+\.\d{2}$', text):
                taxable_lines.append((y, float(text)))
            elif x >= 1060 and re.match(r'^\d+\.\d{2}$', text):
                net_lines.append((y, float(text)))
                
    prod_lines.sort(key=lambda x: x[0])
    qty_lines.sort(key=lambda x: x[0])
    rate_lines.sort(key=lambda x: x[0])
    taxable_lines.sort(key=lambda x: x[0])
    net_lines.sort(key=lambda x: x[0])
    all_desc_words.sort(key=lambda x: x[0])
    
    items = []
    for i in range(len(prod_lines)):
        y_curr, text_curr = prod_lines[i]
        y_next = prod_lines[i+1][0] if i+1 < len(prod_lines) else 1250
        
        desc_parts = [w[1] for w in all_desc_words if y_curr <= w[0] < y_next]
        full_desc = " ".join(desc_parts)
        matched_item = match_stock_item(full_desc, tally_stock_items)
        
        q = qty_lines[i][1] if i < len(qty_lines) else 1.0
        r = rate_lines[i][1] if i < len(rate_lines) else 0.0
        taxable = taxable_lines[i][1] if i < len(taxable_lines) else (q * r)
        net_amt = net_lines[i][1] if i < len(net_lines) else (taxable * 1.05)
        
        items.append({
            'raw_name': full_desc,
            'name': matched_item,
            'qty': q,
            'rate': r,
            'taxable': taxable,
            'net_amt': net_amt,
            'unit': 'BX'
        })

    # Calculations sanity fallback
    if taxable_before_tax == 0.0 and items:
        taxable_before_tax = sum(it['taxable'] for it in items)
    if cgst_val == 0.0 and taxable_before_tax > 0:
        cgst_val = round(taxable_before_tax * 0.025, 2)
    if sgst_val == 0.0 and taxable_before_tax > 0:
        sgst_val = round(taxable_before_tax * 0.025, 2)
    if total_amount == 0.0:
        calc_tot = taxable_before_tax + cgst_val + sgst_val + roundoff
        total_amount = round(calc_tot)

    return {
        'invoiceNo': inv_no,
        'invoiceDate': inv_date,
        'orderNo': order_no,
        'buyerName': buyer_name,
        'buyerAddress': buyer_address,
        'buyerPincode': buyer_pincode,
        'buyerGstin': buyer_gstin,
        'buyerState': 'Madhya Pradesh',
        'items': items,
        'taxableAmount': taxable_before_tax,
        'totalAmount': total_amount,
        'cgst': cgst_val,
        'sgst': sgst_val,
        'roundoff': roundoff
    }

def build_masters_xml(inv, company="ANAND MANGAL_FY26-27"):
    messages = []
    # 1. Base Masters
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

    # 2. Customer Ledger
    c_name = escape_xml(inv['buyerName'])
    c_state = escape_xml(inv['buyerState'] or "Madhya Pradesh")
    c_gstin = escape_xml(inv['buyerGstin'])
    reg_type = "Regular" if c_gstin else "Unregistered"

    cust_xml = [
        '        <TALLYMESSAGE xmlns:UDF="TallyUDF">',
        f'          <LEDGER NAME="{c_name}" ACTION="Create">',
        '            <NAME.LIST>',
        f'              <NAME>{c_name}</NAME>',
        '            </NAME.LIST>',
        '            <PARENT>Sundry Debtors</PARENT>',
        '            <ISBILLWISEON>Yes</ISBILLWISEON>',
        '            <AFFECTSSTOCK>No</AFFECTSSTOCK>',
        '            <COUNTRYNAME>India</COUNTRYNAME>',
        f'            <LEDSTATENAME>{c_state}</LEDSTATENAME>',
        f'            <GSTREGISTRATIONTYPE>{reg_type}</GSTREGISTRATIONTYPE>',
    ]
    if c_gstin:
        cust_xml.append(f'            <PARTYGSTIN>{c_gstin}</PARTYGSTIN>')
    if inv['buyerPincode']:
        cust_xml.append(f'            <PINCODE>{escape_xml(inv["buyerPincode"])}</PINCODE>')
    if inv['buyerAddress']:
        cust_xml.append(f'            <ADDRESS.LIST><ADDRESS>{escape_xml(inv["buyerAddress"])}</ADDRESS></ADDRESS.LIST>')
    cust_xml.extend([
        '          </LEDGER>',
        '        </TALLYMESSAGE>'
    ])
    messages.append("\n".join(cust_xml))

    # 3. Stock Items
    for it in inv['items']:
        name_esc = escape_xml(it['name'])
        unit_esc = escape_xml(it.get('unit', 'BX'))
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
    return envelope

def build_voucher_xml(inv, company="ANAND MANGAL_FY26-27", sales_ledger="Sales - Cream Bell"):
    inv_no = inv['invoiceNo']
    dt_parts = inv['invoiceDate'].split('-')
    if len(dt_parts) == 3:
        tally_date = f"{dt_parts[2]}{dt_parts[1]}{dt_parts[0]}"
    else:
        tally_date = datetime.now().strftime("%Y%m%d")

    c_name = escape_xml(inv['buyerName'])
    c_gstin = escape_xml(inv['buyerGstin'])
    total_val = float(inv['totalAmount'])
    cgst_val = float(inv['cgst'])
    sgst_val = float(inv['sgst'])
    
    # Calculate exact balance
    taxable_sum = sum(float(it['taxable']) for it in inv['items'])
    computed_sum = taxable_sum + cgst_val + sgst_val
    round_off = round(total_val - computed_sum, 2)

    narration = f"Cream Bell Invoice {inv_no} Order {inv.get('orderNo', '')}".strip()

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
        f'            <NARRATION>{escape_xml(narration)}</NARRATION>',
        '            <PERSISTEDVIEW>Invoice Voucher View</PERSISTEDVIEW>',
        '            <ISINVOICE>Yes</ISINVOICE>',
    ]
    if c_gstin:
        xml_lines.append(f'            <PARTYGSTIN>{c_gstin}</PARTYGSTIN>')

    xml_lines.append(f'            <AMOUNT>-{total_val:.2f}</AMOUNT>')

    # 1. Line Items
    for it in inv['items']:
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
        xml_lines.extend([
            '            <LEDGERENTRIES.LIST>',
            '              <LEDGERNAME>Roundoff</LEDGERNAME>',
            f'              <ISDEEMEDPOSITIVE>{"No" if round_off > 0 else "Yes"}</ISDEEMEDPOSITIVE>',
            f'              <AMOUNT>{abs(round_off):.2f}</AMOUNT>',
            '            </LEDGERENTRIES.LIST>'
        ])

    xml_lines.extend([
        '          </VOUCHER>',
        '        </TALLYMESSAGE>'
    ])

    envelope = f"""<ENVELOPE>
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
{chr(10).join(xml_lines)}
      </REQUESTDATA>
    </IMPORTDATA>
  </BODY>
</ENVELOPE>"""
    return envelope

async def process_folder(folder_path, tally_ip="192.168.10.110", tally_port=9000, company="ANAND MANGAL_FY26-27", delete_after=True):
    tally_url = f"http://{tally_ip}:{tally_port}/"

    print("=" * 65)
    print("🍦 Cream Bell PDF to TallyPrime Automatic Importer")
    print(f"📁 Target Folder : {folder_path}")
    print(f"🎯 Target Tally  : {tally_url} ({company})")
    print(f"🗑️ Delete on Done : {'YES (Deletes PDF upon import)' if delete_after else 'NO (Keeps PDF)'}")
    print("=" * 65)

    if not os.path.exists(folder_path):
        os.makedirs(folder_path, exist_ok=True)
        print(f"\n📁 Created folder: {folder_path}")
        print("👉 Please place your Cream Bell invoice PDFs into this folder and run again.")
        return

    pdf_files = glob.glob(os.path.join(folder_path, "*.pdf"))
    if not pdf_files:
        print(f"\nℹ️ No PDF files found in '{folder_path}'.")
        print("👉 Drop your Cream Bell bills into this folder and run again.")
        return

    print(f"\n🔍 Found {len(pdf_files)} PDF file(s) to process.")
    print("📡 Querying Tally masters and existing vouchers...")
    stock_items, existing_vouchers = get_tally_state(tally_url, company)
    print(f"   * Cream Bell stock items in Tally: {len(stock_items)}")
    print(f"   * Existing vouchers in Tally: {len(existing_vouchers)}")

    imported_count = 0
    skipped_count = 0
    error_count = 0

    for idx, pdf_file in enumerate(pdf_files, 1):
        filename = os.path.basename(pdf_file)
        print(f"\n--- [{idx}/{len(pdf_files)}] Processing: {filename} ---")
        
        try:
            # 1. OCR & Parsing
            inv = await parse_creambell_invoice(pdf_file, stock_items)
            if not inv or not inv['invoiceNo']:
                print(f"   ❌ Error: Could not extract invoice details from {filename} (unreadable or not a Cream Bell invoice).")
                error_count += 1
                continue

            inv_no = inv['invoiceNo']
            print(f"   📄 Extracted: Invoice {inv_no} | Date: {inv['invoiceDate']} | Buyer: {inv['buyerName']} | Total: Rs.{inv['totalAmount']}")
            print(f"   📦 Items: {len(inv['items'])} line items")

            # 2. Deduplication check
            if inv_no.upper() in existing_vouchers:
                print(f"   ⚠️ ALREADY IN TALLY: Reference '{inv_no}' already exists in Tally.")
                if delete_after:
                    os.remove(pdf_file)
                    print(f"   🗑️ Deleted duplicate PDF: {filename}")
                skipped_count += 1
                continue

            # 3. Push Masters (Party & Stock Items)
            m_xml = build_masters_xml(inv, company)
            try:
                r_m = requests.post(tally_url, data=m_xml.encode('utf-8'), headers={'Content-Type': 'application/xml'}, timeout=10)
            except Exception as e:
                print(f"   ❌ Tally connection error during masters creation: {e}")
                error_count += 1
                continue

            # 4. Push Sales Voucher
            v_xml = build_voucher_xml(inv, company)
            try:
                r_v = requests.post(tally_url, data=v_xml.encode('utf-8'), headers={'Content-Type': 'application/xml'}, timeout=10)
            except Exception as e:
                print(f"   ❌ Tally connection error during voucher creation: {e}")
                error_count += 1
                continue

            created = re.findall(r'<CREATED>(\d+)</CREATED>', r_v.text)
            altered = re.findall(r'<ALTERED>(\d+)</ALTERED>', r_v.text)
            errors = re.findall(r'<ERRORS>(\d+)</ERRORS>', r_v.text)
            exceptions = re.findall(r'<EXCEPTIONS>(\d+)</EXCEPTIONS>', r_v.text)

            is_success = (created and int(created[0]) > 0) or (altered and int(altered[0]) > 0)

            if is_success:
                existing_vouchers.add(inv_no.upper())
                imported_count += 1
                print(f"   ✅ SUCCESS: Voucher created in Tally for {inv['buyerName']} (Rs.{inv['totalAmount']})!")
                
                # Delete PDF upon success
                if delete_after:
                    try:
                        os.remove(pdf_file)
                        print(f"   🗑️ Successfully deleted: {filename}")
                    except Exception as e:
                        print(f"   ⚠️ Could not delete file: {e}")
            else:
                line_err = re.findall(r'<LINEERROR[^>]*>(.*?)</LINEERROR>', r_v.text)
                print(f"   ❌ Tally rejected voucher for {inv_no}: Created={created}, Errors={errors}, Exceptions={exceptions}")
                if line_err:
                    print(f"      Details: {line_err}")
                error_count += 1

        except Exception as e:
            print(f"   ❌ Unexpected error processing {filename}: {e}")
            error_count += 1

    print("\n" + "=" * 65)
    print("📊 BATCH PROCESSING SUMMARY:")
    print(f"   ✅ Successfully Imported : {imported_count}")
    print(f"   ⚠️ Already in Tally       : {skipped_count}")
    print(f"   ❌ Failed / Errors        : {error_count}")
    print(f"   📁 Remaining in Folder    : {len(glob.glob(os.path.join(folder_path, '*.pdf')))}")
    print("=" * 65 + "\n")

def main():
    parser = argparse.ArgumentParser(description="Cream Bell PDF to Tally Automatic Importer")
    parser.add_argument("--folder", default="creambell_bills", help="Folder containing Cream Bell PDFs (default: creambell_bills)")
    parser.add_argument("--tally-ip", default="192.168.10.110", help="Tally PC IP address (default: 192.168.10.110)")
    parser.add_argument("--tally-port", type=int, default=9000, help="Tally ODBC/HTTP port (default: 9000)")
    parser.add_argument("--company", default="ANAND MANGAL_FY26-27", help="Tally Company Name (default: ANAND MANGAL_FY26-27)")
    parser.add_argument("--no-delete", action="store_true", help="Do not delete PDF after importing")

    args = parser.parse_args()
    asyncio.run(process_folder(
        folder_path=args.folder,
        tally_ip=args.tally_ip,
        tally_port=args.tally_port,
        company=args.company,
        delete_after=not args.no_delete
    ))

if __name__ == "__main__":
    main()
