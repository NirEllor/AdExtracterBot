import os
import requests

def download_media(creative_id, url, brand_name, base_dir=r"C:\עוזר מחקר\AdExtracterBot\ads"):
    """
    מוריד מדיה מה-URL ושומר אותה בנתיב:
    base_dir / subfolder_path / <images|videos|other>
    """
    headers = {"User-Agent": "Mozilla/5.0"}

    try:
        # --- שלב 1: בקשת GET עם stream ---
        with requests.get(url, stream=True, timeout=30, headers=headers) as response:
            response.raise_for_status()

            # --- שלב 2: זיהוי סוג לפי header ---
            content_type = response.headers.get("Content-Type", "").lower()
            if "image" in content_type:
                subdir = "images"
                ext = "." + content_type.split("/")[-1].split(";")[0]  # לדוגמה .jpeg
            elif "video" in content_type:
                subdir = "videos"
                ext = "." + content_type.split("/")[-1].split(";")[0]  # לדוגמה .mp4
            else:
                subdir = "other"
                ext = ""

            # --- שלב 3: יצירת נתיב היעד המלא ---
            # תיקיית בסיס -> שם מותג -> תת-תיקייה לפי סוג קובץ
            output_dir = os.path.join(base_dir, brand_name, subdir)
            os.makedirs(output_dir, exist_ok=True)

            # --- שלב 4: שם הקובץ לפי creative_id בלבד ---
            filename = f"{creative_id}{ext or '.bin'}"
            output_path = os.path.join(output_dir, filename)

            # --- שלב 5: כתיבה לקובץ ---
            with open(output_path, "wb") as file:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        file.write(chunk)

        print(f"✅ נשמר בהצלחה: {output_path} ({content_type or 'unknown'})")
        return output_path

    except Exception as e:
        print(f"❌ שגיאה בהורדת {url}: {e}")
        return None


def download_ads(ads, subfolder_path):
    for creative_id, url in ads.items():
        download_media(creative_id, url, subfolder_path)


if __name__ == '__main__':
    pass
