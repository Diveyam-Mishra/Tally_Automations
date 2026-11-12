import sys
import os
import subprocess
import glob
import json
import re
from datetime import datetime, timedelta
import requests

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except:
        pass

def check_auth_valid(auth_path="auth.json"):
    if not os.path.exists(auth_path):
        return False
    try:
        with open(auth_path, 'r', encoding='utf-8') as f:
            auth_data = json.load(f)
        cookies = {c['name']: c['value'] for c in auth_data.get('cookies', [])}
        headers = {'User-Agent': 'Mozilla/5.0', 'Accept': 'application/json, text/plain, */*'}
        resp = requests.get('https://dms-hsfpl.fieldassist.io/api/v1/user/profile', cookies=cookies, headers=headers, timeout=8)
        return resp.status_code == 200
    except:
        return False

def ensure_valid_auth(auth_path="auth.json"):
    print("🔑 Checking FieldAssist authentication session...")
    if check_auth_valid(auth_path):
        print("✅ FieldAssist session is active and valid!\n")
        return True

    print("\n" + "=" * 65)
    print("⚠️ FieldAssist login session is EXPIRED or MISSING!")
    print("🚀 Opening Chrome browser now for one-time login...")
    print("👉 Please log in to FieldAssist in the opened Chrome window.")
    print("👉 Once you reach the dashboard, your session will save automatically!")
    print("=" * 65 + "\n")

    res = subprocess.run(["node", "save_login.js"])
    if res.returncode == 0 and check_auth_valid(auth_path):
        print("🎉 Login successful! Resuming sync now...\n")
        return True
    else:
        print("❌ Login was not completed or failed. Cannot proceed with sync.")
        return False

def generate_receipts_for_date(date_str, json_path, tally_ip="100.103.81.73", tally_port="9000", company="ANAND MANGAL_FY26-27"):
    """
    Stage 3: Generates Receipt Vouchers for all bills of this date
    EXCEPT those listed in SIGNED_BILLS_INPUT.xlsx.
    """
    print(f"\n[Stage 3/3] Generating Payment Receipts for {date_str} (Excluding Signed Bills)...")
    
    excel_path = "SIGNED_BILLS_INPUT.xlsx"
    if not os.path.exists(excel_path):
        print(f"⚠️ {excel_path} not found. Skipping receipts.")
        return True

    # Parse date to YYYY-MM-DD
    try:
        parts = date_str.split('-')
        d_iso = f"{parts[2]}-{parts[1]}-{parts[0]}"
    except:
        d_iso = date_str

    cmd = [
        "python", "generate_receipts_for_paid_bills.py",
        "--from-date", d_iso,
        "--to-date", d_iso,
        "--excel", excel_path,
        "--tally-ip", tally_ip,
        "--tally-port", tally_port,
        "--company", company,
        "--post"
    ]
    res = subprocess.run(cmd)
    if res.returncode == 0:
        print(f"✅ Stage 3 complete! Receipts created in Tally for {date_str}.")
        return True
    else:
        print(f"⚠️ Stage 3 had an issue creating receipts.")
        return False

def sync_single_date(date_str, limit=500, tally_ip="100.103.81.73", tally_port="9000", do_receipts=True):
    print(f"\n=============================================================")
    print(f"🚀 HALDIRAM DMS -> TALLY AUTO-SYNC PIPELINE FOR {date_str}")
    print(f"=============================================================\n")

    # PRE-FLIGHT CHECK: Verify Auth
    if not ensure_valid_auth("auth.json"):
        return False

    # STAGE 1: Fetch invoices from FieldAssist DMS
    print(f"[Stage 1/3] Fetching invoices from FieldAssist DMS for {date_str}...")
    fetch_cmd = ["node", "fetch_haldiram_invoices.js", date_str, str(limit)]
    res = subprocess.run(fetch_cmd)
    if res.returncode != 0:
        print(f"❌ Stage 1 (Fetcher) failed for {date_str} with code {res.returncode}")
        return False

    # Locate generated JSON file in invoices/
    json_path = os.path.join("invoices", f"invoices_{date_str}.json")
    if not os.path.exists(json_path):
        matches = glob.glob(os.path.join("invoices", f"invoices_{date_str}*.json"))
        if matches:
            json_path = sorted(matches, key=os.path.getmtime, reverse=True)[0]
        else:
            print(f"❌ Could not find output file for {date_str} in invoices/")
            return False

    print(f"✅ Stage 1 complete! Saved to: {json_path}")

    # STAGE 2: Import Sales Invoices into Tally (with automatic deduplication)
    print(f"\n[Stage 2/3] Importing sales vouchers from {json_path} into Tally...")
    import_cmd = ["python", "import_sales_to_tally.py", "--json", json_path, "--tally-ip", tally_ip, "--tally-port", tally_port]
    res2 = subprocess.run(import_cmd)
    if res2.returncode != 0:
        print(f"❌ Stage 2 (Tally Import) encountered an error on {date_str}.")
        return False

    print(f"✅ Stage 2 complete! Sales vouchers synchronized.")

    # STAGE 3: Receipt Generation for Cleared Bills
    if do_receipts:
        generate_receipts_for_date(date_str, json_path, tally_ip=tally_ip, tally_port=tally_port)

    print(f"\n=============================================================")
    print(f"🎉 FULL SYNC (SALES + RECEIPTS) COMPLETED FOR {date_str}!")
    print(f"=============================================================\n")
    return True

def parse_date(d_str):
    return datetime.strptime(d_str, "%d-%m-%Y")

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Haldiram FieldAssist to Tally Full Sync Pipeline")
    parser.add_argument("date1", help="Target date (DD-MM-YYYY) or start date of range")
    parser.add_argument("date2", nargs="?", default=None, help="End date of range (optional) or invoice limit")
    parser.add_argument("--tally-ip", default="100.103.81.73", help="Tally server IP")
    parser.add_argument("--tally-port", default="9000", help="Tally server port")
    parser.add_argument("--no-receipts", action="store_true", help="Skip receipt generation stage")

    args = parser.parse_args()

    arg1 = args.date1
    arg2 = args.date2

    is_range = False
    if arg2:
        try:
            end_dt = parse_date(arg2)
            is_range = True
        except ValueError:
            is_range = False

    do_receipts = not args.no_receipts

    if is_range:
        start_dt = parse_date(arg1)
        end_dt = parse_date(arg2)
        if start_dt > end_dt:
            print("❌ Start date must be before or equal to End date.")
            sys.exit(1)

        curr = start_dt
        dates = []
        while curr <= end_dt:
            dates.append(curr.strftime("%d-%m-%Y"))
            curr += timedelta(days=1)

        print(f"📅 Running sync for {len(dates)} days: {dates[0]} to {dates[-1]}")
        for idx, d_str in enumerate(dates, 1):
            print(f"\n[{idx}/{len(dates)}] Processing {d_str}...")
            ok = sync_single_date(d_str, tally_ip=args.tally_ip, tally_port=args.tally_port, do_receipts=do_receipts)
            if not ok:
                print(f"❌ STOPPING range run due to failure on {d_str}!")
                sys.exit(1)

        print(f"\n=============================================================")
        print(f"🎉 COMPLETED ALL {len(dates)} DAYS ({dates[0]} to {dates[-1]})!")
        print(f"=============================================================")
    else:
        limit = int(arg2) if arg2 and arg2.isdigit() else 500
        ok = sync_single_date(arg1, limit=limit, tally_ip=args.tally_ip, tally_port=args.tally_port, do_receipts=do_receipts)
        sys.exit(0 if ok else 1)

if __name__ == "__main__":
    main()
