import json
import os
import time
import pandas as pd
from io import StringIO
import requests
from browser_investigate import login_if_needed, create_driver
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


FILES_REPORTS_DETAILED = r"C:\Vivix_Media_Files\Reports_Detailed"

brands = [
    'starbucks',
'Jamba_juice',
    "breyers",

]

def to_failed_filename(s: str) -> str:
    prefix = s.split("_", 1)[0]
    return prefix + "_failed_to_download.xlsx"



search_payload = {"SearchTerm": "",
                  "SearchType": 4,
                  "Take": 250,
                  "Skip": 0,
                  "Page": 0,
                  "PageSize": 0,
                  "EntitySet": {"EntitySetId": 10, "Name": "ReportSpecBC", "EntitySetType": 10, "Entities": [],
                                "IsActive": True, "AllEntitiesAreSelected": False},
                  "EntityTypes": [118],
                  "CategoryCodeEnabled": False,
                  "ExcludedSearchEntityItems": [{"EntityItemId": 522,
                                                 "Seq": 0,
                                                 "EntityName": None,
                                                 "EntityLongName": None,
                                                 "EntityCode": None,
                                                 "EntityNameWithGroupCount": None,
                                                 "GroupName": "",
                                                 "IsOwnedByMe": False,
                                                 "GroupEntityItemId": None,
                                                 "ISAdvEntityType": False,
                                                 "ISCatEntityType": True,
                                                 "EntityItemTypeDisplay": "Category",
                                                 "IsAGroup": False, "BelongsToGroup": False,
                                                 "NumberOfItemsInGroup": 0,
                                                 "StartDateAsString": None,
                                                 "Media": 0, "MediaType": 0,
                                                 "MarketId": 0,
                                                 "IsEntitySelected": False,
                                                 "IsEntitySelectable": False,
                                                 "IsEntityForcedSelected": False,
                                                 "EntityForcedSelectedReason": None,
                                                 "DisplayOrder": 0, "StateName": None,
                                                 "DMARank": 0,
                                                 "BrandCategoryEntityTypeDisplayOrder": 0,
                                                 "ProgramEntityTypeDisplayOrder": 0,
                                                 "ShowGroupMembersOnReport": False,
                                                 "CanBeDeletedFromSystem": False,
                                                 "ShowGroupMembersDesc": "",
                                                 "UniqueId": "103_0",
                                                 "GroupedEntities": None,
                                                 "SharedEntity": None,
                                                 "IsExclude": False,
                                                 "EntityId": 0,
                                                 "EntityType": 103}],
                  "HideSummaryMediaItems": False}

HEADERS = {
    'Accept': 'application/json, text/plain, */*',
    'Accept-Encoding': 'gzip',
    'Accept-Language': 'en',
    'Connection': 'keep-alive',
    'Host': 'app.vivvix.com',
    'Origin': 'https://app.vivvix.com',
    'Referer': 'https://app.vivvix.com/360/KMI/IntelliDrive/ApplUI/Spas/CustomReporting/CustomReportingPage.aspx?.pl=EditCustomReportSpec',
    'Sec-Fetch-Dest': 'empty',
    'Sec-Fetch-Mode': 'cors',
    'Sec-Fetch-Site': 'same-origin',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36',
    'sec-ch-ua': 'Google Chrome";v="113", "Chromium";v="113", "Not-A.Brand";v="24',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"Windows"'
}

driver = create_driver()
login_if_needed(driver)

cookies = {c['name']: c['value'] for c in driver.get_cookies()}

cookie_header = "; ".join([f"{k}={v}" for k, v in cookies.items()])

HEADERS["Cookie"] = cookie_header

print("🔥 Cookie injected into HEADERS automatically")


df = pd.read_excel('brands.xlsx', header=None)
brands_excel_raw = df[0]

non_empty = brands_excel_raw[brands_excel_raw.astype(str).str.strip() != ""]

first_brand_row_idx = non_empty.index[0]
last_brand_row_idx = non_empty.index[-1] + 1

brands_excel = brands_excel_raw[first_brand_row_idx:last_brand_row_idx].to_numpy()



def create_report(brand_name: str):
    print("\n======================================")
    print(f"🚀 Starting full report creation for: {brand_name}")
    print("======================================")

    # Load payload template
    print("📄 Loading payload template...")
    with open('creatives_payload.json') as user_file:
        file_contents = user_file.read()

    payload = json.loads(file_contents)

    # Insert brand into payload
    payload['Title'] = brand_name
    search_payload['SearchTerm'] = brand_name

    print(f"🔍 Searching entity for brand: {brand_name}")

    # Search brand entity
    search_url = 'https://app.vivvix.com/360/KMI/IntelliDrive/ApplUI/api/Entity/EntitySearch'
    brand_search = requests.post(
        search_url,
        headers=HEADERS,
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

    create_rep = requests.post(create_url, headers=HEADERS, verify=False)
    print(f"   🔹 Status: {create_rep.status_code}")
    print(f"   🔹 Response: {create_rep.text[:400]}")

    # Step 2: UpdateReportSpec
    update_url = 'https://app.vivvix.com/360/KMI/IntelliDrive/ApplUI/api/CustomReporting/UpdateReportSpec'
    print(f"➡️ Updating report spec → {update_url}")

    update_report_resp = requests.post(update_url, headers=HEADERS, json=payload, verify=False)
    print(f"   🔹 Status: {update_report_resp.status_code}")
    print(f"   🔹 Response: {update_report_resp.text[:400]}")

    # Step 3: SaveReportSpec
    save_url = 'https://app.vivvix.com/360/KMI/IntelliDrive/ApplUI/api/CustomReporting/SaveReportSpec'
    print(f"➡️ Saving report spec → {save_url}")

    save_report = requests.post(save_url, headers=HEADERS, data=brand_name + '*', verify=False)
    print(f"   🔹 Status: {save_report.status_code}")
    print(f"   🔹 Raw Response (reportSpecId): {save_report.text}")

    report_spec_id = save_report.text.strip()

    if not report_spec_id.isdigit():
        print(f"❌ ERROR: Invalid reportSpecId returned: {report_spec_id}")
        return None

    print(f"✅ Extracted reportSpecId = {report_spec_id}")

    # Step 4: RunReport
    run_url = (
        f'https://app.vivvix.com/360/KMI/IntelliDrive/ApplUI/api/CustomReporting/'
        f'DoReportSpecAction?reportSpecId={report_spec_id}&action=Run'
    )

    print(f"➡️ Running report → {run_url}")

    run_report = requests.post(
        run_url,
        headers=HEADERS,
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
        headers=HEADERS, data='FullView', verify=False
    )

    print(f"   🔹 HTTP Status: {get_reports.status_code}")

    if get_reports.status_code != 200:
        print("❌ Failed to fetch report list!")
        return False

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
        print("❌ Reports are still running...\n")
        return False

    print("✅ All reports completed successfully!\n")
    return True

def create_multiple_reps(start, end):
    print('Creating reports')
    for brand in brands_excel[start:end]:
        try:
            report_spec_idv = create_report(brand)
            print(f"report {report_spec_idv} for brand {brand}")
        except Exception as e:
            print(e)

    # Wait until reports are completed
    print('Reports created, waiting for reports to run')
    while not check_reports_status():
        time.sleep(60)


# Gets download link of reports created
def get_download_links(brand_names):
    print("\n====================================")
    print("🔍 Fetching download links for brands:")
    for b in brand_names:
        print(f"   • {b}")
    print("====================================")

    links = []

    # Get all reports
    print("➡️ Sending request to GetReportListData...")
    get_reports = requests.get(
        'https://app.vivvix.com/360/KMI/IntelliDrive/ApplUI/api/CustomReporting/GetReportListData?mode=FullView',
        headers=HEADERS,
        data='FullView',
        verify=False
    )
    print(f"   🔹 HTTP Status: {get_reports.status_code}")

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

        # Clean brand name by removing last suffix (usually date/time)
        name = report_name.rsplit(' ', 1)[0]
        print(f"   • Extracted brand name: {name}")

        # Build download URLs
        creative_link = (
            f'https://app.vivvix.com/360/KMI/IntelliDrive/ApplUI/Pages/'
            f'CreativePages/DownloadCreatives.aspx?.pl=DownloadCreatives'
            f'&searchType=CustomReporting&reportId={report_id}'
        )

        csv_link = key['ReportOutputs'][0]['FullFilePath']

        print(f"   • Creative ZIP link: {creative_link}")
        print(f"   • CSV/Excel file link: {csv_link}")

        links.append({
            'Creative': creative_link,
            'CSV': csv_link,
            'reportID': report_id,
            'Brand': name
        })

    if matched == 0:
        print("❌ No completed reports matched your brand list.")

    print("\n📦 Final: Found", matched, "matching downloadable reports.")
    print("====================================\n")

    return links


def download_excel_report(csv_url, download_path, brand_name):
    response = requests.get(csv_url)
    response.raise_for_status()

    df_ = pd.read_csv(StringIO(response.text))

    excel_path = os.path.join(download_path, f"{brand_name}.xlsx")

    df_.to_excel(excel_path, index=False)
    print(f"Saved Excel report: {excel_path}")


# Downloads all reports through their links
def download_reports(start, end, path):
    print("\n============================")
    print(f"📥 Starting download for brands[{start}:{end}]")
    print("============================")

    links = get_download_links(brands_excel[start:end])
    print(f"🔍 Found {len(links)} completed reports in Vivvix.")

    if len(links) == 0:
        print("⚠️ No reports found. Skipping download.\n")
        return

    if not os.path.exists(path):
        print(f"📁 Creating main download folder: {path}")
        os.makedirs(path)
    else:
        print(f"📁 Main folder already exists: {path}")

    print("🔧 Preparing download headers...")
    download_header = HEADERS.copy()
    download_header['Accept'] = (
        'text/html,application/xhtml+xml,application/xml;q=0.9,'
        'image/avif,image/webp,image/apng,*/*;q=0.8,application/'
        'signed-exchange;v=b3;q=0.7'
    )
    download_header['Accept-Encoding'] = 'gzip, deflate, br'

    print("\n📥 Downloading reports:")

    for item in links:
        brand = item['Brand'].replace('*', '').strip()
        csv_url = item['CSV']

        print(f"\n➡️ Processing brand: {brand}")

        download_path = os.path.join(path, brand)
        print(f"   📁 Creating folder: {download_path}")
        try:
            os.mkdir(download_path)
        except FileExistsError:
            print(f"   ⚠️ Folder already exists, skipping create.")

        print(f"   📄 Downloading Excel report from CSV URL...")
        try:
            download_excel_report(csv_url, download_path, brand)
            print(f"   ✅ Excel saved for: {brand}")
        except Exception as e:
            print(f"   ❌ Failed to download Excel for brand '{brand}': {e}")

    print("\n🎉 All downloads completed!")
    print("============================\n")



# Runs the whole process at once
def run_batch(start, end, download_path):
    print("\n============================")
    print(f"🚀 Running batch: brands[{start}:{end}]")
    print("============================")

    batch_size = end - start
    print(f"📦 Number of brands in this batch: {batch_size}")

    print("🔍 Brands in batch:")
    for b in brands[start:end]:
        print(f"   • {b}")

    print("\n🛠️ Step 1: Creating reports...")
    create_multiple_reps(start, end)
    print("✅ Finished creating report specs.\n")

    print("🛠️ Step 2: Searching for completed reports...")
    links = get_download_links(brands[start:end])

    print(f"📄 Found {len(links)} completed reports ready for download.")

    if len(links) == 0:
        print("⚠️ No completed reports found for this batch. Skipping download.\n")
        return

    print("\n🛠️ Step 3: Downloading reports and creatives...")
    download_reports(start, end, download_path)

    print(f"🎉 Batch completed successfully for brands[{start}:{end}]")
    print("============================\n")


if __name__ == '__main__':
    # links = get_download_links(brands_excel[first_brand_row_idx:last_brand_row_idx])
    download_reports(first_brand_row_idx, last_brand_row_idx, FILES_REPORTS_DETAILED)
    # check_reports_status()
    # run_batch(first_brand_row_idx, last_brand_row_idx, FILES_REPORTS_DETAILED
    #           )