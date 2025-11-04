import requests
from io import BytesIO
import dropbox
from dropbox import Dropbox
from dropbox.exceptions import ApiError
from dropbox.files import WriteMode

dbx = Dropbox("YOUR_ACCESS_TOKEN")

def download_media(creative_id, url, subfolder_path):
    """
    מורידה מדיה מהאינטרנט ומעלה ישירות ל-Dropbox
    לפי סוג הקובץ (image/video/other)
    אל תת התיקייה שנשלחה בארגומנט.
    """
    headers = {"User-Agent": "Mozilla/5.0"}

    try:
        # שלב 1: הורדה מה-URL
        with requests.get(url, stream=True, timeout=30, headers=headers) as response:
            response.raise_for_status()
            content_type = response.headers.get("Content-Type", "").lower()

            # שלב 2: קביעת סוג וסיומת
            if "image" in content_type:
                subdir = "images"
                ext = "." + content_type.split("/")[-1].split(";")[0]
            elif "video" in content_type:
                subdir = "videos"
                ext = "." + content_type.split("/")[-1].split(";")[0]
            else:
                subdir = "other"
                ext = ""

            # שלב 3: קביעת הנתיב המלא בענן
            folder_path = f"{subfolder_path}/{subdir}"
            try: # Check if folder "video"/"images" exists
                dbx.files_get_metadata(folder_path)
            except ApiError:
                dbx.files_create_folder_v2(folder_path)

            filename = f"{creative_id}{ext or '.bin'}"
            dropbox_path = f"{folder_path}/{filename}"

            # שלב 4: העלאה ישירה ל-Dropbox
            file_bytes = BytesIO()
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    file_bytes.write(chunk)
            file_bytes.seek(0)

            dbx.files_upload(file_bytes.read(), dropbox_path, mode=dropbox.files.WriteMode("overwrite"))

            print(f"✅ הועלה בהצלחה ל-Dropbox: {dropbox_path} ({content_type or 'unknown'})")
            return dropbox_path

    except Exception as e:
        print(f"❌ שגיאה בהורדת {url}: {e}")
        return None


def download_ads(ads, subfolder_path):
    for creative_id, url in ads.items():
        download_media(creative_id, url, subfolder_path)


if __name__ == '__main__':
    pass


