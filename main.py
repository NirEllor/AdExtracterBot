import os
from extract import extract
from investigate import create_driver, login_if_needed, investigate
from download import download_ads
import dropbox
import re
from dropbox.exceptions import ApiError


sheet_name = "Report"

ROOT_IMPORT_PATH = "/vivvix_reports (לא מפורטים)"
ROOT_EXPORT_PATH = "/Vivix data"

dbx = dropbox.Dropbox(
    oauth2_refresh_token=os.getenv("DROPBOX_REFRESH_TOKEN"),
    app_key=os.getenv("DROPBOX_APP_KEY"),
    app_secret=os.getenv("DROPBOX_APP_SECRET"),
)

def run(driver, subfolder_path, brand_name, file_name):
    print(f"\n🚀 Starting run() for: {subfolder_path}")

    # יצירת דפדפן והתחברות
    print("🌐 Creating driver and logging in (if needed)...")


    # שלב 1 – חילוץ URLs ו־IDs
    print(f"📊 Extracting data from Excel: {file_name}")
    urls, creative_id_set = {}, set()
    extract(urls, creative_id_set, file_name, sheet_name)
    print(f"🔍 Extracted {len(urls)} URLs, {len(creative_id_set)} creative IDs.")

    # שלב 2 – חקירה
    ads = {}
    print("🧠 Investigating ads...")
    investigate(urls, driver, ads, brand_name)
    print(f"✅ Investigation complete. Found {len(ads)} ads.")

    # סגירת דפדפן
    print("🧹 Browser closed.")

    # שלב 3 – הורדה ל־Dropbox
    print(f"⬇️ Downloading media for {len(ads)} ads into: {subfolder_path}")
    download_ads(ads, brand_name)
    print(f"✅ Finished run() for: {subfolder_path}\n")


def main():
    created_folders = set()

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
        print(f"🔢 File {index}/{len(total_excels)}")
        print(f"📄 Processing Excel file: {file_entry.name}")

        # הורדת הקובץ ל־temp path מקומי
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

        # חילוץ שם המותג
        match = re.match(r"^(.*?)_\d", file_entry.name)
        if match:
            brand_name = match.group(1)
        else:
            brand_name = file_entry.name.rsplit(".", 1)[0]
        print(f"🏷️  Brand name extracted: {brand_name}")

        # קביעת נתיב תיקיית היעד ב-Dropbox
        subfolder_path = f"{ROOT_EXPORT_PATH}/{brand_name}"
        print(f"📂 Target brand folder: {subfolder_path}")

        # יצירת תיקייה למותג אם אינה קיימת
        if subfolder_path not in created_folders:
            try:
                dbx.files_get_metadata(subfolder_path)
                print(f"✅ Folder already exists: {subfolder_path}")
            except ApiError:
                dbx.files_create_folder_v2(subfolder_path)
                print(f"📁 Created new folder: {subfolder_path}")

        # הרצת הפונקציה שלך על הקובץ המקומי
        print(f"🚀 Running 'run()' for brand '{brand_name}'...")
        run(driver, subfolder_path, brand_name, temp_local_path)
        print(f"✅ Finished processing brand '{brand_name}'.")

        # מחיקת הקובץ המקומי אחרי העיבוד
        try:
            os.remove(temp_local_path)
            print(f"🗑️ Deleted temporary file: {temp_local_path}")
        except Exception as e:
            print(f"⚠️ Could not delete temp file: {e}")

    # סגירת הדפדפן בסיום
    print("\n🧹 Closing browser...")
    driver.quit()

    print("\n🏁 All Excel files processed successfully!")
if __name__ == '__main__':
    main()
