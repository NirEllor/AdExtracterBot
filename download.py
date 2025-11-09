import os
import re

import requests
from concurrent.futures import ThreadPoolExecutor, as_completed


def download_media(creative_id, url, brand_name, base_dir=r"C:\עוזר מחקר\AdExtracterBot\ads"):
    headers = {"User-Agent": "Mozilla/5.0"}

    try:
        with requests.get(url, stream=True, timeout=15, headers=headers) as response:
            response.raise_for_status()
            content_type = response.headers.get("Content-Type", "").lower()

            if "text/html" in content_type:
                html = response.text
                match = re.search(r'<img[^>]+src="([^"]+)"', html)
                if match:
                    real_url = match.group(1)
                    print(f"🔗 HTML detected — fetching inner image: {real_url}")
                    return download_media(creative_id, real_url, brand_name, base_dir)


            if "image" in content_type:
                subdir = "images"
                ext = "." + content_type.split("/")[-1].split(";")[0]
            elif "video" in content_type:
                subdir = "videos"
                ext = "." + content_type.split("/")[-1].split(";")[0]
            else:
                subdir = "other"
                ext = ".bin"

            output_dir = os.path.join(base_dir, brand_name, subdir)
            os.makedirs(output_dir, exist_ok=True)

            filename = f"{creative_id}{ext}"
            output_path = os.path.join(output_dir, filename)

            with open(output_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)

        print(f"✅ נשמר בהצלחה: {output_path}")
        return output_path

    except Exception as e:
        print(f"❌ שגיאה בהורדת {url}: {e}")
        return None


def download_ads(ads, brand_name):
    total = len(ads)
    print(f"🚀 מתחיל להוריד {total} פריטים עבור '{brand_name}' במקביל...")

    # Thread pool עם 10 חוטים (ניתן לשנות בהתאם לחוזק המחשב והאינטרנט)
    with ThreadPoolExecutor(max_workers=20) as executor:
        futures = {
            executor.submit(download_media, creative_id, url, brand_name): creative_id
            for creative_id, url in ads.items()
        }

        completed = 0
        for future in as_completed(futures):
            creative_id = futures[future]
            try:
                result = future.result()
                completed += 1
                print(f"📥 {completed}/{total} הורדות הושלמו ({creative_id})")
            except Exception as e:
                print(f"⚠️ שגיאה במדיה {creative_id}: {e}")

    print(f"🏁 כל {total} ההורדות הושלמו עבור '{brand_name}'!")


if __name__ == '__main__':
    pass