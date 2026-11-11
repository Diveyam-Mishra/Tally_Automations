import os
import sys
import json

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except:
        pass
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

def create_reconciliation_workbook(shipment_data, output_filename="Delivery_Collection_Reconciliation.xlsx"):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Collection Settlement"
    ws.views.sheetView[0].showGridLines = True

    # Palette
    NAVY_FILL = PatternFill(start_color="1F4E79", end_color="1F4E79", fill_type="solid")
    HEADER_FILL = PatternFill(start_color="2F5597", end_color="2F5597", fill_type="solid")
    BILL_FILL = PatternFill(start_color="D9E1F2", end_color="D9E1F2", fill_type="solid")
    ITEM_FILL = PatternFill(start_color="F2F2F2", end_color="F2F2F2", fill_type="solid")
    SUMMARY_FILL = PatternFill(start_color="E2EFDA", end_color="E2EFDA", fill_type="solid")
    CARD_LABEL_FILL = PatternFill(start_color="D6DCE4", end_color="D6DCE4", fill_type="solid")
    HIGHLIGHT_YELLOW = PatternFill(start_color="FFF2CC", end_color="FFF2CC", fill_type="solid")
    GREEN_FILL = PatternFill(start_color="C6EFCE", end_color="C6EFCE", fill_type="solid")
    RED_FILL = PatternFill(start_color="FFC7CE", end_color="FFC7CE", fill_type="solid")

    WHITE_BOLD_FONT = Font(name="Segoe UI", size=11, bold=True, color="FFFFFF")
    TITLE_FONT = Font(name="Segoe UI", size=14, bold=True, color="FFFFFF")
    BOLD_FONT = Font(name="Segoe UI", size=10, bold=True)
    REGULAR_FONT = Font(name="Segoe UI", size=10)
    ITALIC_FONT = Font(name="Segoe UI", size=9, italic=True, color="595959")
    CARD_NUM_FONT = Font(name="Segoe UI", size=11, bold=True)

    THIN_BORDER = Border(
        left=Side(style='thin', color='D9D9D9'),
        right=Side(style='thin', color='D9D9D9'),
        top=Side(style='thin', color='D9D9D9'),
        bottom=Side(style='thin', color='D9D9D9')
    )
    DOUBLE_BOTTOM_BORDER = Border(
        left=Side(style='thin', color='D9D9D9'),
        right=Side(style='thin', color='D9D9D9'),
        top=Side(style='thin', color='D9D9D9'),
        bottom=Side(style='double', color='000000')
    )

    # 1. Main Header Title
    ws.merge_cells("A1:K1")
    title_cell = ws["A1"]
    title_cell.value = "AANAND MANGAL — DAILY SHIPMENT DELIVERY & CASH RECONCILIATION"
    title_cell.font = TITLE_FONT
    title_cell.fill = NAVY_FILL
    title_cell.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 32

    # 2. Shipment Details (Left side rows 3-7)
    shipment_no = shipment_data.get('shipmentNo', 'SHIP/19135/0859')
    driver_name = shipment_data.get('driverName', 'GANESH')
    vehicle_no = shipment_data.get('vehicleNo', 'MP 09 ZM 9276')
    created_at = shipment_data.get('createdAt', '')[:10]

    meta_info = [
        ("Load / Shipment No:", shipment_no),
        ("Driver Name:", driver_name),
        ("Vehicle Number:", vehicle_no),
        ("Shipment Date:", created_at or "01-Nov-2026"),
        ("Status:", "Reconciliation in Progress")
    ]

    for idx, (lbl, val) in enumerate(meta_info, start=3):
        ws[f"A{idx}"] = lbl
        ws[f"A{idx}"].font = BOLD_FONT
        ws[f"B{idx}"] = val
        ws[f"B{idx}"].font = REGULAR_FONT
        ws[f"A{idx}"].alignment = Alignment(horizontal="right")
        ws[f"B{idx}"].alignment = Alignment(horizontal="left")

    # 3. Live Cash Settlement Summary Card (Right side rows 3-8, Columns G-K)
    summary_labels = [
        ("G3", "H3", "Total Shipment Value (₹):", "=SUM(E12:E10000)"),
        ("G4", "H4", "Less: Online / UPI (₹):", '=SUMIFS(H12:H10000, G12:G10000, "Online")'),
        ("G5", "H5", "Less: Cheque Received (₹):", '=SUMIFS(H12:H10000, G12:G10000, "Cheque")'),
        ("G6", "H6", "Less: Signed Bills / Pay Later (₹):", '=SUMIFS(F12:F10000, G12:G10000, "Signed Bill")'),
        ("G7", "H7", "Less: Cancelled Bills (₹):", '=SUMIFS(E12:E10000, G12:G10000, "Cancelled")'),
        ("J3", "K3", "EXPECTED CASH (₹):", "=(H3-H4-H5-H6-H7)"),
        ("J4", "K4", "ACTUAL CASH HANDED OVER (₹):", 0),  # User input cell!
        ("J5", "K5", "DIFFERENCE / DISCREPANCY (₹):", "=(K4-K3)")
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
        if val_c == "K4":
            ws[val_c].fill = HIGHLIGHT_YELLOW  # highlighted for staff input!
            ws[val_c].number_format = '₹#,##0.00'
        elif val_c in ["H3", "H4", "H5", "H6", "H7", "K3", "K5"]:
            ws[val_c].number_format = '₹#,##0.00'
            ws[val_c].fill = SUMMARY_FILL

    ws["J6"] = "Match Status:"
    ws["J6"].font = BOLD_FONT
    ws["J6"].fill = CARD_LABEL_FILL
    ws["K6"] = '=IF(K5=0, "✅ CASH MATCHED", IF(K5<0, "⚠️ CASH SHORTAGE", "⚠️ CASH EXCESS"))'
    ws["K6"].font = BOLD_FONT
    ws["K6"].alignment = Alignment(horizontal="center")

    # 4. Table Headers (Row 11)
    headers = [
        ("A", "Type", 10),
        ("B", "Bill No / Item Details", 38),
        ("C", "Party / Retailer / Batch", 30),
        ("D", "Beat / Pkg", 25),
        ("E", "Original Amt (₹)", 16),
        ("F", "Delivered Amt (₹)", 16),
        ("G", "Payment Method", 18),
        ("H", "Amount Collected (₹)", 18),
        ("I", "Shortage / Diff (₹)", 16),
        ("J", "Cheque No / Online Ref", 22),
        ("K", "Remarks / Notes", 25)
    ]

    for col, text, width in headers:
        cell = ws[f"{col}11"]
        cell.value = text
        cell.font = WHITE_BOLD_FONT
        cell.fill = HEADER_FILL
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = THIN_BORDER
        ws.column_dimensions[col].width = width

    ws.row_dimensions[11].height = 28

    # 5. Populate Bills and Sub-items
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

    # Data validation dropdown for Payment Method
    dv = DataValidation(type="list", formula1='"Cash,Online,Cheque,Signed Bill,Cancelled"', allow_blank=False)
    ws.add_data_validation(dv)

    current_row = 12
    bill_index = 1

    for inv_no, inv_data in items_by_inv.items():
        bill_row = current_row
        items = inv_data['items']
        num_items = len(items)
        first_item_row = bill_row + 1
        last_item_row = bill_row + num_items

        # --- MAIN BILL ROW ---
        ws[f"A{bill_row}"] = f"BILL #{bill_index}"
        ws[f"B{bill_row}"] = inv_no
        ws[f"C{bill_row}"] = inv_data['partyName']
        ws[f"D{bill_row}"] = inv_data['beat']

        # Original amount
        orig_val = sum(float(it.get('totalValue', 0.0)) for it in items)
        ws[f"E{bill_row}"] = round(orig_val, 2)
        ws[f"E{bill_row}"].number_format = '₹#,##0.00'

        # Delivered amount: sum of sub items below
        ws[f"F{bill_row}"] = f"=SUM(F{first_item_row}:F{last_item_row})"
        ws[f"F{bill_row}"].number_format = '₹#,##0.00'

        # Payment Method dropdown
        ws[f"G{bill_row}"] = "Cash"  # Default is Cash!
        dv.add(ws[f"G{bill_row}"])

        # Collected Amount: Formula based on method
        ws[f"H{bill_row}"] = f'=IF(G{bill_row}="Cancelled", 0, IF(G{bill_row}="Signed Bill", 0, F{bill_row}))'
        ws[f"H{bill_row}"].number_format = '₹#,##0.00'

        # Shortage / Diff
        ws[f"I{bill_row}"] = f"=(E{bill_row}-F{bill_row})"
        ws[f"I{bill_row}"].number_format = '₹#,##0.00'

        ws[f"J{bill_row}"] = ""
        ws[f"K{bill_row}"] = ""

        # Formatting bill row
        for col in ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K"]:
            cell = ws[f"{col}{bill_row}"]
            cell.font = BOLD_FONT
            cell.fill = BILL_FILL
            cell.border = THIN_BORDER
            if col in ["E", "F", "H", "I"]:
                cell.alignment = Alignment(horizontal="right")
            elif col in ["A", "G"]:
                cell.alignment = Alignment(horizontal="center")

        ws.row_dimensions[bill_row].height = 24
        current_row += 1

        # --- SUB-ITEMS ROWS ---
        for item in items:
            item_row = current_row
            name = item.get('name', 'Product')
            batch = item.get('batchNo', '')
            qty = float(item.get('quantity', 0))
            price = float(item.get('price', 0.0))
            gst_pct = float(item.get('gstPercent', 5))
            tax_multiplier = 1 + (gst_pct / 100.0)
            item_val = float(item.get('totalValue', 0.0))

            ws[f"A{item_row}"] = "  ↳ SKU"
            ws[f"B{item_row}"] = f"   {name}"
            ws[f"C{item_row}"] = f"Batch: {batch}"
            ws[f"D{item_row}"] = f"{int(qty)} Pcs @ ₹{price:.2f}"
            ws[f"E{item_row}"] = round(item_val, 2)
            ws[f"E{item_row}"].number_format = '₹#,##0.00'

            # Delivered item amount formula
            ws[f"F{item_row}"] = round(item_val, 2)
            ws[f"F{item_row}"].number_format = '₹#,##0.00'

            ws[f"G{item_row}"] = ""
            ws[f"H{item_row}"] = ""
            ws[f"I{item_row}"] = ""
            ws[f"J{item_row}"] = ""
            ws[f"K{item_row}"] = ""

            for col in ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K"]:
                cell = ws[f"{col}{item_row}"]
                cell.font = ITALIC_FONT
                cell.fill = ITEM_FILL
                cell.border = THIN_BORDER
                if col in ["E", "F"]:
                    cell.alignment = Alignment(horizontal="right")

            # Group item row under the bill row
            ws.row_dimensions[item_row].outline_level = 1
            ws.row_dimensions[item_row].height = 20
            current_row += 1

        bill_index += 1

    wb.save(output_filename)
    print(f"✅ Created Excel sheet: {output_filename}")

if __name__ == "__main__":
    with open('shipment_detail_result.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    create_reconciliation_workbook(data, "Delivery_Collection_Reconciliation_SHIP_0859.xlsx")
