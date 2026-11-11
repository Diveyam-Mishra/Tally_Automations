import requests
import xml.etree.ElementTree as ET

# Query vouchers matching 2735
query_xml = """<ENVELOPE>
  <HEADER>
    <VERSION>1</VERSION>
    <TALLYREQUEST>Export</TALLYREQUEST>
    <TYPE>Collection</TYPE>
    <ID>VoucherColl</ID>
  </HEADER>
  <BODY>
    <DESC>
      <STATICVARIABLES>
        <SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>
      </STATICVARIABLES>
      <TDL>
        <TDLMESSAGE>
          <COLLECTION NAME="VoucherColl">
            <TYPE>Voucher</TYPE>
            <FILTER>VchFilter</FILTER>
            <FETCH>*,AllInventoryEntries.*,LedgerEntries.*</FETCH>
          </COLLECTION>
          <SYSTEM TYPE="Formulae" NAME="VchFilter">$VoucherNumber contains "2735" or $Reference contains "2735"</SYSTEM>
        </TDLMESSAGE>
      </TDL>
    </DESC>
  </BODY>
</ENVELOPE>"""

try:
    r = requests.post('http://localhost:9000/', data=query_xml.encode('utf-8'), headers={'Content-Type': 'application/xml'}, timeout=15)
    print("Status:", r.status_code)
    with open('voucher_2735_raw.xml', 'w', encoding='utf-8') as f:
        f.write(r.text)
    print("Saved voucher_2735_raw.xml, length:", len(r.text))
except Exception as e:
    print("Error:", e)
