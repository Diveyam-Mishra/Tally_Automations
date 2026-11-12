import os
import sys
import json
import glob
import paramiko
import requests
import xml.etree.ElementTree as ET

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except:
        pass

target_bills = ['13088', '13077', '12719', '12970', '12948', '12963', '12972', '12935', '12700', '12778', '12790', '12751', '12565', '12566', '10111', '10734', '3657']
target_set = set(target_bills)

found_invoices = {}

# 1. Search local JSON files
for path in glob.glob('C:/Users/fixadmin/TALLY/Haldiram/**/*.json', recursive=True):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if isinstance(data, dict):
                data = list(data.values())
            if isinstance(data, list):
                for item in data:
                    if isinstance(item, dict):
                        inv_no = str(item.get('invoiceNo', ''))
                        for b in target_set:
                            if b in inv_no:
                                found_invoices[b] = item
    except Exception as e:
        pass

print(f"Found {len(found_invoices)} in local JSON files.")

# 2. Search remote JSON files via SFTP
try:
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect('100.103.81.73', port=22, username='ayush', password='Agni@1222', timeout=15)
    sftp = ssh.open_sftp()
    remote_dir = 'C:/Users/ayush/Tally/invoices'
    try:
        remote_files = sftp.listdir(remote_dir)
        for f in remote_files:
            if f.endswith('.json'):
                with sftp.open(f"{remote_dir}/{f}") as rfile:
                    try:
                        data = json.load(rfile)
                        if isinstance(data, list):
                            for item in data:
                                if isinstance(item, dict):
                                    inv_no = str(item.get('invoiceNo', ''))
                                    for b in target_set:
                                        if b in inv_no and b not in found_invoices:
                                            found_invoices[b] = item
                    except:
                        pass
    except Exception as e:
        print("Remote invoice dir read error:", e)
    sftp.close()
    ssh.close()
except Exception as e:
    print("SSH connection error:", e)

print(f"Found {len(found_invoices)} in local + remote JSON files.")

# 3. Check Tally on 100.103.81.73:9000 for any missing vouchers
# Query vouchers from Tally
tally_url = "http://100.103.81.73:9000/"
xml_req = """<ENVELOPE>
  <HEADER>
    <VERSION>1</VERSION>
    <TALLYREQUEST>Export</TALLYREQUEST>
    <TYPE>Collection</TYPE>
    <ID>AllVouchers</ID>
  </HEADER>
  <BODY>
    <DESC>
      <STATICVARIABLES>
        <SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>
        <SVCURRENTCOMPANY>ANAND MANGAL_FY26-27</SVCURRENTCOMPANY>
      </STATICVARIABLES>
      <TDL>
        <TDLMESSAGE>
          <COLLECTION NAME="AllVouchers">
            <TYPE>Voucher</TYPE>
            <FETCH>DATE,VOUCHERTYPENAME,VOUCHERNUMBER,PARTYLEDGERNAME,AMOUNT,REFERENCE</FETCH>
          </COLLECTION>
        </TDLMESSAGE>
      </TDL>
    </DESC>
  </BODY>
</ENVELOPE>"""

tally_vouchers = {}
try:
    resp = requests.post(tally_url, data=xml_req.encode('utf-8'), headers={'Content-Type': 'application/xml'}, timeout=30)
    if resp.status_code == 200:
        root = ET.fromstring(resp.text)
        for v in root.findall('.//VOUCHER'):
            vnum = v.findtext('VOUCHERNUMBER', '')
            ref = v.findtext('REFERENCE', '')
            date = v.findtext('DATE', '')
            party = v.findtext('PARTYLEDGERNAME', '')
            amt = v.findtext('AMOUNT', '0')
            for b in target_set:
                if b in vnum or b in ref:
                    tally_vouchers[b] = {
                        'voucherNumber': vnum,
                        'reference': ref,
                        'date': date,
                        'party': party,
                        'amount': abs(float(amt)) if amt else 0.0
                    }
except Exception as e:
    print("Tally query error:", e)

print(f"Found {len(tally_vouchers)} matching in Tally directly.\n")

print("=" * 80)
print(f"{'BILL NO':<8} | {'STATUS':<10} | {'RETAILER / PARTY':<32} | {'AMOUNT (₹)':<12} | {'DATE':<10}")
print("=" * 80)

total_owed = 0.0
for b in target_bills:
    if b in found_invoices:
        inv = found_invoices[b]
        buyer = inv.get('buyerFirmName', 'N/A')
        # calculate invoice amount if total not present
        amt = inv.get('netAmount') or inv.get('totalAmount') or inv.get('invoiceAmount')
        if amt is None and 'orderItems' in inv:
            amt = sum(float(item.get('totalValue', 0)) for item in inv['orderItems'])
        elif amt is None and 'items' in inv:
            amt = sum(float(item.get('totalValue', 0)) for item in inv['items'])
        amt = float(amt or 0)
        dt = (inv.get('invoiceDate') or inv.get('createdAt') or '')[:10]
        total_owed += amt
        print(f"{b:<8} | {'JSON/Portal':<10} | {buyer[:32]:<32} | ₹{amt:>10.2f} | {dt}")
    elif b in tally_vouchers:
        tv = tally_vouchers[b]
        buyer = tv['party']
        amt = tv['amount']
        dt = tv['date']
        total_owed += amt
        print(f"{b:<8} | {'In Tally':<10} | {buyer[:32]:<32} | ₹{amt:>10.2f} | {dt}")
    else:
        print(f"{b:<8} | {'NOT FOUND':<10} | {'Need lookup / FieldAssist':<32} | {'-':>11} | -")

print("=" * 80)
print(f"TOTAL AMOUNT OWED ACROSS FOUND BILLS: ₹{total_owed:,.2f}")
print("=" * 80)
