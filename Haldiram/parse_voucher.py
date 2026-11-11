import re
import xml.etree.ElementTree as ET

with open('voucher_2735_raw.xml', 'r', encoding='utf-8', errors='ignore') as f:
    content = f.read()

content_clean = re.sub(r'&#(?:[0-8]|1[1-2]|1[4-9]|2[0-9]|3[0-1]);', '', content)
root = ET.fromstring(content_clean)

for v in root.findall('.//VOUCHER'):
    if v.findtext('VOUCHERNUMBER') == 'AM/S/26-27/2735':
        print("VOUCHER NUMBER:", v.findtext('VOUCHERNUMBER'))
        print("DATE:", v.findtext('DATE'))
        print("PARTY:", v.findtext('PARTYLEDGERNAME'))
        print("PARTY MAILING NAME:", v.findtext('PARTYMAILINGNAME'))
        print("PARTY ADDRESS:", [a.text for a in v.findall('.//BASICBUYERADDRESS.LIST/BASICBUYERADDRESS')])
        print("GSTIN:", v.findtext('PARTYGSTIN'))
        print("STATE:", v.findtext('STATENAME'))
        print("PLACE OF SUPPLY:", v.findtext('PLACEOFSUPPLY'))
        
        print("\n--- INVENTORY ENTRIES ---")
        for item in v.findall('.//ALLINVENTORYENTRIES.LIST'):
            name = item.findtext('STOCKITEMNAME')
            qty = item.findtext('ACTUALQTY') or item.findtext('BILLEDQTY')
            rate = item.findtext('RATE')
            amount = item.findtext('AMOUNT')
            discount = item.findtext('DISCOUNT')
            hsn = item.findtext('.//GSTHSNNAME') or item.findtext('GSTHSNNAME')
            print(f"Item: {name} | Qty: {qty} | Rate: {rate} | Disc: {discount} | Amount: {amount}")
            for b in item.findall('.//BATCHALLOCATIONS.LIST'):
                print(f"   Batch: {b.findtext('BATCHNAME')} | Qty: {b.findtext('ACTUALQTY')} | Amount: {b.findtext('AMOUNT')}")
                
        print("\n--- LEDGER ENTRIES ---")
        for led in v.findall('.//LEDGERENTRIES.LIST'):
            lname = led.findtext('LEDGERNAME')
            lamt = led.findtext('AMOUNT')
            print(f"Ledger: {lname} | Amount: {lamt}")
