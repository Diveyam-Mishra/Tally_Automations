import zipfile
import xml.etree.ElementTree as ET

path = r'C:\Users\Ayush\Desktop\Sales_AM_S_26-27_1006 jimmi sales data.xlsx'
with zipfile.ZipFile(path, 'r') as z:
    # get shared strings
    shared_strings = []
    if 'xl/sharedStrings.xml' in z.namelist():
        sst_root = ET.fromstring(z.read('xl/sharedStrings.xml'))
        for si in sst_root:
            text = "".join([t.text for t in si.findall('.//{*}t') if t.text])
            shared_strings.append(text)
            
    # read sheet1
    sheet_root = ET.fromstring(z.read('xl/worksheets/sheet1.xml'))
    rows = sheet_root.findall('.//{*}row')
    for r in rows[:30]:
        row_num = r.attrib.get('r')
        cols = []
        for c in r.findall('{*}c'):
            t = c.attrib.get('t')
            v = c.findtext('{*}v')
            val = ""
            if t == 's' and v is not None:
                val = shared_strings[int(v)]
            elif v is not None:
                val = v
            cols.append(val)
        print(f"Row {row_num}: {cols}")
