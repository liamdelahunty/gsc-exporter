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
*   `--last-24-hours`: Use the last 24 hours for the report.
*   `--last-7-days`: Use the last 7 days for the report.
*   `--last-28-days`: Use the last 28 days for the report.
*   `--last-month`: Use the last calendar month for the report.
*   `--last-quarter`: Use the last 3 months as the date range.
*   `--last-3-months`: Use the last 3 months as the date range.
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
You can specify a comparison period. If no option is provided, the script will default to comparing the last full calendar month to the month before it.

*   `--start-date <YYYY-MM-DD> --end-date <YYYY-MM-DD>`: Specify a custom date range.
*   `--last-24-hours`: Compares the last 24 hours to the previous 24 hours.
*   `--last-7-days`: Compares the last 7 days to the previous 7 days.
*   `--last-28-days`: Compares the last 28 days to the previous 28-day period.
*   `--last-month`: Compares the last full calendar month to the month before it.
*   `--last-quarter`: Compares the last full calendar quarter to the quarter before it.
*   `--last-3-months`: Compares the last 3 months to the previous 3-month period.
*   `--last-6-months`: Compares the last 6 months to the previous 6-month period.
*   `--last-12-months`: Compares the last 12 months to the previous 12-month period.
*   `--last-16-months`: Compares the last 16 months to the previous 16-month period.
*   `--compare-to-previous-year`: When used with another date range flag, this compares the selected period to the same period in the previous year.

### Examples

**Analyze performance over the last month (default):**
```bash
python performance-analysis.py https://www.example.com
```

**Analyze performance of the last 28 days vs. the previous 28 days:**
```bash
python performance-analysis.py https://www.example.com --last-28-days
```

**Analyze performance of the last full quarter vs. the previous quarter:**
```bash
python performance-analysis.py sc-domain:example.com --last-quarter
```

**Analyze year-over-year performance for the last month:**
```bash
python performance-analysis.py https://www.example.com --last-month --compare-to-previous-year
```
This will compare performance data from the last full calendar month against the same month from the previous year.

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

---

## Performance Snapshot

The `snapshot-report.py` script provides a single-period overview of your Google Search Console performance data. It fetches key metrics (clicks, impressions, CTR, average position) for a specified date range and presents various observations to help you understand your site's organic search presence.

### Usage

Run the script from the command line, providing the site URL and a date range option.

```bash
python snapshot-report.py <site_url> [date_range_option]
```

*   `<site_url>`: (Required) The full URL of the site property (e.g., `https://www.example.com`) or a domain property (e.g., `sc-domain:example.com`).

### Date Range Options
You can specify a date range using one of the following options. If no option is provided, the script will default to the last calendar month.

*   `--start-date <YYYY-MM-DD> --end-date <YYYY-MM-DD>`: Specify a custom date range.
*   `--last-24-hours`: Use the last 24 hours for the report.
*   `--last-7-days`: Use the last 7 days for the report.
*   `--last-28-days`: Use the last 28 days for the report.
*   `--last-month`: Use the last calendar month for the report.
*   `--last-quarter`: Use the last 3 months for the report.
*   `--last-3-months`: Use the last 3 months for the report.
*   `--last-6-months`: Use the last 6 months for the report.
*   `--last-12-months`: Use the last 12 months for the report.
*   `--last-16-months`: Use the last 16 months for the report (the maximum allowed by the API).

These options are mutually exclusive.

### Examples

**Generate a snapshot for the last month (default):**
```bash
python snapshot-report.py https://www.example.com
```

**Generate a snapshot for the last 7 days:**
```bash
python snapshot-report.py https://www.example.com --last-7-days
```

**Generate a snapshot for the last 12 months:**
```bash
python snapshot-report.py sc-domain:example.com --last-12-months
```

### Output
The script generates two files in the `output/<hostname>` directory:

1.  **`snapshot-pages-[...].csv`**: A detailed CSV file containing the performance data for all pages, including clicks, impressions, CTR, and average position, for the specified period.
2.  **`snapshot-report-[...].html`**: An HTML report that provides an overview of the analysis, with tables for:
    *   Top Pages by Clicks
    *   Top Pages by Impressions
    *   High Impressions, Low CTR Opportunities
    *   Performance by Device
    *   Performance by Country

The HTML report also contains a link in the footer to a detailed guide on how to interpret the data, located at `resources/how-to-read-the-snapshot-report.html`.

---

## Account-Wide Analysis

The `account-wide-analysis.py` script provides a comprehensive overview of your Google Search Console performance across all properties in your account. It fetches key performance metrics (clicks, impressions, CTR, average position) for each complete calendar month over the last 16 months for every site you have access to.

### Usage

Run the script from the command line:

```bash
python account-wide-analysis.py
```

### Output

The script generates two files in the `output/` directory:

1.  **`account-wide-performance-[...].csv`**: A CSV file containing the monthly performance data for all sites.
2.  **`account-wide-performance-[...].html`**: An HTML report that summarises the monthly performance data for all sites.

The HTML report is structured to provide an easy-to-navigate overview:

*   **Interactive Index**: At the top of the report, an index lists all analysed sites. Each entry is a clickable link that navigates directly to the corresponding site's data section.
*   **Structured by Site**: The main data sections are separated for each site, rather than presented as one large table.
*   **Intelligent Sorting**: Both the index and the individual site sections are sorted according to the following hierarchy:
    1.  **Primary Sort**: Alphabetical order based on the root domain (e.g., `croneri.co.uk`).
    2.  **Secondary Sort**: Within each root domain, properties are sorted by subdomain with special prioritisation:
        *   `sc-domain:` properties are listed first.
        *   `www.` versions of the root domain are listed second.
        *   All other subdomains are listed alphabetically.

