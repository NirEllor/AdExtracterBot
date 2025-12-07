import json
import os
import time
from datetime import datetime

import pandas as pd
import requests

from browser_investigate import login_if_needed, create_driver
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


FILES_REPORTS_DETAILED = r"C:\Vivix_Media_Files\Reports_Detailed"

brands = [
    'starbucks',
]

def to_failed_filename(s: str) -> str:
    prefix = s.split("_", 1)[0]
    return prefix + "_failed_to_download.xlsx"





def create_report(brand_name: str):
    print("\n======================================")
    print(f"🚀 Starting full report creation for: {brand_name}")
    print("======================================")

    # Load payload template
    print("📄 Loading payload template...")
    with open('creatives_payload.json') as creatives_payload_file:
        payload = json.load(creatives_payload_file)

    with open("search_payload.json", "r", encoding="utf-8") as search_payload_file:
        search_payload = json.load(search_payload_file)


    # Insert brand into payload
    unique_title = f"{brand_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    payload['Title'] = unique_title
    search_payload['SearchTerm'] = brand_name

    print(f"🔍 Searching entity for brand: {brand_name}")

    # Search brand entity
    search_url = 'https://app.vivvix.com/360/KMI/IntelliDrive/ApplUI/api/Entity/EntitySearch'
    brand_search = requests.post(
        search_url,
        headers=headers,
        json=search_payload,
        verify=False
    ).content

    # Parse results
    try:
        brand_res = json.loads(brand_search.decode('utf-8'))['Results']
    except Exception as e:
        print(f"❌ Failed parsing EntitySearch results: {e}")
        return None

    print(f"   🔹 Number of search results: {len(brand_res)}")
    print("   🔍 Search results returned:")
    for key in brand_res:
        print(f"      • {key['EntityName']}  (EntityId={key['EntityId']})")

    # Look for exact match
    res = None
    for key in brand_res:
        if key['EntityName'].lower().strip() == brand_name.lower().strip():
            res = key

    if res is None:
        print(f"❌ No exact entity match found for '{brand_name}'. Skipping brand.")
        return None

    print(f"✅ Found matching entity: {res['EntityName']} (EntityId={res['EntityId']})")

    # Update payload with the found entity
    payload['BrandCentralSelections']['Entities'] = [res]
    payload['ExcludedSearchEntityItems'] = [res]

    print("\n🛠️ Starting report creation steps...")

    # Step 1: CreateReportSpec
    create_url = 'https://app.vivvix.com/360/KMI/IntelliDrive/ApplUI/api/CustomReporting/CreateReportSpec'
    print(f"➡️ Sending CreateReportSpec → {create_url}")

    create_rep = requests.post(create_url, headers=headers, verify=False, json=payload)
    print(f"   🔹 Status: {create_rep.status_code}")
    print(f"   🔹 Response: {create_rep.text[:400]}")

    # Step 2: UpdateReportSpec
    update_url = 'https://app.vivvix.com/360/KMI/IntelliDrive/ApplUI/api/CustomReporting/UpdateReportSpec'
    print(f"➡️ Updating report spec → {update_url}")

    update_report_resp = requests.post(update_url, headers=headers, json=payload, verify=False)
    print(f"   🔹 Status: {update_report_resp.status_code}")
    print(f"   🔹 Response: {update_report_resp.text[:400]}")

    # Step 3: SaveReportSpec
    save_url = 'https://app.vivvix.com/360/KMI/IntelliDrive/ApplUI/api/CustomReporting/SaveReportSpec'
    print(f"➡️ Saving report spec → {save_url}")

    save_report = requests.post(save_url, headers=headers, data=unique_title, verify=False)
    print(f"   🔹 Status: {save_report.status_code}")
    # print(f"   🔹 Raw Response (reportSpecId): {save_report.text}")

    report_spec_id = save_report.text.strip()

    if not report_spec_id.isdigit():
        print(f"❌ ERROR: Invalid reportSpecId returned")
        return None

    print(f"✅ Extracted reportSpecId")

    # Step 4: RunReport
    run_url = (
        f'https://app.vivvix.com/360/KMI/IntelliDrive/ApplUI/api/CustomReporting/'
        f'DoReportSpecAction?reportSpecId={report_spec_id}&action=Run'
    )

    print(f"➡️ Running report → {run_url}")

    run_report = requests.post(
        run_url,
        headers=headers,
        data=f'reportSpecId={report_spec_id}&action=Run',
        verify=False
    )

    print(f"   🔹 Status: {run_report.status_code}")
    print(f"   🔹 Response: {run_report.text[:400]}")

    print(f"🎉 Finished submitting report for brand: {brand_name}")
    print("======================================\n")

    return report_spec_id


def check_reports_status():
    print("\n====================================")
    print("🔍 Checking report statuses...")
    print("====================================")

    # Get current reports
    print("➡️ Sending request to GetReportListData...")
    get_reports = requests.get(
        'https://app.vivvix.com/360/KMI/IntelliDrive/ApplUI/api/CustomReporting/GetReportListData?mode=FullView',
        headers=headers, data='FullView', verify=False
    )

    print(f"   🔹 HTTP Status: {get_reports.status_code}")

    if get_reports.status_code != 200:
        print("❌ Failed to fetch report list!")
        return 2

    time.sleep(3)

    reps = json.loads(get_reports.text)
    reports = reps.get('ReportList', {}).get('Reports', [])

    print(f"📄 Total reports fetched: {len(reports)}")

    # Check statuses
    incomplete = []
    for key in reports:
        if key['Status'] != 2:
            incomplete.append({
                "ReportId": key['ReportId'],
                "Name": key['ReportName'],
                "Status": key['Status']
            })

    if incomplete:
        print("⏳ Some reports are NOT finished yet:")
        for item in incomplete:
            print(f"   • ID {item['ReportId']} | {item['Name']} | Status={item['Status']}")
        print("⚠️Reports are still being created...⚠️\n")
        return False

    print("✅ All reports completed successfully!\n")
    return True

def create_multiple_reps(brands_excel, start, end):
    print('Creating reports')
    for brand in brands_excel[start:end]:
        try:
            report_spec_idv = create_report(brand)
            print(f"report {report_spec_idv} for brand {brand}")
        except Exception as e:
            print(e)

    # Wait until reports are completed
    print('Reports created, waiting for reports to run')

    finished_creating = check_reports_status()
    while not finished_creating:
        print(f"finish_creating is {finished_creating}, sleeping and running again")
        time.sleep(60)
        print("running again")
        finished_creating = check_reports_status()
    return finished_creating


# Gets download link of reports created
def get_download_links(brand_names):
    print("\n====================================")
    print("🔍 Fetching download links for brands:")
    for b in brand_names:
        print(f"   • {b}")
    print("====================================")

    links = []

    # Get all reports
    # print("➡️ Sending request to GetReportListData...")
    get_reports = requests.get(
        'https://app.vivvix.com/360/KMI/IntelliDrive/ApplUI/api/CustomReporting/GetReportListData?mode=FullView',
        headers=headers,
        data='FullView',
        verify=False
    )
    # print(f"   🔹 HTTP Status: {get_reports.status_code}")

    if get_reports.status_code != 200:
        print("❌ Failed to fetch report list!")
        return links

    time.sleep(2)
    reps = json.loads(get_reports.text)

    reports = reps.get('ReportList', {}).get('Reports', [])
    print(f"📄 Total reports on server: {len(reports)}")

    print("🔍 Looking for completed (Status=2) reports that match the brands...")

    matched = 0
    for key in reports:
        report_name = key['ReportName']
        status = key['Status']
        report_id = key['ReportId']

        # Condition 1: only completed reports
        if status != 2:
            continue

        # Condition 2: match by substring to any brand
        if not any(map(report_name.__contains__, brand_names)):
            continue

        matched += 1
        print(f"\n✅ MATCH #{matched}")
        print(f"   • Report ID: {report_id}")
        print(f"   • Report Name: {report_name}")
        print(f"   • Status: {status}")

        # Clean brand name by removing the last suffix (usually date/time)
        name = report_name.rsplit(' ', 1)[0]
        print(f"   • Extracted brand name: {name}")

        # Build download URLs
        excel_link = key['ReportOutputs'][1]['FullFilePath']


        print(f"   • CSV/Excel file link: {excel_link}")

        links.append({
            'XLSX': excel_link,
            'reportID': report_id,
            'Brand': name
        })

    if matched == 0:
        print("❌ No completed reports matched your brand list.")

    print("\n📦 Final: Found", matched, "matching downloadable reports.")
    print("====================================\n")

    return links




def download_reports(brands_excel, start, end, path):
    print("\n============================")
    print(f"📥 Starting download for brands[{start}:{end}]")
    print("============================")

    links = get_download_links(brands_excel[start:end])
    print(f"🔍 Found {len(links)} completed reports in Vivvix.")

    if not links:
        print("⚠️ No reports found. Skipping download.\n")
        return

    if not os.path.exists(path):
        os.makedirs(path)

    print("\n📥 Downloading reports:")

    for item in links:
        brand = item["Brand"].replace("*", "").strip()
        xlsx_url = item["XLSX"]   # ← שדה חדש

        print(f"\n➡️ Processing brand: {brand}")

        download_path = os.path.join(path, brand)

        os.makedirs(download_path, exist_ok=True)

        try:
            print(f"   📄 Downloading XLSX from {xlsx_url} ...")
            response = requests.get(xlsx_url)

            response.raise_for_status()

            brand_clean = str(brand)
            file_path = os.path.join(str(download_path), f"{str(brand_clean)}.xlsx")

            with open(file_path, "wb") as f:
                f.write(response.content)

            print(f"   ✅ Saved Excel: {file_path}")

        except Exception as e:
            print(f"   ❌ Failed to download XLSX for brand '{brand}': {e}")

    print("\n🎉 All downloads completed!")
    print("============================\n")

def get_sliced_excel_with_brands_names():
    try:

        df = pd.read_excel('brands.xlsx', header=None)
        brands_excel_raw = df[0]
        non_empty = brands_excel_raw[brands_excel_raw.astype(str).str.strip() != ""]
        first_brand_row = non_empty.index[0]
        last_brand_row = non_empty.index[-1] + 1
        return brands_excel_raw[first_brand_row:last_brand_row].to_numpy(), first_brand_row, last_brand_row
    except FileNotFoundError as e:
        print(e)
        return None, None, None


# Runs the whole process at once
def run_batch(brands_excel, start, end, download_path):
    print("\n============================")
    print(f"🚀 Running batch: brands[{start}:{end}]")
    print("============================")

    batch_size = end - start
    print(f"📦 Number of brands in this batch: {batch_size}")

    print("🔍 Brands in batch:")
    for b in brands_excel[start:end]:
        print(f"   • {b}")

    print("\n🛠️ Step 1: Creating reports...")
    status = create_multiple_reps(brands_excel, start, end)
    if status == 2:
        return None
    print("✅ Finished creating report specs.\n") if status else print("Not yet...")

    print("🛠️ Step 2: Searching for completed reports...")
    links = get_download_links(brands_excel[start:end])

    print(f"📄 Found {len(links)} completed reports ready for download.")

    if len(links) == 0:
        print("⚠️ No completed reports found for this batch. Skipping download.\n")
        return

    print("\n🛠️ Step 3: Downloading reports")
    download_reports(brands_excel, start, end, download_path)

    print(f"🎉 Batch completed successfully for brands[{start}:{end}]")
    print("============================\n")


if __name__ == '__main__':
    driver = create_driver()
    cookies = login_if_needed(driver)

    with open("headers.json", "r", encoding="utf-8") as headers_file:
        headers = json.load(headers_file)

    cookie_header = "; ".join([f"{c['name']}={c['value']}" for c in cookies])
    headers["Cookie"] = cookie_header


    print("🔥 Cookie injected into HEADERS automatically")

    excel, first_brand_row_idx, last_brand_row_idx = get_sliced_excel_with_brands_names()


    # links = get_download_links(brands_excel[first_brand_row_idx:last_brand_row_idx])
    # download_reports(first_brand_row_idx, last_brand_row_idx, FILES_REPORTS_DETAILED)
    # check_reports_status()
    if excel is not None:
        run_batch(excel, first_brand_row_idx, last_brand_row_idx, FILES_REPORTS_DETAILED)
