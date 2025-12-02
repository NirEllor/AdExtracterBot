import re
import requests
import boto3
from io import BytesIO
from concurrent.futures import ThreadPoolExecutor, as_completed

s3 = boto3.client("s3")
S3_BUCKET = "ad-extracter-bot-bucket"    # <-- CHANGE THIS


def download_media(creative_id, url, brand_name, base_dir=None):
    headers = {"User-Agent": "Mozilla/5.0"}

    try:
        with requests.get(url, stream=True, timeout=40, headers=headers) as response:
            response.raise_for_status()
            content_type = response.headers.get("Content-Type", "").lower()

            # HTML wrapper - extract inner <img>
            if "text/html" in content_type:
                html = response.text
                match = re.search(r'<img[^>]+src="([^"]+)"', html)
                if match:
                    real_url = match.group(1)
                    print(f"🔗 HTML detected — fetching inner image: {real_url}")
                    return download_media(creative_id, real_url, brand_name, base_dir)

            # Determine type & extension
            if "image" in content_type:
                subdir = "images"
                ext = "." + content_type.split("/")[-1].split(";")[0]
            elif "video" in content_type:
                subdir = "videos"
                ext = "." + content_type.split("/")[-1].split(";")[0]
            else:
                subdir = "other"
                ext = ".bin"

            # Build S3 key
            filename = f"{creative_id}{ext}"
            s3_key = f"{brand_name}/{subdir}/{filename}"

            # Stream the download into memory and upload to S3
            file_buffer = BytesIO()
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    file_buffer.write(chunk)

            file_buffer.seek(0)

            s3.upload_fileobj(file_buffer, S3_BUCKET, s3_key)

        print(f"✅ Uploaded to s3://{S3_BUCKET}/{s3_key}")
        return f"s3://{S3_BUCKET}/{s3_key}", ext

    except Exception as e:
        print(f"❌ Error Downloading {url}: {e}")
        return None, None


def download_ads(ads, brand_name, place_for_files):
    failed_creative_ids = set()
    if not place_for_files:
        raise RuntimeError("place for files not filled")
    total = len(ads)
    print(f"🚀 מתחיל להוריד {total} פריטים עבור '{brand_name}' במקביל...")

    with ThreadPoolExecutor(max_workers=20) as executor:
        futures = {
            executor.submit(download_media, creative_id, url, brand_name, None): creative_id
            for creative_id, url in ads.items()
        }

        completed = 0
        for future in as_completed(futures):
            creative_id = futures[future]
            try:
                result_path, ext = future.result()
                if ext == ".bin":
                    print(f"failed file detected - {creative_id}")
                    failed_creative_ids.add(creative_id)

                completed += 1
                print(f"📥 {completed}/{total} הורדות הושלמו ({creative_id})")
            except Exception as e:
                print(f"⚠️ שגיאה במדיה {creative_id}: {e}")

    print(f"🏁 כל {total} ההורדות הושלמו עבור '{brand_name}'!")
    return failed_creative_ids


if __name__ == '__main__':
    pass
