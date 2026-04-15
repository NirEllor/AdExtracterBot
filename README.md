# AdExtracterBot

> **Automated ad media extraction pipeline — from Vivvix reports to AWS S3**

---

## Overview

AdExtracterBot is a fully automated pipeline that ingests advertising creative reports from Vivvix, resolves each ad's media source URL using a headless browser, and uploads the resulting images and videos to Amazon S3. It is designed to process multiple brands in batch, retry failed downloads intelligently, and integrate seamlessly with Dropbox as the file-exchange layer between report generation and media extraction.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          PHASE 1 — Report Creation (optional)           │
│                                                                         │
│   brands.xlsx  ──►  Vivvix API  ──►  Excel Report  ──►  Dropbox        │
└────────────────────────────────────────────┬────────────────────────────┘
                                             │
                                             ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                          PHASE 2 — Ad Extraction (main)                 │
│                                                                         │
│   Dropbox Excel ──► URL Parsing ──► Selenium Investigation ──► S3      │
│                                                                         │
│   On failure: filter Excel ──► re-upload to Dropbox ──► retry (x5)     │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Full Pipeline Walkthrough

### Step 1 — Report Creation (`reports_utils.py`)

> This step is optional and only needed when you do not already have Excel reports in Dropbox.

1. A headless Chrome browser authenticates with `app.vivvix.com/360/` using Selenium and persists session cookies to `cookies.pkl`.
2. For each brand in `brands.xlsx`, the Vivvix Entity Search API finds the matching entity ID.
3. A report spec is created, updated, saved, and triggered via the Vivvix Custom Reporting API.
4. The bot polls `GetReportListData` until every submitted report reaches **Status = 2** (complete).
5. Completed Excel reports are downloaded and uploaded to the configured Dropbox import folder.

Modes available:
| Mode | `create_detailed_reports` | Date range |
|------|--------------------------|------------|
| Non-detailed (yearly) | `False` | Full year |
| Detailed (weekly) | `True` | Weekly breakdown |

---

### Step 2 — Brand Iteration (`main.py`)

`extract_ads_batch()` iterates over every brand in `brands_list` (defined in `brands.py`). For each brand it:

1. Calls `extract_report_name()` to find the matching `.xlsx` file in Dropbox.
2. Resolves the failed-files Excel name using `to_failed_filename()`.
3. Hands off to `run()` in `process_utils.py`.

---

### Step 3 — Retry Loop (`process_utils.py → run()`)

The loop runs up to **5 attempts** per brand:

| Attempt | Behaviour |
|---------|-----------|
| 1 | Full run on the original Excel report |
| 2+ | Downloads the original report, filters it to **only failed creative IDs**, re-uploads to Dropbox, then re-runs |

Each attempt calls `process_single_run()`, which orchestrates:

```
init_driver_session()
  └── download_report_locally()
        └── process_ads_from_excel()
              ├── extract_urls_from_excel()      # parse HYPERLINK formulas
              ├── investigate_ads_and_collect()   # Selenium media discovery
              └── download_media_assets()         # HTTP fetch + S3 upload
  └── cleanup_temp_file()
  └── driver.quit()
```

---

### Step 4 — Excel Parsing (`excel_utils.py`)

The report Excel is opened with `openpyxl` to preserve formula values. Column A contains `=HYPERLINK(...)` formulas; column B contains the **MASTER CREATIVE ID**.

- Formulas are extracted with a regex: `=HYPERLINK\("([^"]+)"`.
- Rows marked **CREATIVE UNKNOWN** are skipped.
- On retry runs, hidden rows (already-succeeded creatives) are excluded via `row_dimensions`.

---

### Step 5 — Media Investigation (`browser_investigate.py`)

For each creative URL a shared Selenium driver navigates to the page and attempts media extraction in this order:

1. **Direct `<video>` tags** — checks `src` attribute and child `<source>` elements.
2. **`<div id="video">` fallback** — for embedded players.
3. **Image selectors** — tries a prioritized list of CSS selectors targeting known Vivvix image patterns.

Failed creative IDs are written to `{brand_name}_failed_to_download.xlsx` for retry filtering.

> `NUM_WORKERS = 1` — do not increase without explicit approval; the Vivvix session is not thread-safe.

---

### Step 6 — Media Download and S3 Upload (`browser_download.py`)

Downloads are parallelized with **20 workers** via `ThreadPoolExecutor`. Each creative:

1. `GET` request with a standard browser `User-Agent`.
2. If the response is `text/html`, the inner `<img src>` is extracted and re-fetched.
3. Content type determines the subdirectory (`images/`, `videos/`, or `other/`).
4. The file is streamed into a `BytesIO` buffer and uploaded to S3:

```
s3://ad-extracter-bot-bucket/{brand_name}/{images|videos|other}/{creative_id}.{ext}
```

Files with a `.bin` extension (unknown type) are flagged as failed.

---

## Project Structure

```
AdExtracterBot/
├── main.py                          # Entry point — batch loop over brands
├── config.py                        # Env var loading, Dropbox client init
├── brands.py                        # List of brand names to process
├── process_utils.py                 # Orchestration, retry loop
├── browser_investigate.py           # Selenium login + media URL discovery
├── browser_download.py              # HTTP download + S3 upload
├── dropbox_utils.py                 # Dropbox file listing and download
├── excel_utils.py                   # Excel URL parsing and failure filtering
├── reports_utils.py                 # Vivvix report creation and download
├── headers.json                     # HTTP headers template for Vivvix API calls
├── search_payload.json              # Vivvix entity search payload template
├── detailed_reports_payload.json    # Payload template for detailed reports
├── non_detailed_reports_payload.json# Payload template for non-detailed reports
└── requirements.txt                 # Python dependencies
```

---

## Environment Variables

Create a `.env` file in the project root with the following keys:

```dotenv
# Dropbox OAuth2
DROPBOX_REFRESH_TOKEN=your_refresh_token
DROPBOX_APP_KEY=your_app_key
DROPBOX_APP_SECRET=your_app_secret

# Dropbox folder paths
DROPBOX_NON_DETAILED_REPORTS_PATH=/path/to/non_detailed_reports
DROPBOX_DETAILED_REPORTS_PATH=/path/to/detailed_reports
DROPBOX_UPLOAD_FOLDER_PATH=/path/to/upload_folder

# Vivvix credentials
APP_USERNAME=your_vivvix_email
APP_PASSWORD=your_vivvix_password
```

AWS credentials must be configured separately (via `~/.aws/credentials` or environment variables `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY`).

---

## Installation

```bash
# 1. Clone the repository
git clone <repo-url>
cd AdExtracterBot

# 2. Create and activate a virtual environment
python -m venv venv
venv\Scripts\activate      # Windows
# source venv/bin/activate  # macOS / Linux

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env
# Fill in all values in .env
```

---

## Running the Bot

### Run the full ad extraction pipeline

```bash
python main.py
```

This runs `extract_ads_batch()`, which processes every brand in `brands.py`.

### Generate Vivvix reports first (optional)

Uncomment the relevant line in `main()` inside `main.py`:

```python
def main():
    create_reports_batch(create_detailed_reports=False)  # Non-detailed (yearly)
    # create_reports_batch(create_detailed_reports=True)   # Detailed (weekly)
    extract_ads_batch()
```

---

## Key Configuration Constants

| Constant | Location | Default | Purpose |
|----------|----------|---------|---------|
| `MAX_RUNS` | `process_utils.py` | `5` | Maximum retry attempts per brand |
| `NUM_WORKERS` | `browser_investigate.py` | `1` | Selenium concurrency — do not change |
| `S3_BUCKET` | `browser_download.py` | `ad-extracter-bot-bucket` | Target S3 bucket |
| `PLACE_FOR_FILES` | `process_utils.py` | `C:\Vivix_Media_Files` | Local temp directory |
| `TOO_MUCH_TIME` | `browser_investigate.py` | `7200s (2h)` | Cookie expiry threshold |
| `SHEET_NAME` | `process_utils.py` | `Report` | Excel sheet to parse |

---

## Retry Logic — How Filtering Works

After each failed attempt, `apply_post_attempt_filtering()` in `excel_utils.py`:

1. Downloads the original report from Dropbox.
2. Opens it with `openpyxl` to preserve `=HYPERLINK(...)` formulas.
3. Keeps only rows whose **MASTER CREATIVE ID** appears in the failed-IDs Excel.
4. Overwrites the Dropbox file with the filtered version.
5. The next attempt then processes only the remaining failures.

Row-skipping logic differs between the raw report (headers on row 8, data from row 9) and already-filtered files (headers on row 1, data from row 2).

---

## Dependencies

| Package | Purpose |
|---------|---------|
| `selenium` | Headless Chrome automation |
| `webdriver-manager` | Automatic ChromeDriver management |
| `dropbox` | Dropbox API client |
| `boto3` | AWS S3 client |
| `pandas` | DataFrame operations on Excel data |
| `openpyxl` | Formula-preserving Excel read/write |
| `requests` | HTTP media downloads and Vivvix API calls |
| `python-dotenv` | `.env` file loading |
| `urllib3` | HTTP utilities (SSL warning suppression) |

---

## Notes

- **Session cookies** are cached in `cookies.pkl` and reused for up to 2 hours before a fresh login is triggered.
- Vivvix reports with over 100,000 rows are returned as CSV-only by Vivvix; these are logged and skipped gracefully.
- The S3 bucket name is hardcoded in `browser_download.py` — update it before first use.
- `brands.py` contains an empty `brands_list` by default; populate it before running.
