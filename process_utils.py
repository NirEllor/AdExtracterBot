import os

from config import ROOT_EXPORT_PATH
from dropbox_utils import download_excel_from_dropbox, ROOT_IMPORT_PATH
from excel_utils import apply_post_attempt_filtering, extract_external_urls
from browser_investigate import create_driver, login_if_needed, investigate
from browser_download import download_ads
from config import dbx
import time
import pandas as pd



PLACE_FOR_FILES = r"C:\Vivix_Media_Files"
SHEET_NAME = "Report"
MAX_RUNS = 8


os.makedirs(PLACE_FOR_FILES, exist_ok=True)


def extract_urls_from_excel(file_name, sheet_name, filtered_excel=False):
    print(f"📊 Extracting data from Excel: {file_name}")
    urls, creative_ids = {}, set()
    extract_external_urls(urls, creative_ids, file_name, sheet_name, filtered_excel)
    print(f"🔍 Extracted {len(urls)} URLs, {len(creative_ids)} creative IDs.")
    return urls, creative_ids

def investigate_ads_and_collect(driver, urls, brand_name):
    ads = {}
    print("🧠 Investigating ads...")
    failed_creative_ids = investigate(urls, driver, ads, brand_name)
    print(f"✅ Investigation complete. Found {len(ads)} ads.")
    return ads, failed_creative_ids

def download_media_assets(ads, brand_name):
    print(f"⬇️ Downloading media for {len(ads)} ads...")
    failed_files = download_ads(ads, brand_name, PLACE_FOR_FILES)
    return failed_files

def save_failed_ids_excel(brand_name, failed_ids):
    file_path = f"{brand_name}_failed_to_download.xlsx"
    df_new = pd.DataFrame(list(failed_ids), columns=["MASTER CREATIVE ID"])

    try:
        df_old = pd.read_excel(file_path)
    except FileNotFoundError:
        df_old = pd.DataFrame(columns=["MASTER CREATIVE ID"])

    df_combined = pd.concat([df_old, df_new], ignore_index=True)
    df_combined.to_excel(file_path, index=False)

def ads_extractor_bot(driver, subfolder_path, brand_name, file_name, filtered_excel=False):
    print(f"\n🚀 Starting run() for: {subfolder_path}")

    # 1. Extract URLs
    urls, creative_ids = extract_urls_from_excel(
        file_name, SHEET_NAME, filtered_excel
    )

    # 2. Investigate ads
    ads, failed_creative_ids = investigate_ads_and_collect(
        driver, urls, brand_name
    )

    # 3. Download media
    failed_files = download_media_assets(ads, brand_name)

    # 4. Save failed IDs
    save_failed_ids_excel(brand_name, failed_files)

    print(f"✅ Finished run() for: {subfolder_path}\n")

    # success if no failures at all
    return len(failed_files) == 0 and len(failed_creative_ids) == 0


def init_driver_session():
    """Create driver + login."""
    print("🚀 Initializing Chrome driver...")
    driver = create_driver()
    print("🌐 Chrome driver created successfully!")

    print("🔑 Logging in if needed...")
    login_if_needed(driver)
    print("✅ Login check complete.\n")

    return driver

def download_report_locally(report_name, brands):
    """Download Excel and infer brand + subfolder path."""
    temp_local_path, brand_name = download_excel_from_dropbox(
        dbx,
        ROOT_IMPORT_PATH,
        report_name,
        brands
    )

    if not temp_local_path:
        print("❌ Failed to download source file.")
        return None, None, None

    subfolder_path = f"{ROOT_EXPORT_PATH}/{brand_name}"

    return temp_local_path, brand_name, subfolder_path

def process_ads_from_excel(driver, subfolder_path, brand_name, temp_path, filtered_excel):
    """Runs extract → investigate → download ads flow."""
    return ads_extractor_bot(
        driver,
        subfolder_path,
        brand_name,
        temp_path,
        filtered_excel
    )

def cleanup_temp_file(path):
    """Deletes temporary downloaded Excel."""
    try:
        os.remove(path)
        print(f"🗑️ Deleted temporary file: {path}")
    except Exception as e:
        print(f"⚠️ Could not delete temp file: {e}")

def process_single_run(report_name, brands, filtered_excel=False):
    start_time = time.time()
    print(f"🚀 Starting main() process for: {report_name}")

    # 1. Driver + login
    driver = init_driver_session()

    # 2. Download Excel
    temp_path, brand_name, subfolder_path = download_report_locally(report_name, brands)
    if not temp_path:
        driver.quit()
        return False

    # 3. Full ad-processing pipeline
    all_files_arrived = process_ads_from_excel(
        driver,
        subfolder_path,
        brand_name,
        temp_path,
        filtered_excel
    )

    # 4. Cleanup temp Excel
    cleanup_temp_file(temp_path)

    # 5. Close browser
    print("\n🧹 Closing browser...")
    driver.quit()

    # Timing info
    end = time.time()
    elapsed_seconds = end - start_time
    elapsed_minutes = elapsed_seconds / 60
    print(f"⏱ Time took: {elapsed_seconds:.2f} seconds ({elapsed_minutes:.2f} minutes)")
    print("\n🏁 Processing finished!")

    return all_files_arrived



def run(report_name, failed_files_excel_name, brands, max_runs=MAX_RUNS):
    attempt = 1
    all_files_downloaded = False

    while not all_files_downloaded and attempt <= MAX_RUNS:
        print(f"\n🚀 RUN #{attempt} STARTING...\n")

        if attempt > 1:  # Dealing with failed files
            print("Filtering...")
            apply_post_attempt_filtering(report_name, failed_files_excel_name,  brands, attempt=attempt)
            print("Filtering complete!")


        print(f"📊 Running attempt {attempt} out of {max_runs}.\n")

        all_files_downloaded = process_single_run(report_name, brands, filtered_excel=True)

        attempt += 1



    if all_files_downloaded:
        print("\n🎉 Finished! No failed creative IDs remain.")


    else:
        print(f"\n⚠️ Stopping: reached max attempts ({MAX_RUNS}).")


    print("\n🏁 All done.")


