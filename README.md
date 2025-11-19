# Google Search Console Page Exporter

This script connects to the Google Search Console API, retrieves a list of all known pages for a specified domain, and exports them to a CSV file.

## Setup

### 1. Google Cloud Project & API Credentials

Before you can use this script, you need to enable the Google Search Console API and get credentials.

1.  **Create a Google Cloud Project:**
    *   Go to the [Google Cloud Console](https://console.cloud.google.com/).
    *   Create a new project (or use an existing one).

2.  **Enable the Google Search Console API:**
    *   In your project, go to the "APIs & Services" > "Library".
    *   Search for "Google Search Console API" and enable it.

3.  **Create OAuth 2.0 Credentials:**
    *   Go to "APIs & Services" > "Credentials".
    *   Click "Create Credentials" and choose "OAuth client ID".
    *   If prompted, configure the consent screen. For "User Type", select "External" if you're using a personal Google account, and fill in the required app information. Add your email to the "Test users" section.
    *   For the "Application type", select "Desktop app".
    *   Click "Create". A window will appear with your client ID and client secret.
    *   Click the "Download JSON" button to download your credentials.
    *   **Rename the downloaded file to `client_secret.json` and place it in the same directory as the script.**

### 2. Install Dependencies

Install the necessary Python libraries using pip:

```bash
pip install -r requirements.txt
```

## Usage

Run the script from the command line, providing the site URL and an optional date range.

```bash
python gsc_pages_exporter.py <site_url> [date_range_option]
```

*   `<site_url>`: (Required) The full URL of the site property (e.g., `https://www.example.com`) or a domain property (e.g., `sc-domain:example.com`).

### Date Range Options
You can specify a date range using one of the following options. If no option is provided, the script will default to the previous full calendar month.

*   `--start-date <YYYY-MM-DD> --end-date <YYYY-MM-DD>`: Specify a custom date range.
*   `--last-quarter`: Use the last 3 months as the date range.
*   `--last-6-months`: Use the last 6 months as the date range.
*   `--last-12-months`: Use the last 12 months as the date range.
*   `--last-16-months`: Use the last 16 months as the date range (the maximum allowed by the API).

These options are mutually exclusive.

### Examples

**Export pages for the previous month (default):**
```bash
python gsc_pages_exporter.py https://www.example.com
```

**Export pages for a specific date range:**
```bash
python gsc_pages_exporter.py https://www.example.com --start-date 2025-01-01 --end-date 2025-01-31
```

**Export pages for the last quarter:**
```bash
python gsc_pages_exporter.py https://www.example.com --last-quarter
```

**Export pages for the last 12 months:**
```bash
python gsc_pages_exporter.py https://www.example.com --last-12-months
```

### First-Time Authorization
*   The first time you run the script, it will open a new tab in your web browser to ask for your consent to access your Google Search Console data.
*   After you approve, the script will create a `token.json` file to store your authorization, so you won't have to re-authorize every time.

### Output
The script will create two files in the `output/<hostname>` directory:
1.  A CSV file with all the URLs.
2.  An HTML file with a clickable list of all the URLs.

---

## Performance Analysis

The `performance-analysis.py` script extends the functionality by fetching and comparing key performance metrics (clicks, impressions, CTR, position) between two time periods. It's designed to help you quickly identify content that has changed in performance, as well as find new optimization opportunities.

### Usage

Run the script from the command line, providing the site URL and a comparison flag.

```bash
python performance-analysis.py <site_url> [comparison_option]
```

*   `<site_url>`: (Required) The full URL of the site property (e.g., `https://www.example.com`) or a domain property (e.g., `sc-domain:example.com`).

### Comparison Options
You must specify a comparison period. These options determine the two date ranges the script will analyze.

*   `--compare-last-28-days`: (Default) Compares the most recent 28 days to the 28 days prior.
*   `--compare-last-month`: Compares the last full calendar month to the month before it.
*   `--compare-last-quarter`: Compares the last full calendar quarter to the quarter before it.

If no option is provided, the script will default to `--compare-last-28-days`.

### Examples

**Analyze performance over the last 28 days (default):**
```bash
python performance-analysis.py https://www.example.com
```

**Analyze performance of the last full month vs. the previous month:**
```bash
python performance-analysis.py https://www.example.com --compare-last-month
```

**Analyze performance of the last full quarter vs. the previous quarter:**
```bash
python performance-analysis.py sc-domain:example.com --compare-last-quarter
```

### Output
The script generates two files in the `output/<hostname>` directory:

1.  **`performance-comparison-[...].csv`**: A detailed CSV file containing the merged performance data for all pages across both periods, including calculated deltas for each metric.
2.  **`performance-report-[...].html`**: An HTML report that provides a summary of the analysis, with tables for:
    *   Best Performing Content (by change in clicks)
    *   Worst Performing Content (by change in clicks)
    *   Rising Stars (newly visible pages)
    *   Falling Stars (pages with a dramatic drop in traffic)
    *   High Impressions, Low CTR Opportunities

The HTML report also contains a link in the footer to a detailed guide on how to interpret the data, located at `resources/how-to-read-the-performance-analysis-report.html`.
