import json
import re
import xml.etree.ElementTree as ET

with open('voucher_2735_raw.xml', 'r', encoding='utf-8', errors='ignore') as f:
    content = f.read()

content_clean = re.sub(r'&#(?:[0-8]|1[1-2]|1[4-9]|2[0-9]|3[0-1]);', '', content)
root = ET.fromstring(content_clean)

vch = None
for v in root.findall('.//VOUCHER'):
    if v.findtext('VOUCHERNUMBER') == 'AM/S/26-27/2735':
        vch = v
        break

if not vch:
    print("Voucher not found!")
    exit(1)

inv_data = {
    "voucher_number": vch.findtext('VOUCHERNUMBER'),
    "voucher_type": vch.findtext('VOUCHERTYPENAME'),
    "date": vch.findtext('DATE'),
    "party_ledger": vch.findtext('PARTYLEDGERNAME'),
    "party_name": vch.findtext('PARTYNAME'),
    "party_mailing_name": vch.findtext('PARTYMAILINGNAME'),
    "party_address": [a.text for a in vch.findall('.//BASICBUYERADDRESS.LIST/BASICBUYERADDRESS') if a.text],
    "party_gstin": vch.findtext('PARTYGSTIN'),
    "place_of_supply": vch.findtext('PLACEOFSUPPLY'),
    "state_name": vch.findtext('STATENAME'),
    "pincode": vch.findtext('PARTYPINCODE'),
    "cmp_gstin": vch.findtext('CMPGSTIN'),
    "cmp_state": vch.findtext('CMPGSTSTATE'),
    "items": [],
    "ledgers": []
}

for item in vch.findall('.//ALLINVENTORYENTRIES.LIST'):
    item_info = {
        "name": item.findtext('STOCKITEMNAME'),
        "billed_qty": item.findtext('BILLEDQTY'),
        "actual_qty": item.findtext('ACTUALQTY'),
        "rate": item.findtext('RATE'),
        "amount": item.findtext('AMOUNT'),
        "discount": item.findtext('DISCOUNT'),
        "hsn": item.findtext('.//GSTHSNNAME') or item.findtext('GSTHSNNAME') or '',
    }
    inv_data["items"].append(item_info)

for led in vch.findall('.//LEDGERENTRIES.LIST'):
    led_info = {
        "name": led.findtext('LEDGERNAME'),
        "amount": led.findtext('AMOUNT')
    }
    inv_data["ledgers"].append(led_info)

with open('voucher_details.json', 'w', encoding='utf-8') as f:
    json.dump(inv_data, f, indent=2)

print(f"Dumped voucher details. Total items: {len(inv_data['items'])}, Total ledgers: {len(inv_data['ledgers'])}")
