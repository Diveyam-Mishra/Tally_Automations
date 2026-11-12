import json
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

wb = openpyxl.Workbook()

# ==============================================================================
# COLOR PALETTE & STYLES
# ==============================================================================
NAVY_HEADER = PatternFill(start_color='1F4E78', end_color='1F4E78', fill_type='solid')
STEEL_HEADER = PatternFill(start_color='2F5597', end_color='2F5597', fill_type='solid')
SECTION_HEADER = PatternFill(start_color='D9E1F2', end_color='D9E1F2', fill_type='solid')
CARD_BG = PatternFill(start_color='F2F4F7', end_color='F2F4F7', fill_type='solid')
TOTAL_FILL = PatternFill(start_color='D9E1F2', end_color='D9E1F2', fill_type='solid')
PROFIT_FILL = PatternFill(start_color='E2EFDA', end_color='E2EFDA', fill_type='solid')
ALERT_FILL = PatternFill(start_color='FCE4D6', end_color='FCE4D6', fill_type='solid')
YELLOW_FILL = PatternFill(start_color='FFF2CC', end_color='FFF2CC', fill_type='solid')

TITLE_FONT = Font(name='Segoe UI', size=15, bold=True, color='1F4E78')
SUB_FONT = Font(name='Segoe UI', size=9, italic=True, color='595959')
HEADER_FONT = Font(name='Segoe UI', size=10, bold=True, color='FFFFFF')
DARK_HEADER_FONT = Font(name='Segoe UI', size=10, bold=True, color='1F4E78')
BOLD_FONT = Font(name='Segoe UI', size=10, bold=True)
REG_FONT = Font(name='Segoe UI', size=10)
NUM_FONT = Font(name='Segoe UI', size=10)
NUM_BOLD = Font(name='Segoe UI', size=10, bold=True)
BIG_KPI_FONT = Font(name='Segoe UI', size=14, bold=True, color='1F4E78')
BIG_KPI_GREEN = Font(name='Segoe UI', size=14, bold=True, color='375623')
BIG_KPI_RED = Font(name='Segoe UI', size=14, bold=True, color='C00000')

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
    bottom=Side(style='double', color='1F4E78')
)

# Load existing 17 signed bills
signed_bills_data = []
try:
    with open('C:/Users/fixadmin/TALLY/signed_bills_data.json', 'r', encoding='utf-8') as f:
        signed_bills_data = json.load(f)
except:
    pass

# ==============================================================================
# TAB 1: 📊 EXECUTIVE DASHBOARD
# ==============================================================================
ws_dash = wb.active
ws_dash.title = '📊 Executive Dashboard'
ws_dash.views.sheetView[0].showGridLines = True

ws_dash['A1'] = "ANAND MANGAL (HALDIRAM) - EXECUTIVE P&L & OPERATIONS DASHBOARD"
ws_dash['A1'].font = TITLE_FONT
ws_dash['A2'] = "Real-time Profit & Loss, Cash Collections, Market Udhaari & Expense Tracking"
ws_dash['A2'].font = SUB_FONT

# KPI CARDS ROW 4 to 6
cards = [
    ("B4", "C4", "B5", "C5", "MONTHLY SALES (₹)", "='📅 Daily P&L & Collections'!B39", BIG_KPI_FONT, '₹#,##0.00'),
    ("D4", "E4", "D5", "E5", "NET PROFIT (REAL P&L)", "='📅 Daily P&L & Collections'!K39", BIG_KPI_GREEN, '₹#,##0.00'),
    ("F4", "G4", "F5", "G5", "NET PROFIT MARGIN", "=IF(B5>0, D5/B5, 0)", BIG_KPI_FONT, '0.0%'),
    ("B7", "C7", "B8", "C8", "CASH IN DRAWER (MTD)", "='📅 Daily P&L & Collections'!M39", BIG_KPI_FONT, '₹#,##0.00'),
    ("D7", "E7", "D8", "E8", "TOTAL MARKET UDHAARI", "='📝 Signed Bills Log'!D4", BIG_KPI_RED, '₹#,##0.00'),
    ("F7", "G7", "F8", "G8", "STAFF ADVANCES OWED", "='💰 Loans & Lending (Khaata)'!E4", BIG_KPI_FONT, '₹#,##0.00')
]

for l1, l2, v1, v2, label, formula, val_font, num_fmt in cards:
    ws_dash.merge_cells(f"{l1}:{l2}")
    ws_dash[l1] = label
    ws_dash[l1].font = DARK_HEADER_FONT
    ws_dash[l1].fill = SECTION_HEADER
    ws_dash[l1].alignment = Alignment(horizontal='center', vertical='center')
    
    ws_dash.merge_cells(f"{v1}:{v2}")
    ws_dash[v1] = formula
    ws_dash[v1].font = val_font
    ws_dash[v1].fill = CARD_BG
    ws_dash[v1].alignment = Alignment(horizontal='center', vertical='center')
    ws_dash[v1].number_format = num_fmt

    for r in [ws_dash[l1], ws_dash[l2], ws_dash[v1], ws_dash[v2]]:
        r.border = THIN_BORDER

# P&L WATERFALL TABLE (Rows 11 to 24)
ws_dash['B11'] = "MONTHLY FINANCIAL STATEMENT (TRUE P&L BREAKDOWN)"
ws_dash.merge_cells("B11:E11")
ws_dash['B11'].font = HEADER_FONT
ws_dash['B11'].fill = NAVY_HEADER
ws_dash['B11'].alignment = Alignment(horizontal='center', vertical='center')

pnl_lines = [
    ("Gross Delivered Sales Revenue", "='📅 Daily P&L & Collections'!B39", REG_FONT, False),
    ("Less: Cost of Goods Sold (Purchase from Haldiram)", "=-'📅 Daily P&L & Collections'!D39", REG_FONT, False),
    ("= GROSS PROFIT", "=D12+D13", BOLD_FONT, True),
    ("Operating Expenses:", "", Font(name='Segoe UI', size=10, italic=True), False),
    ("   - Van Diesel / Fuel", "=-'📅 Daily P&L & Collections'!F39", REG_FONT, False),
    ("   - Driver & Helper Daily Wages", "=-'📅 Daily P&L & Collections'!G39", REG_FONT, False),
    ("   - Vehicle Repair & Maintenance", "=-'📅 Daily P&L & Collections'!H39", REG_FONT, False),
    ("   - Godown Electricity & Overheads", "=-'📅 Daily P&L & Collections'!I39", REG_FONT, False),
    ("Total Operating Expenses", "=SUM(D16:D19)", BOLD_FONT, False),
    ("= NET OPERATING PROFIT / LOSS", "=D14+D20", BOLD_FONT, True),
    ("Less: Market Udhaari Provision (Signed Bills Pending)", "=-'📝 Signed Bills Log'!D4", Font(name='Segoe UI', size=9, italic=True), False),
    ("= REAL NET PROFIT (CASH IN HAND IMPACT)", "=D21+D22", BOLD_FONT, True)
]

for idx, (title, formula, f_style, is_highlight) in enumerate(pnl_lines, start=12):
    ws_dash.merge_cells(f"B{idx}:C{idx}")
    ws_dash[f"B{idx}"] = title
    ws_dash[f"B{idx}"].font = f_style
    ws_dash[f"B{idx}"].border = THIN_BORDER
    
    ws_dash[f"D{idx}"] = formula if formula else ""
    ws_dash[f"D{idx}"].font = f_style
    ws_dash[f"D{idx}"].border = THIN_BORDER
    ws_dash[f"D{idx}"].alignment = Alignment(horizontal='right')
    if formula:
        ws_dash[f"D{idx}"].number_format = '₹#,##0.00'

    if is_highlight:
        ws_dash[f"B{idx}"].fill = PROFIT_FILL
        ws_dash[f"D{idx}"].fill = PROFIT_FILL

# Operational Insights (Right Side Column G to I)
ws_dash['G11'] = "OPERATIONAL HEALTH SUMMARY"
ws_dash.merge_cells("G11:I11")
ws_dash['G11'].font = HEADER_FONT
ws_dash['G11'].fill = STEEL_HEADER
ws_dash['G11'].alignment = Alignment(horizontal='center', vertical='center')

insights = [
    ("Gross Margin Percentage:", "=IF(B5>0, D14/B5, 0)", '0.0%'),
    ("Operating Cost as % of Sales:", "=IF(B5>0, -D20/B5, 0)", '0.0%'),
    ("Net Profit Margin %:", "=IF(B5>0, D21/B5, 0)", '0.0%'),
    ("Total Pending Signed Bills Count:", "='📝 Signed Bills Log'!B4", '0'),
    ("Oldest Pending Signed Bill:", "='📝 Signed Bills Log'!F4", '0 "Days"'),
    ("Total UPI / Online Payments MTD:", "='📅 Daily P&L & Collections'!N39", '₹#,##0.00'),
    ("Total Cheques Collected MTD:", "='📅 Daily P&L & Collections'!O39", '₹#,##0.00'),
    ("Total Loans / Money You Owe:", "='💰 Loans & Lending (Khaata)'!K4", '₹#,##0.00'),
]

for idx, (label, formula, num_fmt) in enumerate(insights, start=12):
    ws_dash.merge_cells(f"G{idx}:H{idx}")
    ws_dash[f"G{idx}"] = label
    ws_dash[f"G{idx}"].font = REG_FONT
    ws_dash[f"G{idx}"].border = THIN_BORDER
    
    ws_dash[f"I{idx}"] = formula
    ws_dash[f"I{idx}"].font = NUM_BOLD
    ws_dash[f"I{idx}"].border = THIN_BORDER
    ws_dash[f"I{idx}"].alignment = Alignment(horizontal='right')
    ws_dash[f"I{idx}"].number_format = num_fmt

ws_dash.column_dimensions['A'].width = 4
ws_dash.column_dimensions['B'].width = 24
ws_dash.column_dimensions['C'].width = 20
ws_dash.column_dimensions['D'].width = 22
ws_dash.column_dimensions['E'].width = 4
ws_dash.column_dimensions['F'].width = 4
ws_dash.column_dimensions['G'].width = 24
ws_dash.column_dimensions['H'].width = 16
ws_dash.column_dimensions['I'].width = 18

# ==============================================================================
# TAB 2: 📅 DAILY P&L & COLLECTIONS
# ==============================================================================
ws_daily = wb.create_sheet('📅 Daily P&L & Collections')
ws_daily.views.sheetView[0].showGridLines = True

ws_daily['A1'] = "DAILY SALES, EXPENSES, P&L & CASH COLLECTIONS"
ws_daily['A1'].font = TITLE_FONT
ws_daily['A2'] = "Enter daily delivered sales and spends. Net Profit, Gross Margin, and Cash Balances compute automatically."
ws_daily['A2'].font = SUB_FONT

headers_daily = [
    ("A", "Date", 12),
    ("B", "Delivered Sales (₹)", 17),
    ("C", "Margin %", 11),
    ("D", "COGS / Cost (₹)", 16),
    ("E", "Gross Profit (₹)", 16),
    ("F", "Diesel / Fuel (₹)", 15),
    ("G", "Driver Wages (₹)", 15),
    ("H", "Vehicle Repair (₹)", 15),
    ("I", "Electricity / Misc (₹)", 16),
    ("J", "Total Operating Spends (₹)", 18),
    ("K", "DAILY NET P&L (₹)", 17),
    ("L", "Net Margin %", 13),
    ("M", "Cash Handed In (₹)", 16),
    ("N", "UPI / Online (₹)", 15),
    ("O", "Cheques (₹)", 14),
    ("P", "Total Collected (₹)", 16),
    ("Q", "Signed Bills Added (₹)", 16),
    ("R", "Signed Bills Cleared (₹)", 16),
    ("S", "Closing Market Udhaar (₹)", 18)
]

# Header Row 5 & 6
ws_daily['A5'] = "Date"
ws_daily['A5'].font = HEADER_FONT
ws_daily['A5'].fill = NAVY_HEADER
ws_daily['A5'].alignment = Alignment(horizontal='center', vertical='center')

ws_daily.merge_cells("B5:E5")
ws_daily['B5'] = "REVENUE & GROSS PROFIT"
ws_daily['B5'].font = HEADER_FONT
ws_daily['B5'].fill = NAVY_HEADER
ws_daily['B5'].alignment = Alignment(horizontal='center', vertical='center')

ws_daily.merge_cells("F5:J5")
ws_daily['F5'] = "DAILY OPERATING SPENDS (KHARCHA)"
ws_daily['F5'].font = HEADER_FONT
ws_daily['F5'].fill = STEEL_HEADER
ws_daily['F5'].alignment = Alignment(horizontal='center', vertical='center')

ws_daily.merge_cells("K5:L5")
ws_daily['K5'] = "REAL P&L"
ws_daily['K5'].font = HEADER_FONT
ws_daily['K5'].fill = NAVY_HEADER
ws_daily['K5'].alignment = Alignment(horizontal='center', vertical='center')

ws_daily.merge_cells("M5:P5")
ws_daily['M5'] = "COLLECTIONS RECEIVED"
ws_daily['M5'].font = HEADER_FONT
ws_daily['M5'].fill = STEEL_HEADER
ws_daily['M5'].alignment = Alignment(horizontal='center', vertical='center')

ws_daily.merge_cells("Q5:S5")
ws_daily['Q5'] = "MARKET UDHAARI (SIGNED BILLS)"
ws_daily['Q5'].font = HEADER_FONT
ws_daily['Q5'].fill = NAVY_HEADER
ws_daily['Q5'].alignment = Alignment(horizontal='center', vertical='center')

for col_letter, text, width in headers_daily:
    c = ws_daily[f"{col_letter}6"]
    c.value = text
    c.font = HEADER_FONT
    c.fill = NAVY_HEADER if col_letter in ['A', 'B', 'C', 'D', 'E', 'K', 'L', 'Q', 'R', 'S'] else STEEL_HEADER
    c.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
    c.border = THIN_BORDER
    ws_daily.column_dimensions[col_letter].width = width

ws_daily.merge_cells("A5:A6")

ws_daily.row_dimensions[5].height = 20
ws_daily.row_dimensions[6].height = 28

# Days 1 to 30 (Rows 7 to 36)
for day in range(1, 31):
    r = 6 + day
    ws_daily[f"A{r}"] = f"2026-11-{day:02d}"
    ws_daily[f"A{r}"].alignment = Alignment(horizontal='center')
    
    # Defaults
    ws_daily[f"B{r}"] = 0
    ws_daily[f"C{r}"] = 0.065  # 6.5% typical Haldiram margin
    ws_daily[f"C{r}"].number_format = '0.0%'
    
    ws_daily[f"D{r}"] = f"=B{r}*(1-C{r})"
    ws_daily[f"E{r}"] = f"=B{r}-D{r}"
    
    ws_daily[f"F{r}"] = 0  # Diesel
    ws_daily[f"G{r}"] = 0  # Driver Wages
    ws_daily[f"H{r}"] = 0  # Repair
    ws_daily[f"I{r}"] = "='⚡ Fixed Costs & Setup'!$C$9"  # Daily Fixed electricity & godown cost
    ws_daily[f"J{r}"] = f"=SUM(F{r}:I{r})"
    
    ws_daily[f"K{r}"] = f"=E{r}-J{r}"
    ws_daily[f"L{r}"] = f"=IF(B{r}>0, K{r}/B{r}, 0)"
    ws_daily[f"L{r}"].number_format = '0.0%'
    
    ws_daily[f"M{r}"] = 0  # Cash
    ws_daily[f"N{r}"] = 0  # UPI
    ws_daily[f"O{r}"] = 0  # Cheque
    ws_daily[f"P{r}"] = f"=SUM(M{r}:O{r})"
    
    ws_daily[f"Q{r}"] = 0  # New signed bills
    ws_daily[f"R{r}"] = 0  # Signed bills cleared
    
    if day == 1:
        ws_daily[f"S{r}"] = f"='⚡ Fixed Costs & Setup'!$C$12 + Q{r} - R{r}"
    else:
        ws_daily[f"S{r}"] = f"=S{r-1} + Q{r} - R{r}"

    # Formatting
    for col_letter, _, _ in headers_daily:
        cell = ws_daily[f"{col_letter}{r}"]
        cell.font = REG_FONT
        cell.border = THIN_BORDER
        if col_letter in ['B', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'M', 'N', 'O', 'P', 'Q', 'R', 'S']:
            cell.number_format = '₹#,##0.00'
            cell.alignment = Alignment(horizontal='right')
        elif col_letter in ['C', 'L']:
            cell.alignment = Alignment(horizontal='center')
    
    ws_daily[f"K{r}"].font = NUM_BOLD

# Total Row at Row 39
tot_row = 39
ws_daily[f"A{tot_row}"] = "TOTAL (MTD)"
ws_daily[f"A{tot_row}"].font = BOLD_FONT
ws_daily[f"A{tot_row}"].alignment = Alignment(horizontal='center')
ws_daily[f"A{tot_row}"].fill = TOTAL_FILL

ws_daily[f"B{tot_row}"] = "=SUM(B7:B36)"
ws_daily[f"C{tot_row}"] = "=AVERAGE(C7:C36)"
ws_daily[f"D{tot_row}"] = "=SUM(D7:D36)"
ws_daily[f"E{tot_row}"] = "=SUM(E7:E36)"
ws_daily[f"F{tot_row}"] = "=SUM(F7:F36)"
ws_daily[f"G{tot_row}"] = "=SUM(G7:G36)"
ws_daily[f"H{tot_row}"] = "=SUM(H7:H36)"
ws_daily[f"I{tot_row}"] = "=SUM(I7:I36)"
ws_daily[f"J{tot_row}"] = "=SUM(J7:J36)"
ws_daily[f"K{tot_row}"] = "=SUM(K7:K36)"
ws_daily[f"L{tot_row}"] = f"=IF(B{tot_row}>0, K{tot_row}/B{tot_row}, 0)"
ws_daily[f"M{tot_row}"] = "=SUM(M7:M36)"
ws_daily[f"N{tot_row}"] = "=SUM(N7:N36)"
ws_daily[f"O{tot_row}"] = "=SUM(O7:O36)"
ws_daily[f"P{tot_row}"] = "=SUM(P7:P36)"
ws_daily[f"Q{tot_row}"] = "=SUM(Q7:Q36)"
ws_daily[f"R{tot_row}"] = "=SUM(R7:R36)"
ws_daily[f"S{tot_row}"] = f"=S36"

for col_letter, _, _ in headers_daily:
    c = ws_daily[f"{col_letter}{tot_row}"]
    c.font = BOLD_FONT
    c.fill = TOTAL_FILL
    c.border = DOUBLE_BOTTOM_BORDER
    if col_letter in ['B', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'M', 'N', 'O', 'P', 'Q', 'R', 'S']:
        c.number_format = '₹#,##0.00'
        c.alignment = Alignment(horizontal='right')
    elif col_letter in ['C', 'L']:
        c.number_format = '0.0%'
        c.alignment = Alignment(horizontal='center')

# ==============================================================================
# TAB 3: 📝 SIGNED BILLS LOG
# ==============================================================================
ws_bills = wb.create_sheet('📝 Signed Bills Log')
ws_bills.views.sheetView[0].showGridLines = True

ws_bills['A1'] = "SIGNED BILLS (MARKET UDHAARI) DETAILED RECONCILIATION LOG"
ws_bills['A1'].font = TITLE_FONT
ws_bills['A2'] = "Every bill delivered on sign/credit. Mark 'Cleared' when cash/UPI arrives from the retailer."
ws_bills['A2'].font = SUB_FONT

# Top KPI Summary Cards
ws_bills['A4'] = "Total Bills Logged:"
ws_bills['B4'] = "=COUNTA(B7:B50)"
ws_bills['C4'] = "Total Market Owed (₹):"
ws_bills['D4'] = '=SUMIF(G7:G50, "Pending", F7:F50)'
ws_bills['E4'] = "Oldest Pending Bill:"
ws_bills['F4'] = '=IFERROR(MAX(H7:H50), 0)'

for c_pos in ['A4', 'B4', 'C4', 'D4', 'E4', 'F4']:
    ws_bills[c_pos].fill = CARD_BG
    ws_bills[c_pos].border = THIN_BORDER
    ws_bills[c_pos].font = BOLD_FONT

ws_bills['D4'].number_format = '₹#,##0.00'
ws_bills['D4'].font = BIG_KPI_RED

headers_bills = [
    ("A", "S.No", 6),
    ("B", "Bill No / ID", 14),
    ("C", "Full Invoice No", 18),
    ("D", "Retailer / Firm Name", 30),
    ("E", "Beat / Route", 22),
    ("F", "Bill Amount (₹)", 16),
    ("G", "Status", 14),
    ("H", "Days Old", 10),
    ("I", "Date Cleared", 14),
    ("J", "Remarks / Notes", 26)
]

for col_letter, text, width in headers_bills:
    c = ws_bills[f"{col_letter}6"]
    c.value = text
    c.font = HEADER_FONT
    c.fill = NAVY_HEADER
    c.alignment = Alignment(horizontal='center', vertical='center')
    c.border = THIN_BORDER
    ws_bills.column_dimensions[col_letter].width = width

dv_status = DataValidation(type="list", formula1='"Pending,Cleared,Partial"', allow_blank=False)
ws_bills.add_data_validation(dv_status)

# Populate existing 17 bills
row_b = 7
for idx, b in enumerate(sorted(signed_bills_data, key=lambda x: x.get('daysAgo', 0)), start=1):
    ws_bills[f"A{row_b}"] = idx
    ws_bills[f"B{row_b}"] = b.get('billNo')
    ws_bills[f"C{row_b}"] = b.get('invoiceNo')
    ws_bills[f"D{row_b}"] = b.get('buyerFirmName')
    ws_bills[f"E{row_b}"] = b.get('beatName')
    ws_bills[f"F{row_b}"] = b.get('amount')
    ws_bills[f"F{row_b}"].number_format = '₹#,##0.00'
    ws_bills[f"G{row_b}"] = "Pending"
    dv_status.add(ws_bills[f"G{row_b}"])
    
    ws_bills[f"H{row_b}"] = b.get('daysAgo')
    ws_bills[f"I{row_b}"] = ""
    ws_bills[f"J{row_b}"] = f"Delivered on {b.get('date')} - Market Udhaar"

    for col_letter, _, _ in headers_bills:
        cell = ws_bills[f"{col_letter}{row_b}"]
        cell.font = REG_FONT
        cell.border = THIN_BORDER
        if col_letter in ['A', 'B', 'C', 'G', 'H', 'I']:
            cell.alignment = Alignment(horizontal='center')
        elif col_letter == 'F':
            cell.alignment = Alignment(horizontal='right')
            cell.font = NUM_BOLD

    if b.get('daysAgo', 0) > 30:
        ws_bills[f"G{row_b}"].fill = ALERT_FILL
    row_b += 1

# Blank rows for new bills up to row 45
for extra_idx in range(row_b, 46):
    ws_bills[f"A{extra_idx}"] = extra_idx - 6
    ws_bills[f"G{extra_idx}"] = "Pending"
    dv_status.add(ws_bills[f"G{extra_idx}"])
    ws_bills[f"F{extra_idx}"] = 0
    ws_bills[f"F{extra_idx}"].number_format = '₹#,##0.00'
    for col_letter, _, _ in headers_bills:
        cell = ws_bills[f"{col_letter}{extra_idx}"]
        cell.font = REG_FONT
        cell.border = THIN_BORDER

# Total Row at Row 47
ws_bills['E47'] = "TOTAL PENDING UDHAARI:"
ws_bills['E47'].font = BOLD_FONT
ws_bills['E47'].alignment = Alignment(horizontal='right')
ws_bills['F47'] = '=SUMIF(G7:G45, "Pending", F7:F45)'
ws_bills['F47'].font = BOLD_FONT
ws_bills['F47'].number_format = '₹#,##0.00'
ws_bills['F47'].fill = TOTAL_FILL
ws_bills['F47'].border = DOUBLE_BOTTOM_BORDER

# ==============================================================================
# TAB 4: 💰 LOANS & LENDING (KHAATA)
# ==============================================================================
ws_loans = wb.create_sheet('💰 Loans & Lending (Khaata)')
ws_loans.views.sheetView[0].showGridLines = True

ws_loans['A1'] = "KHAATA REGISTER - LENT MONEY, STAFF ADVANCES & BORROWINGS"
ws_loans['A1'].font = TITLE_FONT
ws_loans['A2'] = "Separate personal and business lending. Keep staff salary advances distinct from company profits."
ws_loans['A2'].font = SUB_FONT

# Top KPI Summary Cards
ws_loans['B4'] = "Total Money Lent (Advances Due):"
ws_loans['C4'] = ""
ws_loans['D4'] = "₹"
ws_loans['E4'] = "=F25"
ws_loans['E4'].font = BIG_KPI_FONT
ws_loans['E4'].number_format = '₹#,##0.00'

ws_loans['H4'] = "Total Money I Owe (Liabilities):"
ws_loans['I4'] = ""
ws_loans['J4'] = "₹"
ws_loans['K4'] = "=F45"
ws_loans['K4'].font = BIG_KPI_RED
ws_loans['K4'].number_format = '₹#,##0.00'

for c in ['B4', 'C4', 'D4', 'E4', 'H4', 'I4', 'J4', 'K4']:
    ws_loans[c].fill = CARD_BG
    ws_loans[c].border = THIN_BORDER
    if not ws_loans[c].font or ws_loans[c].font == REG_FONT:
        ws_loans[c].font = BOLD_FONT

# SECTION A: MONEY LENT (Rows 7 to 25)
ws_loans['A7'] = "SECTION A: MONEY I LENT / STAFF SALARY ADVANCES (ASSETS - TO RECEIVE)"
ws_loans.merge_cells("A7:G7")
ws_loans['A7'].font = HEADER_FONT
ws_loans['A7'].fill = NAVY_HEADER
ws_loans['A7'].alignment = Alignment(horizontal='center', vertical='center')

headers_lent = [
    ("A", "Date", 12),
    ("B", "Person / Staff Name", 24),
    ("C", "Category", 18),
    ("D", "Amount Given (₹)", 16),
    ("E", "Recovered (₹)", 16),
    ("F", "Balance Due (₹)", 16),
    ("G", "Notes / Salary Month", 26)
]

for col_letter, text, width in headers_lent:
    c = ws_loans[f"{col_letter}8"]
    c.value = text
    c.font = DARK_HEADER_FONT
    c.fill = SECTION_HEADER
    c.alignment = Alignment(horizontal='center', vertical='center')
    c.border = THIN_BORDER
    ws_loans.column_dimensions[col_letter].width = width

# Sample staff advances
sample_lent = [
    ("2026-11-02", "Ramu (Driver)", "Staff Advance", 500, 0, "Deduct in Nov Salary"),
    ("2026-11-04", "Sunil (Helper)", "Staff Advance", 300, 0, "Deduct in Nov Salary"),
    ("2026-11-06", "Mahesh (Warehouse)", "Staff Advance", 1000, 0, "Deduct in Nov Salary"),
    ("2026-10-25", "Friend / Personal", "Personal Loan", 5000, 2000, "Return by 20th Nov"),
]

for idx, (dt, person, cat, gv, rec, note) in enumerate(sample_lent, start=9):
    ws_loans[f"A{idx}"] = dt
    ws_loans[f"B{idx}"] = person
    ws_loans[f"C{idx}"] = cat
    ws_loans[f"D{idx}"] = gv
    ws_loans[f"E{idx}"] = rec
    ws_loans[f"F{idx}"] = f"=D{idx}-E{idx}"
    ws_loans[f"G{idx}"] = note
    for col_letter, _, _ in headers_lent:
        cell = ws_loans[f"{col_letter}{idx}"]
        cell.font = REG_FONT
        cell.border = THIN_BORDER
        if col_letter in ['D', 'E', 'F']:
            cell.number_format = '₹#,##0.00'
            cell.alignment = Alignment(horizontal='right')
        elif col_letter == 'A':
            cell.alignment = Alignment(horizontal='center')

# Empty rows up to 24
for idx in range(9 + len(sample_lent), 25):
    ws_loans[f"D{idx}"] = 0
    ws_loans[f"E{idx}"] = 0
    ws_loans[f"F{idx}"] = f"=D{idx}-E{idx}"
    for col_letter, _, _ in headers_lent:
        cell = ws_loans[f"{col_letter}{idx}"]
        cell.font = REG_FONT
        cell.border = THIN_BORDER
        if col_letter in ['D', 'E', 'F']:
            cell.number_format = '₹#,##0.00'

# Total Lent Row 25
ws_loans['C25'] = "TOTAL ADVANCES DUE:"
ws_loans['C25'].font = BOLD_FONT
ws_loans['C25'].alignment = Alignment(horizontal='right')
ws_loans['F25'] = "=SUM(F9:F24)"
ws_loans['F25'].font = BOLD_FONT
ws_loans['F25'].number_format = '₹#,##0.00'
ws_loans['F25'].fill = TOTAL_FILL

# SECTION B: MONEY I OWE (Rows 28 to 45)
ws_loans['A28'] = "SECTION B: MONEY I OWE / BORROWINGS (LIABILITIES - TO PAY BACK)"
ws_loans.merge_cells("A28:G28")
ws_loans['A28'].font = HEADER_FONT
ws_loans['A28'].fill = STEEL_HEADER
ws_loans['A28'].alignment = Alignment(horizontal='center', vertical='center')

for col_letter, text, _ in headers_lent:
    c = ws_loans[f"{col_letter}29"]
    # Change headers for section B
    if col_letter == 'B': text = "Creditor / Bank / Person"
    elif col_letter == 'C': text = "Loan Type"
    elif col_letter == 'D': text = "Principal Borrowed (₹)"
    elif col_letter == 'E': text = "Repaid So Far (₹)"
    elif col_letter == 'F': text = "Balance Owed (₹)"
    elif col_letter == 'G': text = "EMI / Due Date / Terms"
    c.value = text
    c.font = DARK_HEADER_FONT
    c.fill = SECTION_HEADER
    c.alignment = Alignment(horizontal='center', vertical='center')
    c.border = THIN_BORDER

sample_owed = [
    ("2026-04-01", "Vehicle Loan (Delivery Van)", "Bank EMI", 350000, 120000, "EMI ₹11,500/month"),
    ("2026-08-15", "Market Emergency Credit", "Short-term Borrowing", 50000, 20000, "Repay by Dec 2026"),
]

for idx, (dt, person, cat, gv, rec, note) in enumerate(sample_owed, start=30):
    ws_loans[f"A{idx}"] = dt
    ws_loans[f"B{idx}"] = person
    ws_loans[f"C{idx}"] = cat
    ws_loans[f"D{idx}"] = gv
    ws_loans[f"E{idx}"] = rec
    ws_loans[f"F{idx}"] = f"=D{idx}-E{idx}"
    ws_loans[f"G{idx}"] = note
    for col_letter, _, _ in headers_lent:
        cell = ws_loans[f"{col_letter}{idx}"]
        cell.font = REG_FONT
        cell.border = THIN_BORDER
        if col_letter in ['D', 'E', 'F']:
            cell.number_format = '₹#,##0.00'
            cell.alignment = Alignment(horizontal='right')
        elif col_letter == 'A':
            cell.alignment = Alignment(horizontal='center')

for idx in range(30 + len(sample_owed), 45):
    ws_loans[f"D{idx}"] = 0
    ws_loans[f"E{idx}"] = 0
    ws_loans[f"F{idx}"] = f"=D{idx}-E{idx}"
    for col_letter, _, _ in headers_lent:
        cell = ws_loans[f"{col_letter}{idx}"]
        cell.font = REG_FONT
        cell.border = THIN_BORDER
        if col_letter in ['D', 'E', 'F']:
            cell.number_format = '₹#,##0.00'

# Total Owed Row 45
ws_loans['C45'] = "TOTAL LIABILITIES OWED:"
ws_loans['C45'].font = BOLD_FONT
ws_loans['C45'].alignment = Alignment(horizontal='right')
ws_loans['F45'] = "=SUM(F30:F44)"
ws_loans['F45'].font = BOLD_FONT
ws_loans['F45'].number_format = '₹#,##0.00'
ws_loans['F45'].fill = TOTAL_FILL

# ==============================================================================
# TAB 5: ⚡ FIXED COSTS & SETUP
# ==============================================================================
ws_fixed = wb.create_sheet('⚡ Fixed Costs & Setup')
ws_fixed.views.sheetView[0].showGridLines = True

ws_fixed['A1'] = "GODOWN FIXED OVERHEADS & SYSTEM CONFIGURATION"
ws_fixed['A1'].font = TITLE_FONT
ws_fixed['A2'] = "Monthly fixed expenses are divided by 30 days to compute daily operating cost for realistic P&L."
ws_fixed['A2'].font = SUB_FONT

ws_fixed['B4'] = "MONTHLY FIXED OVERHEADS"
ws_fixed.merge_cells("B4:C4")
ws_fixed['B4'].font = HEADER_FONT
ws_fixed['B4'].fill = NAVY_HEADER
ws_fixed['B4'].alignment = Alignment(horizontal='center', vertical='center')

fixed_items = [
    ("Monthly Godown Electricity Bill (₹):", 8000),
    ("Monthly Godown Rent (₹):", 15000),
    ("Monthly Vehicle EMI & Insurance (₹):", 12000),
    ("Monthly Fixed Warehouse Staff Salaries (₹):", 20000),
]

for idx, (lbl, val) in enumerate(fixed_items, start=5):
    ws_fixed[f"B{idx}"] = lbl
    ws_fixed[f"B{idx}"].font = REG_FONT
    ws_fixed[f"B{idx}"].border = THIN_BORDER
    
    ws_fixed[f"C{idx}"] = val
    ws_fixed[f"C{idx}"].font = BOLD_FONT
    ws_fixed[f"C{idx}"].border = THIN_BORDER
    ws_fixed[f"C{idx}"].number_format = '₹#,##0.00'
    ws_fixed[f"C{idx}"].alignment = Alignment(horizontal='right')

# Total Monthly Fixed Overheads
ws_fixed['B9'] = "TOTAL MONTHLY FIXED OVERHEADS:"
ws_fixed['B9'].font = BOLD_FONT
ws_fixed['B9'].border = THIN_BORDER
ws_fixed['C9'] = "=SUM(C5:C8)"
ws_fixed['C9'].font = BOLD_FONT
ws_fixed['C9'].number_format = '₹#,##0.00'
ws_fixed['C9'].alignment = Alignment(horizontal='right')
ws_fixed['B9'].fill = TOTAL_FILL
ws_fixed['C9'].fill = TOTAL_FILL

# Daily Fixed Allocation
ws_fixed['B10'] = "DAILY OVERHEAD ALLOCATION (DIVIDED BY 30 DAYS):"
ws_fixed['B10'].font = BOLD_FONT
ws_fixed['B10'].border = THIN_BORDER
ws_fixed['C10'] = "=ROUND(C9/30, 2)"
ws_fixed['C10'].font = BIG_KPI_FONT
ws_fixed['C10'].number_format = '₹#,##0.00'
ws_fixed['C10'].alignment = Alignment(horizontal='right')
ws_fixed['B10'].fill = SECTION_HEADER
ws_fixed['C10'].fill = SECTION_HEADER

# Starting Market Udhaari
ws_fixed['B12'] = "OPENING MARKET UDHAARI BALANCE (01-NOV-2026):"
ws_fixed['B12'].font = BOLD_FONT
ws_fixed['B12'].border = THIN_BORDER
ws_fixed['C12'] = 82612.05  # Starting value from the 17 signed bills
ws_fixed['C12'].font = BIG_KPI_RED
ws_fixed['C12'].number_format = '₹#,##0.00'
ws_fixed['C12'].alignment = Alignment(horizontal='right')
ws_fixed['B12'].fill = ALERT_FILL
ws_fixed['C12'].fill = ALERT_FILL

ws_fixed.column_dimensions['A'].width = 4
ws_fixed.column_dimensions['B'].width = 48
ws_fixed.column_dimensions['C'].width = 24

# Save workbook
out_file = 'C:/Users/fixadmin/TALLY/Haldiram/HALDIRAM_DAILY_PNL_AND_OPERATIONS.xlsx'
wb.save(out_file)
print(f"🎉 Successfully built: {out_file}")
