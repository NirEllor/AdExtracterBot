import os
from extract import extract
from investigate import create_driver, login_if_needed, investigate
from download import download_ads
import dropbox
import time
from dropbox.files import WriteMode
import pandas as pd
import openpyxl
import re


PLACE_FOR_FILES = r"C:\Vivix_Media_Files"

os.makedirs(PLACE_FOR_FILES, exist_ok=True)



ROOT_IMPORT_PATH = "/AdSpender/Vivvix Data/vivvix_reports_for_download"
ROOT_EXPORT_PATH = "/AdSpender/Vivvix Data/Media_files"
REPORT_FILE = "GMC_2024_Yearly_1711244.xlsx"
FAILED_FILE = "GMC_failed_to_download.xlsx"
SHEET_NAME = "Report"
MAX_RUNS = 5

dbx = dropbox.Dropbox(
    oauth2_refresh_token=os.getenv("DROPBOX_REFRESH_TOKEN"),
    app_key=os.getenv("DROPBOX_APP_KEY"),
    app_secret=os.getenv("DROPBOX_APP_SECRET"),
)

def run(driver, subfolder_path, brand_name, file_name, filtered_excel=False):
    print(f"\n🚀 Starting run() for: {subfolder_path}")

    print("🌐 Creating driver and logging in (if needed)...")


    print(f"📊 Extracting data from Excel: {file_name}")
    urls, creative_id_set = {}, set()
    extract(urls, creative_id_set, file_name, SHEET_NAME, filtered_excel=True if filtered_excel else False)
    print(f"🔍 Extracted {len(urls)} URLs, {len(creative_id_set)} creative IDs.")

    ads = {}
    print("🧠 Investigating ads...")
    investigate(urls, driver, ads, brand_name)
    print(f"✅ Investigation complete. Found {len(ads)} ads.")

    print("🧹 Browser closed.")

    print(f"⬇️ Downloading media for {len(ads)} ads into: {subfolder_path}")
    failed_files = download_ads(ads, brand_name, PLACE_FOR_FILES)
    df_new = pd.DataFrame(list(failed_files), columns=["MASTER CREATIVE ID"])
    file_path = f"{brand_name}_failed_to_download.xlsx"

    try:
        df_old = pd.read_excel(file_path)
    except FileNotFoundError:
        df_old = pd.DataFrame(columns=["Values"])


    df_combined = pd.concat([df_old, df_new], ignore_index=True)

    df_combined.to_excel(file_path, index=False)

    print(f"✅ Finished run() for: {subfolder_path}\n")

    return True if not failed_files else False




def download_excel_from_dropbox(dbx_instance, root_import_path, file_name, temp_dir=None):
    """
    Downloads an Excel file from Dropbox to a temporary local directory.

    Returns:
        temp_local_path, brand_name
    """
    if temp_dir is None:
        temp_dir = os.getcwd()

    # Local path for temporary file
    temp_local_path = os.path.join(temp_dir, file_name)
    print(f"⬇️ Downloading {file_name} from Dropbox...")

    try:
        metadata, res = dbx_instance.files_download(f"{root_import_path}/{file_name}")
        with open(temp_local_path, "wb") as f:
            f.write(res.content)
        print(f"✅ Saved locally as: {temp_local_path}")
    except Exception as e:
        print(f"❌ Failed to download {file_name}: {e}")
        return None, None

    # Extract brand name from filename
    match = re.match(r"^(.*?)_\d", file_name)
    if match:
        brand_name = match.group(1)
    else:
        brand_name = file_name.rsplit(".", 1)[0]

    print(f"🏷️ Extracted brand name: {brand_name}")

    return temp_local_path, brand_name



def extract_url_from_formula(formula):
    """Extract URL from Excel HYPERLINK formulas."""
    if not isinstance(formula, str):
        return None
    m = re.search(r'HYPERLINK\("([^"]+)"', formula)
    return m.group(1) if m else None


def filter_failed_files(excel_path, failed_ids_excel, column_name="MASTER CREATIVE ID"):
    print(f"\n📝 Filtering Excel based on previous failures...")

    # 1️⃣ Load failed IDs (with cleaning)
    df_failed = pd.read_excel(failed_ids_excel)
    df_failed[column_name] = (
        df_failed[column_name]
        .astype(str)
        .str.replace(r"\.0$", "", regex=True)
        .str.strip()
    )
    failed_ids = set(df_failed[column_name])

    print("🟥 failed sample:", list(failed_ids)[:10])

    # 2️⃣ Load main Excel USING pandas only to decide which IDs to keep
    df = pd.read_excel(excel_path, skiprows=7)

    df[column_name] = (
        df[column_name]
        .astype(str)
        .str.replace(r"\.0$", "", regex=True)
        .str.strip()
    )

    # IDs to keep
    filtered_ids = set(df[df[column_name].isin(failed_ids)][column_name])
    print("🟦 df sample:", df[column_name].head(10).tolist())
    print(f"🔍 Number of matches: {len(filtered_ids)}")

    # 3️⃣ Load Excel with openpyxl (preserving formulas)
    wb = openpyxl.load_workbook(excel_path)

    # Use original sheet name 'Report'
    if "Report" in wb.sheetnames:
        ws = wb["Report"]
    else:
        ws = wb.active  # fallback
    original_sheet_name = ws.title

    # 4️⃣ Create NEW workbook that will contain filtered rows (formulas preserved)
    new_wb = openpyxl.Workbook()
    new_ws = new_wb.active
    new_ws.title = original_sheet_name  # keep original sheet name

    # 5️⃣ Copy header row (Excel header is row 8)
    header_row = 8
    for cell in ws[header_row]:
        new_ws.cell(row=1, column=cell.col_idx, value=cell.value)

    # 6️⃣ Copy filtered data rows (starting from row 9)
    new_row = 2
    for row in ws.iter_rows(min_row=9):
        creative_value = row[1].value
        creative_id = str(creative_value).replace(".0", "").strip() if creative_value else ""

        if creative_id in filtered_ids:
            for cell in row:
                new_ws.cell(
                    row=new_row,
                    column=cell.col_idx,
                    value=cell.value  # COPY formula / URL / value AS-IS
                )
            new_row += 1

    # 7️⃣ Save new workbook over original path
    new_wb.save(excel_path)

    print(f"📝 Filtered file saved (with formulas + original sheet name): {excel_path}")
    return excel_path


def main(filtered_excel=False):
    start_time = time.time()

    print("🚀 Initializing Chrome driver...")
    driver = create_driver()
    print("🌐 Chrome driver created successfully!")

    print("🔑 Logging in if needed...")
    login_if_needed(driver)
    print("✅ Login check complete.\n")

    print("🚀 Starting main() process...")
    print(f"📄 Working on single source file: {REPORT_FILE}")

    # 1 - Download the specific file only
    temp_local_path, brand_name = download_excel_from_dropbox(
        dbx, ROOT_IMPORT_PATH, REPORT_FILE
    )

    if not temp_local_path:
        print("❌ Failed to download source file. Aborting.")
        driver.quit()
        return False

    subfolder_path = f"{ROOT_EXPORT_PATH}/{brand_name}"

    # 2 - Run main processing (extract → investigate → download media)
    all_files_arrived = run(
        driver,
        subfolder_path,
        brand_name,
        temp_local_path,
        filtered_excel
    )

    # 3 - Delete temp Excel
    try:
        os.remove(temp_local_path)
        print(f"🗑️ Deleted temporary file: {temp_local_path}")
    except Exception as e:
        print(f"⚠️ Could not delete temp file: {e}")

    print("\n🧹 Closing browser...")
    end = time.time()
    elapsed_seconds = end - start_time
    elapsed_minutes = elapsed_seconds / 60
    print(f"⏱ Time took: {elapsed_seconds:.2f} seconds ({elapsed_minutes:.2f} minutes)")

    driver.quit()
    print("\n🏁 Processing finished!")

    return all_files_arrived

def apply_post_attempt_filtering():
    """
    Applies the filtering logic AFTER attempt #1:
    1. Download original REPORT_FILE from Dropbox
    2. Filter it according to FAILED_FILE
    3. Upload filtered version back to Dropbox
    4. Delete temp file
    """
    print("📝 Filtering Excel based on previous failures...")

    # 1 - Download source file from Dropbox
    temp_local_path, _ = download_excel_from_dropbox(
        dbx,
        ROOT_IMPORT_PATH,
        REPORT_FILE
    )

    if not temp_local_path:
        print("❌ Could not download source report for filtering.")
        return

    # 2 - Apply filtering using FAILED_FILE
    filter_failed_files(
        excel_path=temp_local_path,
        failed_ids_excel=FAILED_FILE,
        column_name="MASTER CREATIVE ID"
    )

    # 3 - Upload filtered report back to Dropbox
    with open(temp_local_path, "rb") as f:
        dbx.files_upload(
            f.read(),
            f"{ROOT_IMPORT_PATH}/{REPORT_FILE}",
            mode=WriteMode.overwrite
        )

    print(f"⬆️ Updated filtered report uploaded back to Dropbox.")

    # 4 - Cleanup
    try:
        os.remove(temp_local_path)
        print(f"🗑️ Deleted temporary file: {temp_local_path}")
    except Exception as e:
        print(f"⚠️ Could not remove temp file: {e}")


if __name__ == '__main__':
    attempt = 1
    all_files_downloaded = False

    while not all_files_downloaded and attempt <= MAX_RUNS:
        print(f"\n🚀 RUN #{attempt} STARTING...\n")

        if attempt > 1:
            print("Filtering...")
            apply_post_attempt_filtering()
            print("Filtering complete!")


        print(f"📊 Running attempt {attempt} out of {MAX_RUNS}.\n")

        all_files_downloaded = main(filtered_excel=True)

        attempt += 1


    if all_files_downloaded:
        print("\n🎉 Finished! No failed creative IDs remain.")


    else:
        print(f"\n⚠️ Stopping: reached max attempts ({MAX_RUNS}).")


    print("\n🏁 All done.")



