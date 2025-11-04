from openpyxl import load_workbook
import re

def extract(urls, creative_id_set, excel_path, sheet_name):
    wb = load_workbook(excel_path)
    ws = wb[sheet_name]

    pattern = r'=HYPERLINK\("([^"]+)"'
    print("len(ws['B']) is ", len(ws['B']))
    for url, creative_id in zip(ws['A'], ws['B']):
        if url.row == 1:  # Headers
            continue
        value = str(url.value)
        match = re.search(pattern, value)
        if match and creative_id.value not in creative_id_set:
            creative_id_set.add(creative_id.value)
            urls[creative_id.value] = match.group(1)
    print("len of creative_id_set is ", len(creative_id_set))


if __name__ == '__main__':
    pass
