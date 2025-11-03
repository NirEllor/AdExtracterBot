import os
import pickle
import time
from urllib.parse import urljoin
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from dotenv import load_dotenv


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
    chrome_options.add_argument("--start-maximized")
    # chrome_options.add_argument("--headless=new")  # לבוט ללא חלון גרפי
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
            time.sleep(2)
            print("✅ Cookies loaded — כנראה כבר מחובר.")
            return
        except Exception as e:
            print("⚠️ בעיה בטעינת cookies:", e)

    print("🔐 מבצע התחברות ראשונה...")
    wait = WebDriverWait(driver, 25)
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
        time.sleep(1)

        username_input = None
        password_input = None
        for _ in range(10):  # retry a few times for dynamic layouts
            username_input = find_visible_input(By.ID, "signInFormUsername")
            password_input = find_visible_input(By.ID, "signInFormPassword")
            if username_input and password_input:
                break
            time.sleep(0.5)

        if not username_input or not password_input:
            raise RuntimeError("Couldn't locate visible username/password fields")

        # Scroll into view and fill credentials
        driver.execute_script("arguments[0].scrollIntoView(true);", username_input)
        time.sleep(0.3)
        username_input.clear()
        username_input.send_keys(USERNAME)
        password_input.clear()
        password_input.send_keys(PASSWORD)

        # Find and click visible submit button
        login_button = find_visible_input(By.NAME, "signInSubmitButton")
        if not login_button:
            raise RuntimeError("Couldn't locate visible submit button")
        driver.execute_script("arguments[0].scrollIntoView(true);", login_button)
        time.sleep(0.3)
        login_button.click()

        # Wait for redirect after successful login
        wait.until(lambda d: "login" not in d.current_url.lower())

        # Save cookies for reuse
        pickle.dump(driver.get_cookies(), open(COOKIES_FILE, "wb"))
        print("✅ התחברות בוצעה בהצלחה וה-cookies נשמרו.")
    except Exception as e:
        print("❌ שגיאה בהתחברות:", e)


# === חילוץ קישור המדיה מתוך source שנמצא תחת img/video ===
def extract_single_media_source(driver):
    base_url = driver.current_url

    # בדוק <img> → <source>
    for img in driver.find_elements(By.TAG_NAME, "img"):
        for s in img.find_elements(By.TAG_NAME, "source"):
            src = s.get_attribute("src")
            if src:
                absolute = urljoin(base_url, src)
                print(f"🖼️ נמצא source בתוך <img>: {absolute}")
                return absolute

    # בדוק <video> → <source>
    for video in driver.find_elements(By.TAG_NAME, "video"):
        for s in video.find_elements(By.TAG_NAME, "source"):
            src = s.get_attribute("src")
            if src:
                absolute = urljoin(base_url, src)
                print(f"🎥 נמצא source בתוך <video>: {absolute}")
                return absolute

    print("⚠️ לא נמצא אלמנט source עם src")
    return None


# === ביקור בעמוד ובדיקת המדיה ===
def investigate_page(driver, url):
    time.sleep(3)
    try:
        driver.get(url)
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        print(f"🔎 Visiting {url}")

        media_src = extract_single_media_source(driver)
        if media_src:
            print(f"✅ Success! URL = {media_src}")
        else:
            print("❌ No media found.")
        return media_src

    except Exception as e:
        print(f"⚠️ שגיאה בכניסה ל-{url}: {e}")
        return None

def investigate(urls, driver, ads):
    for creative_id, url in urls.items():
        ad_url = investigate_page(driver, url)
        ads[creative_id] = ad_url


if __name__ == '__main__':
    pass
