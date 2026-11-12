import sys
import os
import subprocess
import glob
import json
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
    print("🚀 Opening Chrome browser now for login...")
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

def sync_single_date(date_str, limit=500, tally_ip="100.103.81.73", tally_port="9000"):
    print(f"\n=============================================================")
    print(f"🚀 HALDIRAM DMS -> TALLY SALES SYNC FOR {date_str}")
    print(f"=============================================================\n")

    # PRE-FLIGHT CHECK: Verify Auth
    if not ensure_valid_auth("auth.json"):
        return False

    # STAGE 1: Fetch invoices from FieldAssist DMS
    print(f"[Stage 1/2] Fetching invoices from FieldAssist DMS for {date_str}...")
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
    print(f"\n[Stage 2/2] Importing sales vouchers from {json_path} into Tally...")
    import_cmd = ["python", "import_sales_to_tally.py", "--json", json_path, "--tally-ip", tally_ip, "--tally-port", tally_port]
    res2 = subprocess.run(import_cmd)
    if res2.returncode != 0:
        print(f"❌ Stage 2 (Tally Import) encountered an error on {date_str}.")
        return False

    print(f"\n=============================================================")
    print(f"🎉 SALES SYNC COMPLETED SUCCESSFULLY FOR {date_str}!")
    print(f"=============================================================\n")
    return True

def parse_date(d_str):
    return datetime.strptime(d_str, "%d-%m-%Y")

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Haldiram FieldAssist to Tally Sales Sync (Sales Vouchers Only)")
    parser.add_argument("date1", help="Target date (DD-MM-YYYY) or start date of range")
    parser.add_argument("date2", nargs="?", default=None, help="End date of range (optional) or invoice limit")
    parser.add_argument("--tally-ip", default="100.103.81.73", help="Tally server IP")
    parser.add_argument("--tally-port", default="9000", help="Tally server port")

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

        print(f"📅 Running sales sync for {len(dates)} days: {dates[0]} to {dates[-1]}")
        for idx, d_str in enumerate(dates, 1):
            print(f"\n[{idx}/{len(dates)}] Processing {d_str}...")
            ok = sync_single_date(d_str, tally_ip=args.tally_ip, tally_port=args.tally_port)
            if not ok:
                print(f"❌ STOPPING range run due to failure on {d_str}!")
                sys.exit(1)

        print(f"\n=============================================================")
        print(f"🎉 COMPLETED ALL {len(dates)} DAYS ({dates[0]} to {dates[-1]})!")
        print(f"=============================================================")
    else:
        limit = int(arg2) if arg2 and arg2.isdigit() else 500
        ok = sync_single_date(arg1, limit=limit, tally_ip=args.tally_ip, tally_port=args.tally_port)
        sys.exit(0 if ok else 1)

if __name__ == "__main__":
    main()
