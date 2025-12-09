from dropbox_utils import extract_report_name
from process_utils import run
from reports_utils import to_failed_filename, create_reports_batch
from config import dbx
from brands import brands_list


def extract_ads_batch():
    for brand in brands_list:
        report_name = extract_report_name(dbx, brand)
        if report_name:
            failed_files_excel_name = to_failed_filename(report_name)
            run(report_name, failed_files_excel_name, brands_list)


def main():
    create_reports_batch(create_detailed_reports=False)  # For adExtractorBot
    extract_ads_batch()
    # create_reports_batch(create_detailed_reports=True)  # Not working yet!


if __name__ == '__main__':
    main()




