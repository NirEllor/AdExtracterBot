import os

import pandas as pd

from extract import extract
from investigate import create_driver, login_if_needed, investigate
from download import download_ads
import dropbox
import re
import time
from dropbox.exceptions import ApiError

PLACE_FOR_FILES = r"C:\Vivix_Media_Files"

os.makedirs(PLACE_FOR_FILES, exist_ok=True)

print(f"תיקייה נוצרה בהצלחה: {PLACE_FOR_FILES}")


ROOT_IMPORT_PATH = "/AdSpender/Vivvix Data/vivvix_reports_for_download"
ROOT_EXPORT_PATH = "/AdSpender/Vivvix Data/Media_files"
ONLY_ONE_FILE = "Jeep_2024_yearly_1711272.xlsx"
SHEET_NAME = "Report"

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

    return False if failed_files else True




def download_excel_from_dropbox(dbx, root_import_path, file_name, temp_dir=None):
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
        metadata, res = dbx.files_download(f"{root_import_path}/{file_name}")
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


def main(filtered_excel=False):
    created_folders = set()
    need_another_run = False

    print("🚀 Initializing Chrome driver...")
    driver = create_driver()
    print("🌐 Chrome driver created successfully!")

    print("🔑 Logging in if needed...")
    login_if_needed(driver)
    print("✅ Login check complete.\n")

    print("🚀 Starting main() process...")
    print(f"📁 Checking source folder: {ROOT_IMPORT_PATH}")

    try:
        files = dbx.files_list_folder(ROOT_IMPORT_PATH).entries
        print(f"📂 Found {len(files)} items in '{ROOT_IMPORT_PATH}'.")
    except ApiError as e:
        print(f"❌ Error accessing import folder: {e}")
        driver.quit()
        return

    total_excels = [f for f in files if f.name.endswith((".xlsx", ".xls"))]
    print(f"🧾 Total Excel files to process: {len(total_excels)}\n")

    for index, file_entry in enumerate(total_excels, start=1):
        print(f"\n====================================")
        if file_entry.name != ONLY_ONE_FILE:
            continue
        print(f"🔢 File {index}/{len(total_excels)}")
        start_time = time.time()
        print(f"📄 Processing Excel file: {file_entry.name}")

        temp_local_path = os.path.join(os.getcwd(), file_entry.name)
        print(f"⬇️ Downloading {file_entry.name} from Dropbox...")

        try:
            metadata, res = dbx.files_download(f"{ROOT_IMPORT_PATH}/{file_entry.name}")
            with open(temp_local_path, "wb") as f:
                f.write(res.content)
            print(f"✅ Saved locally as: {temp_local_path}")
        except Exception as e:
            print(f"❌ Failed to download {file_entry.name}: {e}")
            continue

        match = re.match(r"^(.*?)_\d", file_entry.name)
        if match:
            brand_name = match.group(1)
        else:
            brand_name = file_entry.name.rsplit(".", 1)[0]
        print(f"🏷️  Brand name extracted: {brand_name}")

        subfolder_path = f"{ROOT_EXPORT_PATH}/{brand_name}"
        print(f"📂 Target brand folder: {subfolder_path}")

        if subfolder_path not in created_folders:
            try:
                dbx.files_get_metadata(subfolder_path)
                print(f"✅ Folder already exists: {subfolder_path}")
            except ApiError:
                dbx.files_create_folder_v2(subfolder_path)
                print(f"📁 Created new folder: {subfolder_path}")

        print(f"🚀 Running 'run()' for brand '{brand_name}'...")
        need_another_run = run(driver, subfolder_path, brand_name, temp_local_path, filtered_excel=True if filtered_excel else False)
        end_time = time.time()
        print(f"✅ Finished processing brand '{brand_name}'.")
        elapsed_seconds = end_time - start_time
        elapsed_minutes = elapsed_seconds / 60

        print(f"The operation took {elapsed_seconds:.2f} seconds ({elapsed_minutes:.2f} minutes)")

        try:
            os.remove(temp_local_path)
            print(f"🗑️ Deleted temporary file: {temp_local_path}")
        except Exception as e:
            print(f"⚠️ Could not delete temp file: {e}")

    print("\n🧹 Closing browser...")
    driver.quit()
    print("\n🏁 All Excel files processed successfully!")

    return need_another_run






if __name__ == '__main__':
    need_another_run = True

    while need_another_run:
        need_another_run = main(filtered_excel=True)


