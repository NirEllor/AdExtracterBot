import os
import pickle
import time
from selenium import webdriver
from selenium.common import TimeoutException, NoSuchElementException
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from dotenv import load_dotenv
import pandas as pd




# === קונפיגורציה כללית ===
CHROMEDRIVER_PATH = r"C:\chromedriver-win64\chromedriver.exe"
COOKIES_FILE = "cookies.pkl"
LOGIN_URL = "https://app.vivvix.com/360/"

load_dotenv()

USERNAME = os.getenv("APP_USERNAME")
PASSWORD = os.getenv("APP_PASSWORD")
if not USERNAME or not PASSWORD:
    raise RuntimeError("Missing credentials: set APP_USERNAME and APP_PASSWORD in env")


# === יצירת driver ===
def create_driver():
    chrome_options = Options()
    # chrome_options.add_argument("--start-maximized")
    chrome_options.add_argument("--headless=new")  # לבוט ללא חלון גרפי
    service = Service(CHROMEDRIVER_PATH)
    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver


# === התחברות אוטומטית עם cookies ===
def login_if_needed(driver):
    driver.get(LOGIN_URL)
    time.sleep(2)

    # === Try loading cookies first ===
    if os.path.exists(COOKIES_FILE):
        try:
            cookies = pickle.load(open(COOKIES_FILE, "rb"))
            for c in cookies:
                if "expiry" in c:
                    c["expiry"] = int(c["expiry"])
                driver.add_cookie(c)
            driver.refresh()
            time.sleep(5)
            print("✅ Cookies loaded — כנראה כבר מחובר.")
            return
        except Exception as e:
            print("⚠️ בעיה בטעינת cookies:", e)

    print("🔐 מבצע התחברות ראשונה...")
    wait = WebDriverWait(driver, 10)
    try:
        signin_btn = wait.until(EC.element_to_be_clickable((By.CLASS_NAME, "signin")))
        signin_btn.click()
        
        # Wait for a visible username input (handles both layouts)
        def find_visible_input(by, value):
            elements = driver.find_elements(by, value)
            for el in elements:
                if el.is_displayed():
                    return el
            return None

        # Ensure form is visible (some versions have animation delay)
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'form[name="cognitoSignInForm"]')))
        time.sleep(5)

        username_input = None
        password_input = None
        for _ in range(10):  # retry a few times for dynamic layouts
            username_input = find_visible_input(By.ID, "signInFormUsername")
            password_input = find_visible_input(By.ID, "signInFormPassword")
            if username_input and password_input:
                break
            time.sleep(1)

        if not username_input or not password_input:
            raise RuntimeError("Couldn't locate visible username/password fields")

        # Scroll into view and fill credentials
        driver.execute_script("arguments[0].scrollIntoView(true);", username_input)
        time.sleep(1)
        username_input.clear()
        username_input.send_keys(USERNAME)
        password_input.clear()
        password_input.send_keys(PASSWORD)

        # Find and click visible submit button
        login_button = find_visible_input(By.NAME, "signInSubmitButton")
        if not login_button:
            raise RuntimeError("Couldn't locate visible submit button")
        driver.execute_script("arguments[0].scrollIntoView(true);", login_button)
        time.sleep(1)
        login_button.click()

        # Wait for redirect after successful login
        wait.until(lambda d: "login" not in d.current_url.lower())

        # Save cookies for reuse
        pickle.dump(driver.get_cookies(), open(COOKIES_FILE, "wb"))
        print("✅ התחברות בוצעה בהצלחה וה-cookies נשמרו.")
    except Exception as e:
        print("❌ שגיאה בהתחברות:", e)


# === חילוץ קישור המדיה מתוך source שנמצא תחת img/video ===
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def extract_single_media_source(driver):
    wait = WebDriverWait(driver, 50)


    # 🔹 קודם ננסה לחפש וידאו
    try:
        video_div = wait.until(EC.presence_of_element_located((By.ID, "video")))
        source = video_div.find_element(By.TAG_NAME, "source")
        src = source.get_attribute("src")
        if src:
            print(f"🎥 נמצא וידאו: {src}")
            return src
    except TimeoutException or NoSuchElementException as e:
        print("❌ לא נמצא וידאו, ממשיך לבדוק תמונה...")
        print(e)

    # 🔹 אם לא נמצא וידאו, ננסה תמונה
    try:
        # המתן עד שתופיע תמונה עם vivix ב-src
        image_element = wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "img[src*='CreativeViewer.axd']"))
        )

        # שלוף את הכתובת של התמונה
        src = image_element.get_attribute("src")
        if src:
            print(f"🖼️ נמצאה תמונה: {src}")
            return src

    except TimeoutException or NoSuchElementException as e:
        print("❌ לא נמצא תמונה, ממשיך לבדוק תמונה...")
        print(e)

    # 🔹 fallback – לא נמצא כלום
    print("⚠️ לא נמצא אלמנט וידאו או תמונה עם src")
    return None

from openpyxl import Workbook

def save_ads_to_excel(ads, output_path=r"C:\עוזר מחקר\AdExtracterBot\ads\ads.xlsx"):
    """
    מקבל מילון שבו כל מפתח הוא מזהה (creative_id) וכל ערך הוא URL.
    שומר לקובץ Excel: עמודה A = מפתח, עמודה B = ערך.
    """
    wb = Workbook()
    ws = wb.active
    ws.title = "Ads"

    # כותרות לעמודות
    ws.append(["Creative ID", "URL"])

    # כתיבת הנתונים
    for key, value in ads.items():
        ws.append([key, value])

    # שמירה לקובץ
    wb.save(output_path)
    print(f"✅ נשמר בהצלחה: {output_path}")



# === ביקור בעמוד ובדיקת המדיה ===
def investigate_page(driver, url):
    print(f"\n🌐 Navigating to page: {url}")
    try:
        driver.get(url)
        print("⏳ Waiting for body to load...")
        WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        print(f"🔎 Page loaded successfully for {url}")

        print("📸 Attempting to extract media source...")
        media_src = extract_single_media_source(driver)

        if media_src:
            print(f"✅ Media found! Source URL = {media_src}")
        else:
            print("❌ No media found on this page.")

        return media_src

    except Exception as e:
        print(f"⚠️ Error while investigating {url}: {e}")
        return None

def investigate(urls, driver, ads, brand_name):
    print("\n🚀 Starting investigation phase...")
    print(f"🧾 Total creatives to investigate: {len(urls)}")
    failed_creative_ids = set()

    for index, (creative_id, url) in enumerate(urls.items(), start=1):
        print(f"\n--------------------------------------------")
        print(f"🔢 Processing creative #{index}: ID = {creative_id}")
        print(f"🔗 Original URL: {url}")

        ad_url = investigate_page(driver, url)
        ads[creative_id] = ad_url

        if ad_url:
            print(f"📥 Added media for creative ID {creative_id}")
        else:
            print(f"⚠️ No media found for creative ID {creative_id}")
            failed_creative_ids.add(creative_id)

        # הדפסה של התקדמות כוללת
        print(f"📊 Progress: {index}/{len(urls)} creatives processed.")

        # לצורך בדיקות – עצור אחרי שלושה פריטים
        # if len(ads) == 3:
        #     print("🧪 Debug mode: stopping after 3 creatives.")
        #     break

    df = pd.DataFrame(list(failed_creative_ids), columns=["Values"])
    df.to_excel(f"{brand_name}_failed_to_download.xlsx", index=False)

    print("\n🏁 Investigation complete.")
    print(f"✅ Total creatives with media found: {sum(1 for v in ads.values() if v)} / {len(ads)}")

if __name__ == '__main__':
    pass
