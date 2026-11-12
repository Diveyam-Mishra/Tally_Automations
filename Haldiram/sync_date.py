import sys
import os
import subprocess
import glob
from datetime import datetime, timedelta

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except:
        pass

def sync_single_date(date_str, limit=500, tally_ip="100.103.81.73", tally_port="9000"):
    print(f"\n=============================================================")
    print(f"🚀 HALDIRAM DMS -> TALLY SYNC FOR {date_str}")
    print(f"=============================================================\n")

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

    # STAGE 2: Import into Tally (with automatic deduplication check)
    print(f"\n[Stage 2/2] Importing invoices from {json_path} into Tally...")
    import_cmd = ["python", "import_sales_to_tally.py", "--json", json_path, "--tally-ip", tally_ip, "--tally-port", tally_port]
    res2 = subprocess.run(import_cmd)
    if res2.returncode != 0:
        print(f"❌ Stage 2 (Tally Import) encountered an error on {date_str}.")
        return False

    print(f"\n🎉 SYNC COMPLETED SUCCESSFULLY FOR {date_str}!\n")
    return True

def parse_date(d_str):
    return datetime.strptime(d_str, "%d-%m-%Y")

def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  Single Date: python sync_date.py <DD-MM-YYYY>")
        print("  Date Range : python sync_date.py <START_DATE> <END_DATE>")
        print("Example:")
        print("  python sync_date.py 03-10-2026 10-10-2026")
        sys.exit(1)

    arg1 = sys.argv[1]
    arg2 = sys.argv[2] if len(sys.argv) > 2 else None

    # Check if arg2 is a date or a number (limit)
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

        print(f"📅 Running sync for {len(dates)} days: {dates[0]} to {dates[-1]}")
        for idx, d_str in enumerate(dates, 1):
            print(f"\n[{idx}/{len(dates)}] Processing {d_str}...")
            ok = sync_single_date(d_str)
            if not ok:
                print(f"❌ STOPPING range run due to failure on {d_str}!")
                sys.exit(1)

        print(f"\n=============================================================")
        print(f"🎉 COMPLETED ALL {len(dates)} DAYS ({dates[0]} to {dates[-1]})!")
        print(f"=============================================================")
    else:
        limit = int(arg2) if arg2 and arg2.isdigit() else 500
        ok = sync_single_date(arg1, limit)
        sys.exit(0 if ok else 1)

if __name__ == "__main__":
    main()
