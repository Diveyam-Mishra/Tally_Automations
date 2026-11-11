# Tally Automations

Automation, integration, and operational workflows for FMCG distribution across **Haldiram** and **Cream-Bell**, synced with **TallyPrime** over Tailscale.

## Architecture

- **Primary Tally Host:** Remote machine (`herukii` @ `100.103.81.73:9000`) connected via Tailscale.
- **Company:** `ANAND MANGAL_FY26-27`
- **Tally XML / HTTP Interface:** Direct voucher/master posting and queries on port 9000.
- **Remote Terminal Execution:** SSH via `remote_exec.py` directly to the Tally host.

---

## Directory Structure

```text
├── Cream-Bell/
│   ├── import_creambell_csv.py       # Cream-Bell CSV invoice parser and Tally importer
│   ├── import_creambell_pdfs.py      # Cream-Bell PDF invoice parser
│   ├── IMPORT_CREAMBELL_BILLS.bat    # Batch runner for PDF import
│   └── IMPORT_CREAMBELL_CSV.bat      # Batch runner for CSV import
│
├── Haldiram/
│   ├── generate_delivery_reconciliation.py  # Route reconciliation and delivery sheets
│   ├── generate_reconciliation_sheet.py     # Dispatched vs collected reconciliation
│   ├── GENERATE_DELIVERY_SHEET.bat          # Daily delivery sheet runner
│   ├── import_sales_to_tally.py             # FieldAssist sales invoice importer to Tally
│   ├── fetch_haldiram_invoices.js           # Playwright scraper/fetcher for FieldAssist
│   ├── fetch_range.js                       # Multi-day range invoice fetcher
│   ├── sync_date.py                         # Single date sync orchestrator
│   ├── build_excel.py                       # Excel voucher generation utility
│   ├── dump_vch.py                          # Tally voucher dump utility
│   ├── find_voucher.py                      # Tally voucher lookup utility
│   ├── inspect_xlsx.py                      # Spreadsheet validator
│   ├── parse_voucher.py                     # XML voucher parser
│   ├── test_local_tally.py                  # Local/remote Tally connection tester
│   ├── test_xlsx_builder.py                 # Workbook generator test
│   ├── START_DAILY_SYNC.bat                 # One-click daily sync runner
│   └── TALLY_INTEGRATION_GUIDE.md           # Tally schema and configuration guide
│
├── remote_exec.py                           # SSH command runner for the remote Tally host
└── .gitignore
```

---

## Prerequisites

- Python 3.10+ (`requests`, `paramiko`)
- Node.js & Playwright (for FieldAssist scraping)
- Tailscale (authenticated to the private network)
- TallyPrime running with **ODBC/XML Server enabled on port 9000**.
