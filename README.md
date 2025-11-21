# Google Search Console Exporter Scripts

This repository contains a collection of Python scripts designed to connect to the Google Search Console (GSC) API, retrieve performance data, and export it into user-friendly formats like CSV and HTML reports.

## Setup

### 1. Google Cloud Project & API Credentials

Before you can use these scripts, you need to enable the Google Search Console API and obtain credentials.

1.  **Create a Google Cloud Project:**
    *   Go to the [Google Cloud Console](https://console.cloud.google.com/).
    *   Create a new project or use an existing one.

2.  **Enable the Google Search Console API:**
    *   In your project, go to "APIs & Services" > "Library".
    *   Search for "Google Search Console API" and enable it.

3.  **Create OAuth 2.0 Credentials:**
    *   Go to "APIs & Services" > "Credentials".
    *   Click "Create Credentials" and choose "OAuth client ID".
    *   If prompted, configure the consent screen. For "User Type," select "External" if you're using a personal Google account, and fill in the required app information. Add your email to the "Test users" section.
    *   For the "Application type," select "Desktop app".
    *   Click "Create." A window will appear with your client ID and client secret.
    *   Click the "Download JSON" button to download your credentials.
    *   **Rename the downloaded file to `client_secret.json` and place it in the root directory of this project.**

### 2. Install Dependencies

Install the necessary Python libraries using pip:

```bash
pip install -r requirements.txt
```

### First-Time Authorization
The first time you run any of these scripts, a new tab will open in your web browser, asking for your consent to access your GSC data. After you approve, the script will create a `token.json` file to store your authorization, so you won't have to re-authorize on subsequent runs.

---

## Available Scripts

This suite includes several scripts for different types of analysis:

*   [gsc_pages_exporter.py](#gsc-pages-exporter)
*   [performance-analysis.py](#performance-analysis)
*   [snapshot-report.py](#performance-snapshot)
*   [key-performance-metrics.py](#key-performance-metrics)
*   [queries-pages-analysis.py](#queries-pages-analysis)
*   [query-position-analysis.py](#query-position-distribution-analysis)

---

## gsc_pages_exporter.py

Exports all known pages from a GSC property for a given date range.

### Usage

```bash
python gsc_pages_exporter.py <site_url> [date_range_option]
```

*   `<site_url>`: (Required) The full URL of the site property (e.g., `https://www.example.com`) or a domain property (e.g., `sc-domain:example.com`).

*   **Date Range Options**: Options like `--last-7-days`, `--last-month`, `--start-date YYYY-MM-DD`, etc., are available. If omitted, it defaults to the last full month.

### Output

Generates a CSV and an HTML file containing a list of all URLs found in the specified period, saved to the `output/<hostname>/` directory.

---

## performance-analysis.py

Fetches and compares key performance metrics (clicks, impressions, CTR, position) between two time periods to identify trends and optimization opportunities.

### Usage

```bash
python performance-analysis.py <site_url> [comparison_option]
```

*   `<site_url>`: (Required) The full URL of the site property or a domain property.
*   **Comparison Options**: Includes flags like `--last-28-days`, `--last-month`, and `--compare-to-previous-year`. Defaults to comparing the last full month to the month before it.

### Output

Generates a detailed CSV file and an HTML report in `output/<hostname>/`. The report highlights best/worst performing content, rising stars, and more.

---

## snapshot-report.py

Provides a single-period overview of your GSC performance, presenting various observations to help you understand your site's organic search presence.

### Usage

```bash
python snapshot-report.py <site_url> [date_range_option]
```

*   `<site_url>`: (Required) The full URL of the site property or a domain property.
*   **Date Range Options**: Similar to other scripts, allows specifying periods like `--last-7-days`, `--last-month`, etc. Defaults to the last calendar month.

### Output

Generates a CSV with detailed page data and an HTML report in `output/<hostname>/`. The report includes top pages, performance by device/country, and optimization opportunities.

---

## key-performance-metrics.py

Provides a monthly overview of key performance metrics (clicks, impressions, CTR, average position). This script can run for a single specified site or for all properties in your GSC account.

### Usage

**For a single site:**
```bash
python key-performance-metrics.py <site_url>
```
*   `<site_url>`: The full URL of the site property or a domain property.

**For all sites in your account:**
```bash
python key-performance-metrics.py
```

### Output

*   **Single Site**: Generates a CSV and an HTML file in `output/<hostname>/` showing monthly performance over the last 16 months.
*   **All Sites**: Generates `output/account/` with a CSV and a comprehensive HTML report. The report includes an interactive index and intelligently sorts sites by root domain and subdomain type for easy navigation.

---

## queries-pages-analysis.py

Extends the `key-performance-metrics` script by also fetching the number of unique queries and pages for each month.

### Usage

**For a single site:**
```bash
python queries-pages-analysis.py <site_url>
```

**For all sites in your account:**
```bash
python queries-pages-analysis.py
```

### Output

*   **Single Site**: Generates a CSV and an HTML file in `output/<hostname>/` with monthly data including unique query and page counts.
*   **All Sites**: Generates corresponding files in `output/account/` for an account-wide overview.

---

## query-position-analysis.py

Focuses on the distribution of query positions, breaking down clicks and impressions into predefined ranking buckets (1-3, 4-10, 11-20, 21+) for a more granular view of search visibility.

### Usage

**For a single site:**
```bash
python query-position-analysis.py <site_url>
```

**For all sites in your account:**
```bash
python query-position-analysis.py
```

### Output

*   **Single Site**: Generates a CSV and an HTML file in `output/<hostname>/` detailing the monthly query position distribution.
*   **All Sites**: Generates `output/account/` with a CSV and an HTML report providing an account-wide breakdown.