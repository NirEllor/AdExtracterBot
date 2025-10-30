from openpyxl import load_workbook
import re

def extract(urls, creative_id_set):
    excel_path = "booking_com_2024_1696090.xlsx"
    sheet_name = "Report"
    wb = load_workbook(excel_path)
    ws = wb[sheet_name]

    pattern = r'=HYPERLINK\("([^"]+)"'

    for url, creative_id in zip(ws['A'], ws['B']):
        if url.row == 1:  # Headers
            continue
        value = str(url.value)
        match = re.search(pattern, value)
        if match and creative_id.value not in creative_id_set:
            creative_id_set.add(creative_id.value)
            urls[creative_id] = match.group(1)

if __name__ == '__main__':
    pass
