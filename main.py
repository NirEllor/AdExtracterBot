from dropbox_utils import extract_report_name
from process_utils import run
from reports_utils import brands, to_failed_filename, create_reports_batch
from config import dbx

def extract_ads_batch():
    for brand in brands:
        report_name = extract_report_name(dbx, brand)
        failed_files_excel_name = to_failed_filename(report_name)
        run(report_name=report_name, failed_files_excel_name=failed_files_excel_name)

def main():
    create_reports_batch()
    extract_ads_batch()

if __name__ == '__main__':
    main()




