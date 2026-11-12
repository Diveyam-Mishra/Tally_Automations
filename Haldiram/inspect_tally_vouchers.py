import requests
import re

url = "http://100.103.81.73:9000/"
xml_request = """<ENVELOPE>
  <HEADER>
    <VERSION>1</VERSION>
    <TALLYREQUEST>Export</TALLYREQUEST>
    <TYPE>Collection</TYPE>
    <ID>AllRefsColl</ID>
  </HEADER>
  <BODY>
    <DESC>
      <STATICVARIABLES>
        <SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>
        <SVCURRENTCOMPANY>ANAND MANGAL_FY26-27</SVCURRENTCOMPANY>
      </STATICVARIABLES>
      <TDL>
        <TDLMESSAGE>
          <COLLECTION NAME="AllRefsColl">
            <TYPE>Voucher</TYPE>
            <FETCH>VOUCHERNUMBER,REFERENCE</FETCH>
          </COLLECTION>
        </TDLMESSAGE>
      </TDL>
    </DESC>
  </BODY>
</ENVELOPE>"""

try:
    resp = requests.post(url, data=xml_request.encode('utf-8'), headers={'Content-Type': 'application/xml; charset=utf-8'}, timeout=40)
    print("Status code:", resp.status_code)
    if resp.status_code == 200:
        refs = re.findall(r'<REFERENCE[^>]*>([^<]+)</REFERENCE>', resp.text)
        vchs = re.findall(r'<VOUCHERNUMBER[^>]*>([^<]+)</VOUCHERNUMBER>', resp.text)
        print(f"Total References found in Tally: {len(refs)}")
        print(f"Total Voucher Numbers found in Tally: {len(vchs)}")
        print("Sample References:", refs[:10])
        print("Sample Voucher Numbers:", vchs[:10])
except Exception as e:
    print("Error:", e)
