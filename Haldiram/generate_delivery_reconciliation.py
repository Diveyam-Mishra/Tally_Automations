import os
import sys
import json
from datetime import datetime, timedelta, timezone
import requests
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.worksheet.datavalidation import DataValidation

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except:
        pass

def get_fieldassist_session():
    auth_path = os.path.join(os.path.dirname(__file__), 'auth.json')
    if not os.path.exists(auth_path):
        print("❌ auth.json not found! Please run `node save_login.js` first.")
        sys.exit(1)

    with open(auth_path, 'r', encoding='utf-8') as f:
        auth = json.load(f)

    token = None
    cookies = {}
    for c in auth.get('cookies', []):
        cookies[c['name']] = c['value']
        if c['name'] == 'accessToken':
            token = c['value']

    headers = {
        'Accept': 'application/json',
        'Authorization': f'Bearer {token}' if token else ''
    }
    return headers, cookies

def fetch_recent_shipments(headers, cookies, days_back=30):
    to_date = datetime.now(timezone.utc) + timedelta(days=1)
    from_date = to_date - timedelta(days=days_back)
    
    body_str = json.dumps({
        "fromDate": from_date.strftime("%m/%d/%Y"),
        "toDate": to_date.strftime("%m/%d/%Y")
    })
    
    url = f"https://dms-hsfpl.fieldassist.io/api/v1/shipment/?seller-id=19135&body={requests.utils.quote(body_str)}&has-sku-detail=false"
    r = requests.get(url, headers=headers, cookies=cookies, timeout=15)
    if r.status_code != 200:
        return []
    return r.json()

def fetch_shipment_details(shipment_id, headers, cookies):
    url = f"https://dms-hsfpl.fieldassist.io/api/v1/shipment/{shipment_id}?has-sku-detail=true"
    r = requests.get(url, headers=headers, cookies=cookies, timeout=15)
    if r.status_code != 200:
        return None
    return r.json()

def build_excel_reconciliation(shipment_data, output_path):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Settlement"
    ws.views.sheetView[0].showGridLines = True

    # Styling Palette
    NAVY_FILL = PatternFill(start_color="1F4E79", end_color="1F4E79", fill_type="solid")
    HEADER_FILL = PatternFill(start_color="2F5597", end_color="2F5597", fill_type="solid")
    BILL_FILL = PatternFill(start_color="D9E1F2", end_color="D9E1F2", fill_type="solid")
    ITEM_FILL = PatternFill(start_color="F9F9F9", end_color="F9F9F9", fill_type="solid")
    EXTRA_ITEM_FILL = PatternFill(start_color="FFF9E6", end_color="FFF9E6", fill_type="solid")
    SUMMARY_FILL = PatternFill(start_color="E2EFDA", end_color="E2EFDA", fill_type="solid")
    CARD_LABEL_FILL = PatternFill(start_color="D6DCE4", end_color="D6DCE4", fill_type="solid")
    HIGHLIGHT_YELLOW = PatternFill(start_color="FFF2CC", end_color="FFF2CC", fill_type="solid")
    CASH_HEADER_FILL = PatternFill(start_color="C6EFCE", end_color="C6EFCE", fill_type="solid")
    SPLIT_HEADER_FILL = PatternFill(start_color="FCE4D6", end_color="FCE4D6", fill_type="solid")

    TITLE_FONT = Font(name="Segoe UI", size=13, bold=True, color="FFFFFF")
    WHITE_BOLD_FONT = Font(name="Segoe UI", size=10, bold=True, color="FFFFFF")
    DARK_BOLD_FONT = Font(name="Segoe UI", size=10, bold=True, color="000000")
    BOLD_FONT = Font(name="Segoe UI", size=10, bold=True)
    REGULAR_FONT = Font(name="Segoe UI", size=10)
    ITALIC_FONT = Font(name="Segoe UI", size=9, italic=True, color="404040")
    CARD_NUM_FONT = Font(name="Segoe UI", size=11, bold=True)

    THIN_BORDER = Border(
        left=Side(style='thin', color='D0D0D0'),
        right=Side(style='thin', color='D0D0D0'),
        top=Side(style='thin', color='D0D0D0'),
        bottom=Side(style='thin', color='D0D0D0')
    )

    # 1. Main Title
    ws.merge_cells("A1:P1")
    title_cell = ws["A1"]
    title_cell.value = "AANAND MANGAL — DAILY SHIPMENT DELIVERY & CASH RECONCILIATION"
    title_cell.font = TITLE_FONT
    title_cell.fill = NAVY_FILL
    title_cell.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 30

    # 2. Metadata (Left side rows 3-7)
    shipment_no = shipment_data.get('shipmentNo', 'N/A')
    driver_name = shipment_data.get('driverName', 'N/A')
    vehicle_no = shipment_data.get('vehicleNo', 'N/A')
    date_str = (shipment_data.get('createdAt') or '')[:10]

    meta_info = [
        ("Load / Shipment No:", shipment_no),
        ("Driver Name:", driver_name),
        ("Vehicle Number:", vehicle_no),
        ("Shipment Date:", date_str),
        ("Settlement Status:", "In Progress")
    ]

    for idx, (lbl, val) in enumerate(meta_info, start=3):
        ws[f"A{idx}"] = lbl
        ws[f"A{idx}"].font = BOLD_FONT
        ws[f"B{idx}"] = val
        ws[f"B{idx}"].font = REGULAR_FONT
        ws[f"A{idx}"].alignment = Alignment(horizontal="right")
        ws[f"B{idx}"].alignment = Alignment(horizontal="left")

    # Group items by invoice
    items_by_inv = {}
    for item in shipment_data.get('shipmentItems', []):
        inv_no = item['invoiceNo']
        if inv_no not in items_by_inv:
            items_by_inv[inv_no] = {
                'invoiceNo': inv_no,
                'partyName': item.get('buyerFirmName', ''),
                'beat': item.get('beat', ''),
                'items': []
            }
        items_by_inv[inv_no]['items'].append(item)

    max_row = 15 + len(items_by_inv) * 2 + sum(len(v['items']) for v in items_by_inv.values()) + 10

    # 3. Live Cash Settlement Summary Cards (Rows 3-8, Columns H to O)
    summary_labels = [
        ("H3", "I3", "Total Original Value (₹):", f'=SUMIF(A12:A{max_row}, "BILL*", H12:H{max_row})'),
        ("H4", "I4", "Total Delivered Value (₹):", f'=SUMIF(A12:A{max_row}, "BILL*", I12:I{max_row})'),
        ("H5", "I5", "Total Online / UPI (₹):", f'=SUMIF(A12:A{max_row}, "BILL*", M12:M{max_row})'),
        ("H6", "I6", "Total Cheques (₹):", f'=SUMIF(A12:A{max_row}, "BILL*", N12:N{max_row})'),
        ("H7", "I7", "Total Signed / Udhar (₹):", f'=SUMIF(A12:A{max_row}, "BILL*", O12:O{max_row})'),
        ("H8", "I8", "Total Cancelled (₹):", f'=SUMIFS(H12:H{max_row}, A12:A{max_row}, "BILL*", J12:J{max_row}, "Cancelled")'),
    ]

    for lbl_c, val_c, label, formula in summary_labels:
        ws[lbl_c] = label
        ws[lbl_c].font = BOLD_FONT
        ws[lbl_c].fill = CARD_LABEL_FILL
        ws[lbl_c].alignment = Alignment(horizontal="right")

        ws[val_c] = formula
        ws[val_c].font = CARD_NUM_FONT
        ws[val_c].alignment = Alignment(horizontal="right")
        ws[val_c].border = THIN_BORDER
        ws[val_c].number_format = '₹#,##0.00'
        ws[val_c].fill = SUMMARY_FILL

    # Cash Drawer Card (Cols L, M, N)
    cash_card = [
        ("L3", "M3", "N3", "EXPECTED CASH FROM DRIVER (₹):", f'=SUMIF(A12:A{max_row}, "BILL*", L12:L{max_row})', SUMMARY_FILL),
        ("L4", "M4", "N4", "ACTUAL CASH HANDED OVER (₹):", 0, HIGHLIGHT_YELLOW),
        ("L5", "M5", "N5", "DIFFERENCE / VARIANCE (₹):", "=(N4-N3)", SUMMARY_FILL),
    ]

    for l_c, m_c, val_c, label, formula, fill_c in cash_card:
        ws.merge_cells(f"{l_c}:{m_c}")
        ws[l_c] = label
        ws[l_c].font = BOLD_FONT
        ws[l_c].fill = CARD_LABEL_FILL
        ws[l_c].alignment = Alignment(horizontal="right", vertical="center")

        ws[val_c] = formula
        ws[val_c].font = CARD_NUM_FONT
        ws[val_c].alignment = Alignment(horizontal="right", vertical="center")
        ws[val_c].border = THIN_BORDER
        ws[val_c].number_format = '₹#,##0.00'
        ws[val_c].fill = fill_c

    ws.merge_cells("L6:M6")
    ws["L6"] = "Settlement Status:"
    ws["L6"].font = BOLD_FONT
    ws["L6"].fill = CARD_LABEL_FILL
    ws["L6"].alignment = Alignment(horizontal="right", vertical="center")

    ws["N6"] = '=IF(N5=0, "CASH MATCHED (OK)", IF(N5<0, "CASH SHORTAGE", "CASH EXCESS"))'
    ws["N6"].font = BOLD_FONT
    ws["N6"].alignment = Alignment(horizontal="center", vertical="center")
    ws["N6"].fill = SUMMARY_FILL
    ws["N6"].border = THIN_BORDER

    # 4. Table Headers (Row 11)
    headers = [
        ("A", "Type", 12, HEADER_FILL, WHITE_BOLD_FONT),
        ("B", "Bill No / Product Description", 38, HEADER_FILL, WHITE_BOLD_FONT),
        ("C", "Party / Retailer / Batch", 32, HEADER_FILL, WHITE_BOLD_FONT),
        ("D", "Beat / Cat", 18, HEADER_FILL, WHITE_BOLD_FONT),
        ("E", "Price (₹)", 13, HEADER_FILL, WHITE_BOLD_FONT),
        ("F", "Order Qty", 11, HEADER_FILL, WHITE_BOLD_FONT),
        ("G", "Deliv Qty", 11, HEADER_FILL, WHITE_BOLD_FONT),
        ("H", "Original Amt (₹)", 15, HEADER_FILL, WHITE_BOLD_FONT),
        ("I", "Delivered Amt (₹)", 16, HEADER_FILL, WHITE_BOLD_FONT),
        ("J", "Payment Method", 17, HEADER_FILL, WHITE_BOLD_FONT),
        ("K", "Split / Non-Cash (₹)", 18, SPLIT_HEADER_FILL, DARK_BOLD_FONT),
        ("L", "CASH (₹)", 15, CASH_HEADER_FILL, DARK_BOLD_FONT),
        ("M", "ONLINE / UPI (₹)", 15, SPLIT_HEADER_FILL, DARK_BOLD_FONT),
        ("N", "CHEQUE (₹)", 15, SPLIT_HEADER_FILL, DARK_BOLD_FONT),
        ("O", "SIGNED / UDHAR (₹)", 16, SPLIT_HEADER_FILL, DARK_BOLD_FONT),
        ("P", "Cheque No / UTR / Remarks", 24, HEADER_FILL, WHITE_BOLD_FONT)
    ]

    for col, text, width, fill, font in headers:
        cell = ws[f"{col}11"]
        cell.value = text
        cell.font = font
        cell.fill = fill
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = THIN_BORDER
        ws.column_dimensions[col].width = width

    ws.row_dimensions[11].height = 28

    # Data Validation for Payment Method Dropdown
    dv_method = DataValidation(
        type="list",
        formula1='"Cash,Online / UPI,Cheque,Signed / Udhar,Cash + Online,Cash + Signed,Cash + Cheque,Cancelled,Other Driver"',
        allow_blank=False
    )
    ws.add_data_validation(dv_method)

    current_row = 12
    bill_index = 1

    for inv_no, inv_data in items_by_inv.items():
        bill_row = current_row
        items = inv_data['items']
        num_items = len(items)
        first_item_row = bill_row + 1
        extra_row = first_item_row + num_items
        last_item_row = extra_row

        # --- BILL ROW ---
        ws[f"A{bill_row}"] = f"BILL #{bill_index}"
        ws[f"B{bill_row}"] = inv_no
        ws[f"C{bill_row}"] = inv_data['partyName']
        ws[f"D{bill_row}"] = inv_data['beat']
        ws[f"E{bill_row}"] = ""
        ws[f"F{bill_row}"] = ""
        ws[f"G{bill_row}"] = ""

        orig_val = sum(float(it.get('totalValue', 0.0)) for it in items)
        ws[f"H{bill_row}"] = round(orig_val, 2)
        ws[f"H{bill_row}"].number_format = '₹#,##0.00'

        # Delivered amount: sum of all sub-items + extra item row
        ws[f"I{bill_row}"] = f"=SUM(I{first_item_row}:I{last_item_row})"
        ws[f"I{bill_row}"].number_format = '₹#,##0.00'

        # Payment Method Dropdown: default Cash
        ws[f"J{bill_row}"] = "Cash"
        dv_method.add(ws[f"J{bill_row}"])

        # Col K: Split / Non-Cash Amount (User enters online/signed/cheque portion here if split)
        ws[f"K{bill_row}"] = 0
        ws[f"K{bill_row}"].number_format = '₹#,##0.00'

        # Col L: CASH (₹)
        ws[f"L{bill_row}"] = (
            f'=IF(OR(J{bill_row}="Cancelled", J{bill_row}="Other Driver"), 0, '
            f'IF(J{bill_row}="Cash", I{bill_row}, '
            f'IF(J{bill_row}="Online / UPI", 0, '
            f'IF(J{bill_row}="Cheque", 0, '
            f'IF(J{bill_row}="Signed / Udhar", 0, '
            f'IF(OR(J{bill_row}="Cash + Online", J{bill_row}="Cash + Signed", J{bill_row}="Cash + Cheque"), '
            f'MAX(0, I{bill_row}-K{bill_row}), I{bill_row}))))))'
        )
        ws[f"L{bill_row}"].number_format = '₹#,##0.00'

        # Col M: ONLINE / UPI (₹)
        ws[f"M{bill_row}"] = f'=IF(J{bill_row}="Online / UPI", I{bill_row}, IF(J{bill_row}="Cash + Online", K{bill_row}, 0))'
        ws[f"M{bill_row}"].number_format = '₹#,##0.00'

        # Col N: CHEQUE (₹)
        ws[f"N{bill_row}"] = f'=IF(J{bill_row}="Cheque", I{bill_row}, IF(J{bill_row}="Cash + Cheque", K{bill_row}, 0))'
        ws[f"N{bill_row}"].number_format = '₹#,##0.00'

        # Col O: SIGNED / UDHAR (₹)
        ws[f"O{bill_row}"] = f'=IF(J{bill_row}="Signed / Udhar", I{bill_row}, IF(J{bill_row}="Cash + Signed", K{bill_row}, 0))'
        ws[f"O{bill_row}"].number_format = '₹#,##0.00'

        ws[f"P{bill_row}"] = ""

        for col in ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L", "M", "N", "O", "P"]:
            cell = ws[f"{col}{bill_row}"]
            cell.font = BOLD_FONT
            cell.fill = BILL_FILL
            cell.border = THIN_BORDER
            if col in ["H", "I", "K", "L", "M", "N", "O"]:
                cell.alignment = Alignment(horizontal="right", vertical="center")
            elif col in ["A", "J"]:
                cell.alignment = Alignment(horizontal="center", vertical="center")
            else:
                cell.alignment = Alignment(horizontal="left", vertical="center")

        ws[f"K{bill_row}"].fill = HIGHLIGHT_YELLOW
        ws[f"L{bill_row}"].fill = CASH_HEADER_FILL
        ws.row_dimensions[bill_row].height = 24
        current_row += 1

        # --- SUB-ITEMS ROWS ---
        for item in items:
            item_row = current_row
            name = item.get('name', 'Product')
            batch = item.get('batchNo', '')
            qty = float(item.get('quantity', 0))
            item_val = float(item.get('totalValue', 0.0))
            # Price including GST per unit so delivered value matches invoice total
            unit_price_inc_gst = round(item_val / qty, 2) if qty > 0 else float(item.get('price', 0.0))

            ws[f"A{item_row}"] = "  ↳ SKU"
            ws[f"B{item_row}"] = f"   {name}"
            ws[f"C{item_row}"] = f"Batch: {batch}" if batch else ""
            ws[f"D{item_row}"] = item.get('category', '')
            ws[f"E{item_row}"] = unit_price_inc_gst
            ws[f"E{item_row}"].number_format = '₹#,##0.00'
            ws[f"F{item_row}"] = int(qty) if qty.is_integer() else qty
            ws[f"G{item_row}"] = int(qty) if qty.is_integer() else qty  # Delivered Qty default equals Ordered Qty!
            ws[f"H{item_row}"] = round(item_val, 2)
            ws[f"H{item_row}"].number_format = '₹#,##0.00'
            
            # Delivered amount formula: proportional to Delivered Qty / Ordered Qty
            if qty > 0:
                ws[f"I{item_row}"] = f"=ROUND(G{item_row}*(H{item_row}/F{item_row}), 2)"
            else:
                ws[f"I{item_row}"] = f"=(G{item_row}*E{item_row})"
            ws[f"I{item_row}"].number_format = '₹#,##0.00'

            for c in ["J", "K", "L", "M", "N", "O", "P"]:
                ws[f"{c}{item_row}"] = ""

            for col in ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L", "M", "N", "O", "P"]:
                cell = ws[f"{col}{item_row}"]
                cell.font = ITALIC_FONT
                cell.fill = ITEM_FILL
                cell.border = THIN_BORDER
                if col in ["E", "F", "G", "H", "I"]:
                    cell.alignment = Alignment(horizontal="right", vertical="center")

            # Group item row under the bill row
            ws.row_dimensions[item_row].outline_level = 1
            ws.row_dimensions[item_row].height = 20
            current_row += 1

        # --- EXTRA / ADDED ITEM ROW ---
        ws[f"A{extra_row}"] = "  ↳ [+ Extra Item]"
        ws[f"B{extra_row}"] = ""  # User can type extra product name here
        ws[f"C{extra_row}"] = "Extra / Adjustment"
        ws[f"D{extra_row}"] = ""
        ws[f"E{extra_row}"] = 0.00
        ws[f"E{extra_row}"].number_format = '₹#,##0.00'
        ws[f"F{extra_row}"] = 0
        ws[f"G{extra_row}"] = 0
        ws[f"H{extra_row}"] = 0.00
        ws[f"H{extra_row}"].number_format = '₹#,##0.00'
        ws[f"I{extra_row}"] = f"=(G{extra_row}*E{extra_row})"
        ws[f"I{extra_row}"].number_format = '₹#,##0.00'

        for c in ["J", "K", "L", "M", "N", "O", "P"]:
            ws[f"{c}{extra_row}"] = ""

        for col in ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L", "M", "N", "O", "P"]:
            cell = ws[f"{col}{extra_row}"]
            cell.font = ITALIC_FONT
            cell.fill = EXTRA_ITEM_FILL
            cell.border = THIN_BORDER
            if col in ["E", "F", "G", "H", "I"]:
                cell.alignment = Alignment(horizontal="right", vertical="center")

        ws.row_dimensions[extra_row].outline_level = 1
        ws.row_dimensions[extra_row].height = 20
        current_row += 1

        bill_index += 1

    wb.save(output_path)
    return output_path

def main():
    print("=" * 65)
    print("📦 Haldiram Daily Delivery & Collection Reconciliation Generator")
    print("=" * 65)

    headers, cookies = get_fieldassist_session()
    print("📡 Fetching active shipments from FieldAssist...")
    shipments = fetch_recent_shipments(headers, cookies, days_back=30)

    if not shipments:
        print("❌ No shipments found for the last 30 days.")
        return

    print(f"\n📋 Active Shipments ({len(shipments)} found):")
    for idx, s in enumerate(shipments, 1):
        s_no = s.get('shipmentNo', '')
        d_name = s.get('driverName', 'N/A')
        val = s.get('totalValue', 0.0)
        dt = (s.get('createdAt') or '')[:10]
        v_no = s.get('vehicleNo', '')
        print(f"  [{idx:2d}] {s_no:24s} | Driver: {d_name:14s} | Vehicle: {v_no:14s} | Total: Rs.{val:9.2f} | Date: {dt}")

    default_ship = shipments[0]
    prompt = f"\n👉 Select shipment [1-{len(shipments)}] or press ENTER for latest [{default_ship['shipmentNo']}]: "
    try:
        choice = input(prompt).strip()
    except EOFError:
        choice = ""

    chosen_ship = default_ship
    if choice.isdigit() and 1 <= int(choice) <= len(shipments):
        chosen_ship = shipments[int(choice) - 1]

    ship_id = chosen_ship['id']
    ship_no = chosen_ship['shipmentNo']
    clean_ship_no = ship_no.replace('/', '_')
    driver = (chosen_ship.get('driverName') or 'Driver').strip().replace(' ', '_')

    print(f"\n⏳ Fetching all bills and line items for {ship_no} (ID: {ship_id})...")
    details = fetch_shipment_details(ship_id, headers, cookies)
    if not details:
        return

    out_dir = os.path.join(os.path.dirname(__file__), 'reconciliation_sheets')
    os.makedirs(out_dir, exist_ok=True)
    filename = f"Reconciliation_{clean_ship_no}_{driver}.xlsx"
    out_path = os.path.join(out_dir, filename)

    print("📊 Generating Excel Reconciliation Workbook with Split Payment support...")
    try:
        build_excel_reconciliation(details, out_path)
    except PermissionError:
        ts = datetime.now().strftime("%H%M%S")
        filename = f"Reconciliation_{clean_ship_no}_{driver}_{ts}.xlsx"
        out_path = os.path.join(out_dir, filename)
        build_excel_reconciliation(details, out_path)
        print(f"ℹ️ (Original file was open in Excel, saved as {filename})")

    print("\n" + "=" * 65)
    print(f"🎉 SUCCESS! Excel Workbook created at:")
    print(f"   {out_path}")
    print("=" * 65)

    try:
        os.startfile(out_path)
        print("🚀 Opening in Excel...")
    except Exception as e:
        pass

if __name__ == '__main__':
    main()
