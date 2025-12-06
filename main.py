from dropbox_utils import extract_report_name
from process_utils import run
from reports_utils import brands
from config import dbx



def main():
    for brand in brands:
        report_name = extract_report_name(dbx, brand)
        failed_files_excel_name = f"{brand}_failed_to_download.xlsx"
        run(report_name=report_name, failed_files_excel_name=failed_files_excel_name)


if __name__ == '__main__':
    main()




