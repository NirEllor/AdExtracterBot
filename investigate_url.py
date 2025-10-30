from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
import time

chrome_options = Options()
chrome_options.add_argument("--start-maximized")

service = Service("C:\chromedriver-win64\chromedriver.exe")
driver = webdriver.Chrome(service=service, options=chrome_options)



def investigate(url):
    try:

        driver.get(url)
        time.sleep(3)
        login_button = driver.find_element(By.CLASS_NAME, "signin")
        login_button.click()

        username_input = driver.find_element(By.ID, "signInFormUsername")
        password_input = driver.find_element(By.ID, "signInFormPassword")

        username_input.send_keys(username)
        password_input.send_keys(password)




    except Exception as e:
        print(e)

    finally:
        time.sleep(3)
        driver.quit()

