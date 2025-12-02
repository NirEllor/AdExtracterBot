import os
import dropbox
from dotenv import load_dotenv

# ← טוען את משתני הסביבה מהקובץ .env
load_dotenv()

PLACE_FOR_FILES = r"C:\Vivix_Media_Files"

ROOT_IMPORT_PATH = os.getenv("DROPBOX_DETAILED_REPORTS_PATH")
ROOT_EXPORT_PATH = os.getenv("DROPBOX_UPLOAD_FOLDER_PATH")

USERNAME = os.getenv("APP_USERNAME")
PASSWORD = os.getenv("APP_PASSWORD")

dbx = dropbox.Dropbox(
    oauth2_refresh_token=os.getenv("DROPBOX_REFRESH_TOKEN"),
    app_key=os.getenv("DROPBOX_APP_KEY"),
    app_secret=os.getenv("DROPBOX_APP_SECRET"),
)
