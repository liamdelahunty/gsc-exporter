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
*   [gsc-pages-queries.py](#gsc-pages-queries.py)
*   [key-performance-metrics.py](#key-performance-metrics)
*   [monthly-summary-report.py](#monthly-summary-report)
*   [performance-analysis.py](#performance-analysis)
*   [queries-pages-analysis.py](#queries-pages-analysis)
*   [query-position-analysis.py](#query-position-distribution-analysis)
*   [snapshot-report.py](#snapshot-report.py)
*   [generate_gsc_wrapped.py](#google-organic-wrapped-report)

---

## gsc_pages_exporter.py
---
## generate_gsc_wrapped.py

Creates a "Google Organic Wrapped"-style annual summary for a single GSC property, presenting your year in search in a fun, engaging format.

### Usage

```bash
python generate_gsc_wrapped.py <site_url> [date_range_option]
```
*   `<site_url>`: (Required) The full URL of the site property.
*   **Date Range Options**: By default, a YTD report is generated. You can use `--last-12-months` or a custom range with `--start-date` and `--end-date`.
*   **Brand Analysis Options**:
    *   `--brand-terms <term1> <term2>`: Specify brand terms directly on the command line.
    *   `--brand-terms-file <path>`: Provide a path to a text file containing brand terms (one per line).
    *   `--no-brand-detection`: Disable the brand vs. non-brand classification.

### Output

Generates a visually engaging HTML report in `output/<hostname>/` that highlights key metrics like total clicks, top pages, and busiest months.

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
## gsc-pages-queries.py

Generates a detailed, interactive HTML report showing the relationship between queries and pages. This script can either fetch live data from Google Search Console or generate a report from a previously saved CSV file, making it efficient to create different views of the same dataset.

### Usage

The script has two main modes of operation:

1.  **Download Data from GSC:**
    ```bash
    python gsc-pages-queries.py <site_url> [date_range_option] [options]
    ```

2.  **Generate Report from CSV:**
    ```bash
    python gsc-pages-queries.py --csv <path_to_file.csv> [options]
    ```

### Data Source Options

A data source is required. You must specify either `<site_url>` (positional argument), `--csv`, or use `--use-cache` with `<site_url>`.

*   `<site_url>`: The full URL of the site property (e.g., `https://www.example.com`) or a domain property (e.g., `sc-domain:example.com`). This is a positional argument.
*   `--csv <path>`: Path to an existing CSV file to use as the data source, skipping the GSC download.
*   `--use-cache`: Optional flag to use with `<site_url>`. If a CSV file from a previous run exists for the same site and date range, it will be used instead of re-downloading data.

### Other Options

*   **Date Range**: Options like `--last-7-days`, `--last-month`, `--last-12-months`, etc., are available when downloading data via `<site_url>`.
*   **Report Size**:
    *   `--report-limit <number>`: Sets the maximum number of top-level items (e.g., queries or pages) to include in the HTML report. Defaults to 250.
    *   `--sub-table-limit <number>`: Sets the maximum number of rows to display within each accordion's sub-table. Defaults to 100.
*   **Brand Analysis**:
    *   By default, the script automatically detects brand terms from the site URL and classifies queries containing them as "Brand".
    *   `--brand-terms <term1> <term2> ...`: Specify a list of custom brand terms. These are added to the auto-detected terms.
    *   `--no-brand-detection`: Disables the brand vs. non-brand classification entirely.

### Example Workflow

1.  **Initial Download:** Run a large query to get all the data you need and save it. The script will automatically classify brand/non-brand queries based on the domain name.
    ```bash
    python gsc-pages-queries.py https://www.example.com --last-12-months
    ```
    This creates a CSV file and a detailed HTML report with Non-Brand, Brand, and All Queries tabs.

2.  **Generate a Limited Report from Cache:** Now, quickly generate a smaller HTML report from the data you just saved without hitting the API again.
    ```bash
    python gsc-pages-queries.py https://www.example.com --last-12-months --use-cache --report-limit 50
    ```
    The `--use-cache` flag finds and uses the CSV from the previous step. The output is an HTML report with only the top 50 items in each tab.

### Output

Generates a CSV file (if downloading data) and an interactive HTML report.

By default, the HTML report includes automatic brand-detection and has three tabs for query analysis:
1.  **Non-Brand Queries**: An accordion list of queries that do not contain brand terms.
2.  **Brand Queries**: An accordion list of queries that contain brand terms.
3.  **All Queries**: A combined view of all queries.

It also includes the original **Pages to Queries** tab. If brand detection is disabled, the report reverts to the original two-tab format.


---

## performance-analysis.py

Fetches and compares key performance metrics (clicks, impressions, CTR, position) between two time periods. It can download live data or generate a report from a previously saved comparison CSV, making it efficient to re-run an analysis.

### Usage

1.  **Download Data from GSC:**
    ```bash
    python performance-analysis.py <site_url> [comparison_option] [filters]
    ```

2.  **Generate Report from CSV:**
    ```bash
    python performance-analysis.py --csv <path_to_comparison_file.csv>
    ```

### Data Source Options

*   `<site_url>`: The full URL of the site property. This is a positional argument, required unless `--csv` is used.
*   `--csv <path>`: Path to an existing comparison CSV file to use as the data source, skipping the GSC download.
*   `--use-cache`: Optional flag to use with `<site_url>`. If a comparison CSV from a previous run exists for the same site and date range, it will be used instead of re-downloading.

### Other Options

*   **Comparison Options**: Includes flags like `--last-28-days`, `--last-month`, and `--compare-to-previous-year`. Defaults to comparing the last full month to the month before it.
*   **Filter Options**: Includes flags like `--page-contains`, `--query-exact`, etc., to filter the data downloaded from GSC.

### Example Workflow

1.  **Initial Download:** Run a comparison to get the data you need.
    ```bash
    python performance-analysis.py https://www.example.com --last-month
    ```
    This creates a `performance-comparison-....csv` file in the `output/` directory.

2.  **Use Cache to Regenerate Report:** If you want to regenerate the HTML report from the exact same data, use the cache.
    ```bash
    python performance-analysis.py https://www.example.com --last-month --use-cache
    ```

### Output

Generates a detailed CSV file containing the merged data from both periods (if downloading) and an HTML report that highlights best/worst performing content, rising stars, and more.

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
---

## monthly-summary-report.py

Generates a concise account-wide or single-site summary of Google Search Console performance for the *last complete calendar month*. This report provides a quick overview of key metrics and counts.

### Usage

**For a single site:**
`ash
python monthly-summary-report.py <site_url>
`
*   <site_url>: The full URL of the site property (e.g., https://www.example.com) or a domain property (e.g., sc-domain:example.com).

**For all sites in your account (recommended for account-wide overview):**
`ash
python monthly-summary-report.py
`
This will generate a report for all sites you have access to, aggregating data for the last complete month.

### Output

*   **HTML Report**: A single HTML file located in output/account/ (for account-wide) or output/<hostname>/ (for single site), named monthly-summary-report-account-wide-YYYY-MM.html or monthly-summary-report-hostname-YYYY-MM.html. This report features:
    *   Clicks, Impressions, CTR, and Average Position.
    *   Unique Query and Page counts.
    *   Domains sorted alphabetically.
    *   Numbers formatted for readability (e.g., 1,234).
    *   A warning (*) if unique query or page counts might be truncated due to Google Search Console API limits, with a note explaining the truncation.
*   **CSV Report**: An accompanying CSV file with the raw data.

