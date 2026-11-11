import csv
import json
import os
import shutil
import zipfile
from xml.sax.saxutils import escape

with open('voucher_details.json', 'r', encoding='utf-8') as f:
    vch = json.load(f)

def get_col_letter(col_idx):
    result = ""
    while col_idx > 0:
        col_idx, remainder = divmod(col_idx - 1, 26)
        result = chr(65 + remainder) + result
    return result

class SimpleXlsx:
    def __init__(self):
        self.sheets = []  # list of (name, rows, col_widths)
        
    def add_sheet(self, name, col_widths=None):
        rows = []
        self.sheets.append((name, rows, col_widths or {}))
        return rows

    def save(self, filepath):
        types_overrides = []
        wb_sheets = []
        wb_rels = []
        
        styles_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <fonts count="6">
    <font><name val="Calibri"/><sz val="11"/></font>
    <font><b/><name val="Calibri"/><sz val="11"/></font>
    <font><b/><name val="Calibri"/><sz val="15"/><color rgb="FF1F4E78"/></font>
    <font><b/><name val="Calibri"/><sz val="11"/><color rgb="FFFFFFFF"/></font>
    <font><b/><name val="Calibri"/><sz val="12"/></font>
    <font><i/><name val="Calibri"/><sz val="10"/><color rgb="FF595959"/></font>
  </fonts>
  <fills count="7">
    <fill><patternFill patternType="none"/></fill>
    <fill><patternFill patternType="gray125"/></fill>
    <fill><patternFill patternType="solid"><fgColor rgb="FF1F4E78"/></patternFill></fill>
    <fill><patternFill patternType="solid"><fgColor rgb="FFD9E1F2"/></patternFill></fill>
    <fill><patternFill patternType="solid"><fgColor rgb="FFF2F4F7"/></patternFill></fill>
    <fill><patternFill patternType="solid"><fgColor rgb="FFE2EFDA"/></patternFill></fill>
    <fill><patternFill patternType="solid"><fgColor rgb="FFFCE4D6"/></patternFill></fill>
  </fills>
  <borders count="3">
    <border><left/><right/><top/><bottom/><diagonal/></border>
    <border>
      <left style="thin"><color rgb="FFB0C4DE"/></left>
      <right style="thin"><color rgb="FFB0C4DE"/></right>
      <top style="thin"><color rgb="FFB0C4DE"/></top>
      <bottom style="thin"><color rgb="FFB0C4DE"/></bottom>
    </border>
    <border>
      <left style="thin"><color rgb="FFB0C4DE"/></left>
      <right style="thin"><color rgb="FFB0C4DE"/></right>
      <top style="thin"><color rgb="FFB0C4DE"/></top>
      <bottom style="double"><color rgb="FF1F4E78"/></bottom>
    </border>
  </borders>
  <cellStyleXfs count="1">
    <xf numFmtId="0" fontId="0" fillId="0" borderId="0"/>
  </cellStyleXfs>
  <cellXfs count="12">
    <!-- 0: Regular -->
    <xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/>
    <!-- 1: Bold -->
    <xf numFmtId="0" fontId="1" fillId="0" borderId="0" xfId="0"/>
    <!-- 2: Title Large Center -->
    <xf numFmtId="0" fontId="2" fillId="0" borderId="0" xfId="0" applyFont="1"><alignment horizontal="center"/></xf>
    <!-- 3: Table Header (Dark Navy Fill, White Text) -->
    <xf numFmtId="0" fontId="3" fillId="2" borderId="1" xfId="0" applyFont="1" applyFill="1" applyBorder="1" applyAlignment="1"><alignment horizontal="center" vertical="center"/></xf>
    <!-- 4: Table Cell Regular with border -->
    <xf numFmtId="0" fontId="0" fillId="0" borderId="1" xfId="0" applyBorder="1"/>
    <!-- 5: Table Cell Number Right aligned -->
    <xf numFmtId="0" fontId="0" fillId="0" borderId="1" xfId="0" applyBorder="1" applyAlignment="1"><alignment horizontal="right"/></xf>
    <!-- 6: Table Cell Number Bold Right aligned -->
    <xf numFmtId="0" fontId="1" fillId="3" borderId="1" xfId="0" applyFont="1" applyFill="1" applyBorder="1" applyAlignment="1"><alignment horizontal="right"/></xf>
    <!-- 7: Section Header Light Blue -->
    <xf numFmtId="0" fontId="1" fillId="3" borderId="1" xfId="0" applyFont="1" applyFill="1" applyBorder="1"/>
    <!-- 8: Total Double Bottom Green -->
    <xf numFmtId="0" fontId="1" fillId="5" borderId="2" xfId="0" applyFont="1" applyFill="1" applyBorder="1" applyAlignment="1"><alignment horizontal="right"/></xf>
    <!-- 9: Center aligned bordered cell -->
    <xf numFmtId="0" fontId="0" fillId="0" borderId="1" xfId="0" applyBorder="1" applyAlignment="1"><alignment horizontal="center"/></xf>
    <!-- 10: Subtitle / italic -->
    <xf numFmtId="0" fontId="5" fillId="0" borderId="0" xfId="0" applyFont="1"><alignment horizontal="center"/></xf>
    <!-- 11: Header Light soft gray -->
    <xf numFmtId="0" fontId="1" fillId="4" borderId="1" xfId="0" applyFont="1" applyFill="1" applyBorder="1"/>
  </cellXfs>
</styleSheet>"""

        with zipfile.ZipFile(filepath, 'w', zipfile.ZIP_DEFLATED) as z:
            z.writestr('_rels/.rels', """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
</Relationships>""")
            
            for idx, (name, rows, col_widths) in enumerate(self.sheets, 1):
                sheet_file = f"worksheets/sheet{idx}.xml"
                types_overrides.append(f'<Override PartName="/xl/{sheet_file}" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>')
                wb_sheets.append(f'<sheet name="{escape(name)}" sheetId="{idx}" r:id="rId{idx}"/>')
                wb_rels.append(f'<Relationship Id="rId{idx}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="{sheet_file}"/>')
                
                sheet_lines = [
                    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
                    '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
                ]
                
                if col_widths:
                    sheet_lines.append('  <cols>')
                    for col_idx, width in col_widths.items():
                        sheet_lines.append(f'    <col min="{col_idx}" max="{col_idx}" width="{width}" customWidth="1"/>')
                    sheet_lines.append('  </cols>')
                    
                sheet_lines.append('  <sheetData>')
                for r_idx, row in enumerate(rows, 1):
                    sheet_lines.append(f'    <row r="{r_idx}">')
                    for c_idx, cell in enumerate(row, 1):
                        if cell is None:
                            continue
                        val, style_idx, val_type = cell
                        col_let = get_col_letter(c_idx)
                        c_ref = f"{col_let}{r_idx}"
                        
                        s_attr = f' s="{style_idx}"' if style_idx is not None else ''
                        if val_type == 'n':
                            sheet_lines.append(f'      <c r="{c_ref}"{s_attr}><v>{val}</v></c>')
                        else:
                            sheet_lines.append(f'      <c r="{c_ref}"{s_attr} t="inlineStr"><is><t>{escape(str(val))}</t></is></c>')
                    sheet_lines.append('    </row>')
                    
                sheet_lines.append('  </sheetData>')
                sheet_lines.append('</worksheet>')
                z.writestr(f"xl/{sheet_file}", "\n".join(sheet_lines))

            styles_rid = f"rId{len(self.sheets) + 1}"
            wb_rels.append(f'<Relationship Id="{styles_rid}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>')
            
            content_types_xml = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
  <Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>
  {"".join(types_overrides)}
</Types>"""
            z.writestr('[Content_Types].xml', content_types_xml)

            workbook_xml = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <sheets>
    {"".join(wb_sheets)}
  </sheets>
</workbook>"""
            z.writestr('xl/workbook.xml', workbook_xml)

            wb_rels_xml = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  {"".join(wb_rels)}
</Relationships>"""
            z.writestr('xl/_rels/workbook.xml.rels', wb_rels_xml)
            z.writestr('xl/styles.xml', styles_xml)

# Create Workbook
xlsx = SimpleXlsx()

# ----------------- SHEET 1: TAX INVOICE -----------------
col_w = {
    1: 8,   # S.No
    2: 38,  # Description of Goods
    3: 14,  # HSN/SAC
    4: 14,  # Quantity
    5: 14,  # Rate (Rs)
    6: 10,  # Disc %
    7: 16   # Amount (Rs)
}
s1 = xlsx.add_sheet("Tax Invoice", col_w)

def add_r(sheet, cells):
    sheet.append(cells)

# Company Header
add_r(s1, [(None, None, 's'), ('ANAND MANGAL', 2, 's'), (None, None, 's'), (None, None, 's'), (None, None, 's'), (None, None, 's'), (None, None, 's')])
add_r(s1, [(None, None, 's'), ('2A, Scheme No - 140, Pipliyana Talab, Indore (M.P.)', 10, 's'), (None, None, 's'), (None, None, 's'), (None, None, 's'), (None, None, 's'), (None, None, 's')])
add_r(s1, [(None, None, 's'), ('GSTIN: 23AKUPM4082G1ZW | State: Madhya Pradesh (23) | Email: anand.mishrag9@gmail.com', 10, 's'), (None, None, 's'), (None, None, 's'), (None, None, 's'), (None, None, 's'), (None, None, 's')])
add_r(s1, [(None, None, 's'), ('TAX INVOICE', 3, 's'), (None, None, 's'), (None, None, 's'), (None, None, 's'), (None, None, 's'), (None, None, 's')])
add_r(s1, [])

# Invoice & Buyer Details Block
inv_date_str = f"{vch['date'][6:8]}-{vch['date'][4:6]}-{vch['date'][:4]}"
add_r(s1, [('Invoice No:', 1, 's'), (vch['voucher_number'], 1, 's'), (None, None, 's'), ('Dated:', 1, 's'), (inv_date_str, 1, 's'), (None, None, 's'), (None, None, 's')])
add_r(s1, [('Buyer (Bill to):', 7, 's'), (vch['party_name'], 7, 's'), (None, None, 's'), ('Place of Supply:', 1, 's'), (vch['place_of_supply'], 0, 's'), (None, None, 's'), (None, None, 's')])
add_r(s1, [('Address:', 1, 's'), (", ".join(vch['party_address']), 0, 's'), (None, None, 's'), ('State / Code:', 1, 's'), (f"{vch['state_name']} (23)", 0, 's'), (None, None, 's'), (None, None, 's')])
add_r(s1, [('Buyer GSTIN:', 1, 's'), (vch['party_gstin'], 1, 's'), (None, None, 's'), ('Voucher Type:', 1, 's'), (vch['voucher_type'], 0, 's'), (None, None, 's'), (None, None, 's')])
add_r(s1, [])

# Table Header
add_r(s1, [
    ('S.No.', 3, 's'),
    ('Description of Goods', 3, 's'),
    ('HSN/SAC', 3, 's'),
    ('Quantity', 3, 's'),
    ('Rate (₹)', 3, 's'),
    ('Disc %', 3, 's'),
    ('Amount (₹)', 3, 's')
])

total_qty = 0.0
total_amt = 0.0

for idx, item in enumerate(vch['items'], 1):
    q_str = item['billed_qty'].strip()
    q_num = float(q_str.split()[0])
    total_qty += q_num
    
    r_str = item['rate'].strip().replace('/PCS', '')
    r_num = float(r_str)
    
    a_num = float(item['amount'])
    total_amt += a_num
    
    add_r(s1, [
        (idx, 9, 'n'),
        (item['name'], 4, 's'),
        (item['hsn'], 9, 's'),
        (q_str, 5, 's'),
        (f"{r_num:,.2f}", 5, 's'),
        (item['discount'], 9, 's'),
        (f"{a_num:,.2f}", 5, 's')
    ])

# Table Subtotal
add_r(s1, [
    (None, None, 's'),
    ('Subtotal / Taxable Value', 6, 's'),
    (None, None, 's'),
    (f"{total_qty:.1f} PCS", 6, 's'),
    (None, None, 's'),
    (None, None, 's'),
    (f"{total_amt:,.2f}", 6, 's')
])

# Taxes & Ledger entries
cgst_amt = 0.0
sgst_amt = 0.0
roundoff_amt = 0.0
grand_total = 0.0

for led in vch['ledgers']:
    lname = led['name']
    lamt = float(led['amount'])
    if lname == 'CGST':
        cgst_amt = lamt
        add_r(s1, [(None, None, 's'), ('CGST @ 6%', 1, 's'), (None, None, 's'), (None, None, 's'), (None, None, 's'), (None, None, 's'), (f"{cgst_amt:,.2f}", 5, 's')])
    elif lname == 'SGST':
        sgst_amt = lamt
        add_r(s1, [(None, None, 's'), ('SGST @ 6%', 1, 's'), (None, None, 's'), (None, None, 's'), (None, None, 's'), (None, None, 's'), (f"{sgst_amt:,.2f}", 5, 's')])
    elif lname == 'Roundoff':
        roundoff_amt = lamt
        add_r(s1, [(None, None, 's'), ('Round Off', 1, 's'), (None, None, 's'), (None, None, 's'), (None, None, 's'), (None, None, 's'), (f"{roundoff_amt:,.2f}", 5, 's')])
    elif lname == vch['party_ledger']:
        grand_total = abs(lamt)

# Grand Total Row
add_r(s1, [
    (None, None, 's'),
    ('GRAND TOTAL (₹)', 8, 's'),
    (None, None, 's'),
    (None, None, 's'),
    (None, None, 's'),
    (None, None, 's'),
    (f"₹ {grand_total:,.2f}", 8, 's')
])

add_r(s1, [])
add_r(s1, [('Amount in Words:', 1, 's'), ('Eight Thousand Five Hundred Seventeen Rupees Only', 0, 's')])
add_r(s1, [])
add_r(s1, [('Declaration:', 1, 's'), ('We declare that this invoice shows the actual price of the goods described and that all particulars are true and correct.', 10, 's')])
add_r(s1, [(None, None, 's'), (None, None, 's'), (None, None, 's'), (None, None, 's'), ('For ANAND MANGAL', 1, 's')])
add_r(s1, [])
add_r(s1, [(None, None, 's'), (None, None, 's'), (None, None, 's'), (None, None, 's'), ('Authorised Signatory', 1, 's')])


# ----------------- SHEET 2: ITEM DETAILS (DATA TABLE) -----------------
col_w2 = {
    1: 8,   # S.No
    2: 18,  # Invoice No
    3: 12,  # Date
    4: 25,  # Customer Name
    5: 18,  # Customer GSTIN
    6: 35,  # Item Description
    7: 12,  # HSN Code
    8: 10,  # Qty
    9: 8,   # Unit
    10: 12, # Rate
    11: 14, # Taxable Amount
    12: 12, # CGST Amount
    13: 12, # SGST Amount
    14: 14  # Total Amount
}
s2 = xlsx.add_sheet("Item_Data_Table", col_w2)

# Header
add_r(s2, [
    ('S.No.', 3, 's'),
    ('Invoice No', 3, 's'),
    ('Date', 3, 's'),
    ('Party Name', 3, 's'),
    ('Party GSTIN', 3, 's'),
    ('Item Description', 3, 's'),
    ('HSN/SAC', 3, 's'),
    ('Quantity', 3, 's'),
    ('Unit', 3, 's'),
    ('Rate (₹)', 3, 's'),
    ('Taxable Amt (₹)', 3, 's'),
    ('CGST (₹)', 3, 's'),
    ('SGST (₹)', 3, 's'),
    ('Total Item Value (₹)', 3, 's')
])

csv_rows = []
csv_header = ['S.No', 'Invoice No', 'Date', 'Party Name', 'Party GSTIN', 'Item Description', 'HSN/SAC', 'Quantity', 'Unit', 'Rate', 'Taxable Amount', 'CGST', 'SGST', 'Total Item Value']
csv_rows.append(csv_header)

for idx, item in enumerate(vch['items'], 1):
    q_str = item['billed_qty'].strip()
    parts = q_str.split()
    q_val = float(parts[0])
    u_val = parts[1] if len(parts) > 1 else 'PCS'
    
    r_val = float(item['rate'].strip().replace('/PCS', ''))
    a_val = float(item['amount'])
    
    # Each item's tax (approx 6% CGST + 6% SGST based on total voucher proportion)
    item_tax_rate = (cgst_amt / total_amt) if total_amt > 0 else 0.06
    item_cgst = round(a_val * item_tax_rate, 2)
    item_sgst = round(a_val * item_tax_rate, 2)
    item_tot = round(a_val + item_cgst + item_sgst, 2)
    
    add_r(s2, [
        (idx, 9, 'n'),
        (vch['voucher_number'], 9, 's'),
        (inv_date_str, 9, 's'),
        (vch['party_name'], 4, 's'),
        (vch['party_gstin'], 9, 's'),
        (item['name'], 4, 's'),
        (item['hsn'], 9, 's'),
        (q_val, 5, 'n'),
        (u_val, 9, 's'),
        (r_val, 5, 'n'),
        (a_val, 5, 'n'),
        (item_cgst, 5, 'n'),
        (item_sgst, 5, 'n'),
        (item_tot, 5, 'n')
    ])
    
    csv_rows.append([
        idx,
        vch['voucher_number'],
        inv_date_str,
        vch['party_name'],
        vch['party_gstin'],
        item['name'],
        item['hsn'],
        q_val,
        u_val,
        r_val,
        a_val,
        item_cgst,
        item_sgst,
        item_tot
    ])

# Save Excel files
xlsx_local = os.path.abspath('AM_S_26-27_2735.xlsx')
xlsx_desktop = os.path.join(os.path.expanduser('~'), 'Desktop', 'AM_S_26-27_2735.xlsx')

xlsx.save(xlsx_local)
shutil.copyfile(xlsx_local, xlsx_desktop)
print(f"Saved Excel file to:\n 1) {xlsx_local}\n 2) {xlsx_desktop}")

# Save CSV files
csv_local = os.path.abspath('AM_S_26-27_2735.csv')
csv_desktop = os.path.join(os.path.expanduser('~'), 'Desktop', 'AM_S_26-27_2735.csv')

with open(csv_local, 'w', newline='', encoding='utf-8') as f:
    writer = csv.writer(f)
    writer.writerows(csv_rows)

shutil.copyfile(csv_local, csv_desktop)
print(f"Saved CSV file to:\n 1) {csv_local}\n 2) {csv_desktop}")
