import requests
import re

xml = """<ENVELOPE>
  <HEADER>
    <VERSION>1</VERSION>
    <TALLYREQUEST>Export</TALLYREQUEST>
    <TYPE>Collection</TYPE>
    <ID>CompanyColl</ID>
  </HEADER>
  <BODY>
    <DESC>
      <STATICVARIABLES>
        <SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>
      </STATICVARIABLES>
      <TDL>
        <TDLMESSAGE>
          <COLLECTION NAME="CompanyColl">
            <TYPE>Company</TYPE>
            <FETCH>Name</FETCH>
          </COLLECTION>
        </TDLMESSAGE>
      </TDL>
    </DESC>
  </BODY>
</ENVELOPE>"""

try:
    r = requests.post('http://localhost:9000/', data=xml.encode('utf-8'), headers={'Content-Type': 'application/xml'}, timeout=5)
    names = re.findall(r'<NAME[^>]*>([^<]+)</NAME>', r.text)
    print('Status:', r.status_code)
    print(f'Total Companies loaded in Tally: {len(names)}')
    for n in names:
        print('  *', n)
    if not names:
        print('Raw text:\n', r.text[:600])
except Exception as e:
    print('Error:', e)
