
from extract import extract
from investigate import create_driver, login_if_needed, investigate
from download import download_ads


def run():

    driver = create_driver()
    login_if_needed(driver)

    urls, creative_id_set = {}, set()

    extract(urls, creative_id_set)

    ads = {}

    investigate(urls, driver, ads)  # ads passed by reference

    driver.quit()



    download_ads(ads)


