import os

from extract import extract
from investigate import create_driver, login_if_needed, investigate
from download import download_ads
import dropbox
import re
from dropbox.exceptions import ApiError


excel_path = "booking_com_2024_1696090.xlsx"
sheet_name = "Report"

ROOT_IMPORT_PATH = "/vivvix_reports (לא מפורטים)"
ROOT_EXPORT_PATH = "/Vivix data"
ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")

dbx = dropbox.Dropbox(ACCESS_TOKEN)


def run(subfolder_path):
    print(f"\n🚀 Starting run() for: {subfolder_path}")

    # יצירת דפדפן והתחברות
    print("🌐 Creating driver and logging in (if needed)...")
    driver = create_driver()
    login_if_needed(driver)

    # שלב 1 – חילוץ URLs ו־IDs
    print(f"📊 Extracting data from Excel: {excel_path}")
    urls, creative_id_set = {}, set()
    extract(urls, creative_id_set, excel_path, sheet_name)
    print(f"🔍 Extracted {len(urls)} URLs, {len(creative_id_set)} creative IDs.")

    # שלב 2 – חקירה
    ads = {}
    print("🧠 Investigating ads...")
    investigate(urls, driver, ads)
    print(f"✅ Investigation complete. Found {len(ads)} ads.")

    # סגירת דפדפן
    driver.quit()
    print("🧹 Browser closed.")

    # שלב 3 – הורדה ל־Dropbox
    print(f"⬇️ Downloading media for {len(ads)} ads into: {subfolder_path}")
    download_ads(ads, subfolder_path)
    print(f"✅ Finished run() for: {subfolder_path}\n")


def main():
    print("🚀 Starting main() process...")
    print(f"📁 Checking source folder: {ROOT_IMPORT_PATH}")

    try:
        files = dbx.files_list_folder(ROOT_IMPORT_PATH).entries
        print(f"📂 Found {len(files)} items in '{ROOT_IMPORT_PATH}'.")
    except ApiError as e:
        print(f"❌ Error accessing import folder: {e}")
        return

    for file_entry in files:
        if file_entry.name.endswith((".xlsx", ".xls")):
            print(f"\n====================================")
            print(f"📄 Processing Excel file: {file_entry.name}")

            match = re.match(r"^(.*?)_\d", file_entry.name)
            if match:
                brand_name = match.group(1)
            else:
                brand_name = file_entry.name.rsplit(".", 1)[0]

            subfolder_path = f"{ROOT_EXPORT_PATH}/{brand_name}"
            print(f"📂 Target brand folder: {subfolder_path}")

            # בדוק אם קיימת תיקייה למותג
            try:
                dbx.files_get_metadata(subfolder_path)
                print(f"✅ Folder already exists: {subfolder_path}")
            except ApiError:
                dbx.files_create_folder_v2(subfolder_path)
                print(f"📁 Created new folder: {subfolder_path}")

            # הפעלת הריצה למותג
            run(subfolder_path)

    print("\n🏁 All Excel files processed successfully!")


if __name__ == '__main__':
    main()
