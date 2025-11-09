import os
import pickle
import time
from selenium import webdriver
from selenium.common import TimeoutException, NoSuchElementException, StaleElementReferenceException
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from dotenv import load_dotenv
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager


CHROMEDRIVER_PATH = r"C:\Users\Nir\PycharmProjects\AdExtracterBot\chromedriver.exe"
COOKIES_FILE = "cookies.pkl"
LOGIN_URL = "https://app.vivvix.com/360/"

load_dotenv()

USERNAME = os.getenv("APP_USERNAME")
PASSWORD = os.getenv("APP_PASSWORD")
if not USERNAME or not PASSWORD:
    raise RuntimeError("Missing credentials: set APP_USERNAME and APP_PASSWORD in env")


def create_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    # chrome_options.add_argument("--start-maximized")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    return driver


def login_if_needed(driver):
    driver.get(LOGIN_URL)
    time.sleep(2)

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
        
        def find_visible_input(by, value):
            elements = driver.find_elements(by, value)
            for el in elements:
                if el.is_displayed():
                    return el
            return None

        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'form[name="cognitoSignInForm"]')))
        time.sleep(5)

        username_input = None
        password_input = None
        for _ in range(10):
            username_input = find_visible_input(By.ID, "signInFormUsername")
            password_input = find_visible_input(By.ID, "signInFormPassword")
            if username_input and password_input:
                break
            time.sleep(1)

        if not username_input or not password_input:
            raise RuntimeError("Couldn't locate visible username/password fields")

        driver.execute_script("arguments[0].scrollIntoView(true);", username_input)
        time.sleep(1)
        username_input.clear()
        username_input.send_keys(USERNAME)
        password_input.clear()
        password_input.send_keys(PASSWORD)

        login_button = find_visible_input(By.NAME, "signInSubmitButton")
        if not login_button:
            raise RuntimeError("Couldn't locate visible submit button")
        driver.execute_script("arguments[0].scrollIntoView(true);", login_button)
        time.sleep(1)
        login_button.click()

        wait.until(lambda d: "login" not in d.current_url.lower())

        pickle.dump(driver.get_cookies(), open(COOKIES_FILE, "wb"))
        print("✅ התחברות בוצעה בהצלחה וה-cookies נשמרו.")
    except Exception as e:
        print("❌ שגיאה בהתחברות:", e)




def extract_single_media_source(driver, retries=1):
    for attempt in range(1, retries + 1):
        print(f"🔁 ניסיון {attempt} מתוך {retries}")
        src = _extract_once(driver)
        if src:
            return src
        time.sleep(5)
    return None

def _extract_once(driver):
    return find_video_source(driver) or find_image_source(driver)




def find_video_source(driver):
    wait = WebDriverWait(driver, 10)
    try:
        # קודם נחפש תגי video ישירות
        videos = driver.find_elements(By.TAG_NAME, "video")
        for v in videos:
            try:
                src = v.get_attribute("src") or v.find_element(By.TAG_NAME, "source").get_attribute("src")
                if src and src.startswith("http"):
                    print(f"🎥 נמצא וידאו: {src}")
                    return src
            except NoSuchElementException:
                continue
            except StaleElementReferenceException:
                time.sleep(1)
                videos = driver.find_element(By.TAG_NAME, "video")

        # fallback – div עם id="video"
        video_div = wait.until(EC.presence_of_element_located((By.ID, "video")))
        source = video_div.find_element(By.TAG_NAME, "source")
        src = source.get_attribute("src")
        if src:
            print(f"🎥 נמצא וידאו (div): {src}")
            return src

    except TimeoutException:
        print("⏱️ לא נמצא וידאו בזמן שהוקצב")
    except Exception as e:
        print(f"⚠️ שגיאה בזמן חיפוש וידאו: {e}")
    return None


def find_image_source(driver, max_retries=2):
    wait = WebDriverWait(driver, 10)
    image_selectors = [
        "img[src*='vivvix']",
        "img[src*='CreativeViewer.axd']",
        "img[src*='CreativeByCollectionID']",
    ]


    for selector in image_selectors:
        for attempt in range(1, max_retries + 1):
            try:
                img = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, selector)))
                src = img.get_attribute("src")
                if src and src.startswith("http"):
                    print(f"🖼️ נמצאה תמונה ({selector}) בניסיון {attempt}: {src}")
                    return src
                break

            except TimeoutException:
                if attempt == max_retries:
                    print(f"⏱️ לא נמצא אלמנט לפי {selector} אחרי {max_retries} ניסיונות.")
                continue

            except StaleElementReferenceException:
                print(f"🔁 אלמנט התחלף (stale) — מנסה שוב ({attempt}/{max_retries}) עבור {selector}...")
                time.sleep(1)
                continue

            except Exception as e:
                print(f"⚠️ שגיאה בזמן חיפוש לפי {selector} (ניסיון {attempt}): {e}")
                break

    print("⚠️ לא נמצאה אף תמונה תואמת.")
    return None


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


def investigate(urls, driver, ads, brand_name, max_workers=1):

    print(f"\n🚀 Starting investigation phase for '{brand_name}'...")
    print(f"🧾 Total creatives to investigate: {len(urls)}")

    failed_creative_ids = set()

    def process_creative(c_id, url):
        ad_creative_url = investigate_page(driver, url)
        return c_id, ad_creative_url

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(process_creative, cid, url): cid
            for cid, url in urls.items()
        }

        completed = 0
        for future in as_completed(futures):
            creative_id = futures[future]
            try:
                cid, ad_url = future.result()
                ads[cid] = ad_url
                completed += 1

                if ad_url:
                    print(f"✅ [{completed}/{len(urls)}] Found media for {cid}")
                else:
                    print(f"⚠️ [{completed}/{len(urls)}] No media for {cid}")
                    failed_creative_ids.add(cid)

            except Exception as e:
                print(f"❌ Error in creative {creative_id}: {e}")
                failed_creative_ids.add(creative_id)

    if failed_creative_ids:
        df = pd.DataFrame(list(failed_creative_ids), columns=["Values"])
        df.to_excel(f"{brand_name}_failed_to_download.xlsx", index=False)
        print(f"🧾 Saved {len(failed_creative_ids)} failed IDs to Excel.")

    print(f"\n🏁 Investigation complete for '{brand_name}'.")
    print(f"✅ Total creatives with media found: "
          f"{sum(1 for v in ads.values() if v)} / {len(urls)}")

if __name__ == '__main__':
    pass
