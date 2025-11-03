import pandas as pd

from extract import extract
from investigate import create_driver, login_if_needed, investigate
from download import download_ads

excel_path = "booking_com_2024_1696090.xlsx"
sheet_name = "Report"


def run():

    driver = create_driver()
    login_if_needed(driver)

    urls, creative_id_set = {}, set()

    extract(urls, creative_id_set, excel_path, sheet_name)

    ads = {}

    investigate(urls, driver, ads)  # ads passed by reference

    df = pd.DataFrame(list(ads.items()), columns=["Creative_ID", "URL"])

    # שמור כקובץ אקסל
    df.to_excel(fr"C:\עוזר מחקר\AdExtracterBot\mapping_{excel_path}.xlsx", index=False)

    driver.quit()



    # download_ads(ads)


if __name__ == '__main__':
    run()

