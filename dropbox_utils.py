import os
import re
from dropbox.files import WriteMode
import dropbox
from config import  ROOT_IMPORT_PATH




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

def extract_report_name(dbx_instance, brand, root_import_path=ROOT_IMPORT_PATH):
    """
    Returns the first Excel file name in a Dropbox folder that contains BRAND in its name.
    If multiple files match, returns the first one found.
    If none match, returns None.
    """
    print(f"📂 Scanning Dropbox folder: {root_import_path}")
    print(f"🔎 Looking for Excel file containing brand: '{brand}'")

    try:
        result = dbx_instance.files_list_folder(root_import_path)
    except Exception as e:
        print(f"❌ Failed to access folder: {e}")
        return None

    BRAND_lower = brand.lower()

    for entry in result.entries:
        if not isinstance(entry, dropbox.files.FileMetadata):
            continue

        name = entry.name

        # Only Excel files
        if not name.lower().endswith(".xlsx"):
            continue

        # Does the file contain the brand?
        if BRAND_lower in name.lower():
            print(f"✅ Found matching file: {name}")
            return name

    print(f"⚠️ No Excel file found for brand '{brand}'.")
    return None
