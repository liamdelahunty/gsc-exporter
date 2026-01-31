# Google Search Console Exporter Scripts

This repository contains a collection of Python scripts designed to connect to the Google Search Console (GSC) API, retrieve performance data, and export it into user-friendly formats like CSV and HTML reports.

## Scripts at a Glance

| Script | Description |
| --- | --- |
| `key-performance-metrics.py` | Fetches a high-level, 16-month overview of Clicks, Impressions, CTR, and Position. Ideal for a quick health check. |
| `monthly-summary-report.py` | Provides a detailed summary for the last complete month, including unique query and page counts. |
| `snapshot-report.py` | Gives a detailed snapshot for a single period, breaking data down by device and country. |
| `performance-analysis.py` | Compares two time periods (e.g., month-over-month) to find performance changes, rising stars, and content decay. |
| `queries-pages-analysis.py` | Extends `key-performance-metrics` by adding unique query and page counts to the 16-month view. |
| `query-position-analysis.py` | Tracks the distribution of query ranking positions over 16 months, with charts to visualize the trends. |
| `query-segmentation-report.py` | Groups top 50 queries into position buckets (1-3, 4-10, etc.) to identify high-performance keywords at different ranking levels. Includes summary charts for clicks, impressions, CTR, and query count distribution. |
| `gsc-pages-queries.py` | Generates a detailed, interactive report to explore the relationship between specific queries and the pages they lead to. |
| `page-level-report.py` | Generates a page-level report including clicks, impressions, CTR, position, and unique query counts for each URL. |
| `gsc_pages_exporter.py` | Exports a simple, bulk list of all pages discovered within a given date range. |
| `generate_gsc_wrapped.py` | Creates a fun, "Spotify Wrapped"-style annual summary of your site's GSC performance. |
| `run_for_sites.py` | A utility script to run any of the above analysis scripts for a custom list of sites. |
| `run_all_reports_for_site.py` | A composite script to run all primary, monthly useful analysis reports for a single domain. |
| `run_wrapped_for_all_properties.py` | A utility script to automate running the `generate_gsc_wrapped.py` script for every site you have access to. |

### A Note on Date-Related Flags

All date-related flags like `--last-7-days`, `--last-28-days`, and `--last-month` are dynamic. They calculate date ranges based on the **latest date for which data is available** in Google Search Console, not based on today's calendar date. This accounts for GSC's typical data processing delay.


## Typical Workflow

Here is a recommended workflow for analyzing your GSC data, moving from a high-level overview to a detailed investigation.

### 1. Get a High-Level Overview
Start with a broad look at all your properties to spot trends or anomalies.
```bash
python key-performance-metrics.py
```
This will generate a report in `output/account/` showing the 16-month performance for all sites. Identify any sites that need a closer look.

### 2. Get a Snapshot of a Single Site
Once you've identified a site of interest, run the snapshot report to get a quick, detailed overview of its performance for the last month.
```bash
python snapshot-report.py https://www.example.com --last-month
```

### 3. Compare Performance Over Time
To understand recent changes, compare the last month's performance to the previous month. This will highlight what's improved and what's declined.
```bash
python performance-analysis.py https://www.example.com --last-month
```

### 4. Get a Page-Level Overview
To get a high-level view of how each page is performing and how many queries are driving traffic to it, use the new page-level report.
```bash
python page-level-report.py https://www.example.com --last-month
```

### 5. Investigate Query & Page Relationships
If you notice a page has lost traffic, use this script to see which specific queries have dropped off for that page.
```bash
python gsc-pages-queries.py https://www.example.com --last-month
```

### 6. Analyse Ranking Distribution
To see how your keyword rankings are distributed and trending over time, use the position analysis script. The charts make it easy to see if you are gaining or losing visibility in the top positions.
```bash
python query-position-analysis.py https://www.example.com
```

### 7. Run Reports for a Custom Group of Sites
If you need to run any of these reports for a specific group of sites, use the `run_for_sites.py` utility. First, create a file like `my_sites.txt` and add your URLs.
```bash
# Example: my_sites.txt
# https://www.site-a.com
# https://www.site-b.co.uk

# Now run the script
python run_for_sites.py snapshot-report.py --sites-file my_sites.txt --last-7-days
```

The Setup instructions are given at the end of this documnet.

## Available Scripts

This suite includes several scripts for different types of analysis:

*   [gsc_pages_exporter.py](#gsc_pages_exporter.py)
*   [gsc-pages-queries.py](#gsc-pages-queriespy)
*   [page-level-report.py](#page-level-reportpy)
*   [key-performance-metrics.py](#key-performance-metricspy)
*   [monthly-summary-report.py](#monthly-summary-report)
*   [performance-analysis.py](#performance-analysis)
*   [queries-pages-analysis.py](#queries-pages-analysis)
*   [query-segmentation-report.py](#query-segmentation-reportpy)
*   [query-position-analysis.py](#query-position-distribution-analysis)
*   [snapshot-report.py](#snapshot-report.py)
*   [generate_gsc_wrapped.py](#google-organic-wrapped-report)
*   [run_for_sites.py](#run-for-sites)

---

## gsc_pages_exporter.py

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
    *   The script now automatically loads brand terms from a corresponding file in the `config/` directory (e.g., `config/brand-terms-example.txt` for `example.com`).
    *   `--brand-terms-file <path>`: Manually specify a path to a text file containing brand terms (one per line). This will override the automatic file loading.
    *   `--brand-terms <term1> <term2> ...`: Specify a list of custom brand terms on the command line. These are always added to the set of terms.
    *   `--no-brand-detection`: Disables all brand analysis, including file loading and URL detection.

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

## page-level-report.py

Generates a page-level report showing the total clicks, impressions, CTR, average position, and the number of unique queries for each page.

### Usage

```bash
python page-level-report.py <site_url> [date_range_option] [--strip-query-strings]
```

*   `<site_url>`: (Required) The full URL of the site property (e.g., `https://www.example.com`) or a domain property (e.g., `sc-domain:example.com`).
*   `--strip-query-strings`: (Optional) Removes query strings from page URLs before aggregating data. This is useful for rolling up pages like `page?id=1` and `page?id=2` into a single `page` entry. When used, the output filename will include a `-no-query` suffix.

*   **Date Range Options**: Options like `--last-7-days`, `--last-month`, etc., are available. If omitted, it defaults to the last calendar month.

### Output

Generates a CSV and an HTML file in `output/<hostname>/`. The report lists all pages with their aggregated performance metrics (including average position) and the count of unique queries driving traffic to them, sorted by clicks in descending order. The HTML report also includes a summary table with overall totals.

### Advanced CSV Generation

You can re-process an existing CSV to create smaller, more focused reports without re-downloading data. This is useful for analysing the top performing queries.

*   `--top-queries <number>`: When used with `--csv`, this generates a new CSV file containing only the top N queries, sorted by total clicks.
*   `--split-brand`: Use with `--top-queries` to generate two separate files: one for the top N brand queries and one for the top N non-brand queries.

**Example:**

After running an initial download, you can generate a report of just the top 100 brand and non-brand queries.

```bash
# First, run the full download (if you haven't already)
python gsc-pages-queries.py https://www.example.com --last-12-months

# Now, generate focused CSVs from the downloaded file
python gsc-pages-queries.py --csv ./output/example.com/gsc-pages-queries-example-com-....csv --top-queries 100 --split-brand
```
This will create two new files:
*   `...-top-100-brand-queries.csv`
*   `...-top-100-non-brand-queries.csv`


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

Generates a detailed CSV file containing the merged data from both periods (if downloading) and an HTML report that highlights best/worst performing content, rising stars, and more. The HTML report includes clicks and impressions formatted for readability (e.g., 1,234).

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

Generates a CSV with detailed page data and an HTML report in `output/<hostname>/`. The report includes top pages, performance by device/country, and optimization opportunities. The HTML report also includes clicks and impressions formatted for readability (e.g., 1,234).

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

*   **Single Site**: Generates a CSV and an HTML file in `output/<hostname>/` showing monthly performance over the last 16 months. The HTML report includes numbers formatted for readability (e.g., 1,234).
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

*   **Single Site**: Generates a CSV and an HTML file in `output/<hostname>/` with monthly data including unique query and page counts. The HTML report includes numbers formatted for readability (e.g., 1,234).
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

*   **Single Site**: Generates a CSV and an HTML file in `output/<hostname>/` detailing the monthly query position distribution. The HTML report includes numbers formatted for readability (e.g., 1,234) and line charts visualizing clicks and impressions by position, as well as total clicks and impressions over time.
*   **All Sites**: Generates `output/account/` with a CSV and an HTML report providing an account-wide breakdown.

---

## query-segmentation-report.py

Generates a report that segments top queries by their ranking position buckets (1-3, 4-10, 11-20, and 21+). The report now includes summary charts at the top, providing a visual overview of the distribution of clicks, impressions, CTR, and query counts across these segments.

### Usage
```bash
python query-segmentation-report.py <site_url> [date_range_option]
```
*   `<site_url>`: (Required) The full URL of the site property (e.g., `https://www.example.com`) or a domain property (e.g., `sc-domain:example.com`).

*   **Date Range Options**: Options like `--last-month`, etc., are available. If omitted, it defaults to the last calendar month.

### Output
Generates a CSV and an HTML file in `output/<hostname>/`. The report contains four tables, each showing the top 50 queries (by clicks) for one of the position segments, preceded by the new summary charts.

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



## generate_gsc_wrapped.py

Creates a "Google Organic Wrapped"-style annual summary for a single GSC property, presenting your year in search in a fun, engaging format.

### Usage

The script has two main modes of operation:

1.  **Download Data from GSC:**
    ```bash
    python generate_gsc_wrapped.py <site_url> [date_range_option] [options]
    ```

2.  **Generate Report from CSV:**
    ```bash
    python generate_gsc_wrapped.py --csv <path_to_file.csv> [options]
    ```

### Arguments

*   `<site_url>`: The full URL of the site property (e.g., `https://www.example.com`) or a domain property (e.g., `sc-domain:example.com`). This is required unless `--csv` is used, but highly recommended for full functionality (e.g., 'Monthly Performance' calculations and brand term auto-detection).
*   `--csv <path>`: Path to an existing CSV file to use as the data source, skipping most GSC API calls. The CSV must contain at least `"page"`, `"query"`, `"clicks"`, and `"impressions"` columns. Date range flags are ignored when `--csv` is used.

*   **Date Range Options**:
    *   By default, a YTD report is generated.
    *   `--last-12-months`: Analyze the last 12 complete months.
    *   `--start-date YYYY-MM-DD` and `--end-date YYYY-MM-DD`: Specify a custom date range.

*   **Brand Analysis Options**:
    *   `--brand-terms <term1> <term2> ...`: Specify brand terms directly on the command line.
    *   `--brand-terms-file <path>`: Provide a path to a text file containing brand terms (one per line).
    *   `--no-brand-detection`: Disable the brand vs. non-brand classification.

### Features

*   **Enhanced Monthly Metrics**: The report now includes a 2x2 grid displaying monthly performance highlights for:
    *   Busiest Month (by Clicks)
    *   Top Impression Month
    *   Highest CTR Month
    *   Best Position Month
*   **Clickable Top Pages**: URLs in the "Your Top 5 Pages" list are now clickable and open in a new browser tab.

### Output

Generates a visually engaging HTML report that highlights key metrics, top pages, and monthly performance.
*   Reports are saved in `output/<hostname>/`.
*   To prevent overwriting, `sc-domain:` properties are saved in directories prefixed with `sc-domain-` (e.g., `output/sc-domain-example.com/`).

---
## run_wrapped_for_all_properties.py

Executes the `generate_gsc_wrapped.py` script for every Google Search Console property you have access to. This automates the process of generating "Wrapped" reports across your entire portfolio of sites.

### Usage

```bash
python run_for_all_properties.py [options_for_generate_gsc_wrapped.py]
```

All command-line arguments passed to `run_for_all_properties.py` (e.g., `--last-12-months`, `--no-brand-detection`, `--brand-terms-file`) will be forwarded to each execution of `generate_gsc_wrapped.py`.

### Example

To generate "Wrapped" reports for all properties for the last 12 months:

```bash
python run_for_all_properties.py --last-12-months
```

### Output

The script will print real-time output from each `generate_gsc_wrapped.py` run to your console. HTML reports will be saved in their respective property-specific directories under the `output/` folder, following the naming conventions described in the `generate_gsc_wrapped.py` section.

## run_for_sites.py

Executes a specified analysis script for a predefined list of Google Search Console properties. This is useful for running reports on a specific subset of your sites.

### Usage

The script can be run in two ways:

1.  **Provide sites as command-line arguments:**
    ```bash
    python run_for_sites.py <script_to_run.py> <site_url_1> <site_url_2> ...
    ```

2.  **Provide sites from a text file:**
    ```bash
    python run_for_sites.py <script_to_run.py> --sites-file <path_to_file.txt>
    ```
    The text file should contain one site URL per line. Lines starting with `#` will be ignored.

### Example

To run `query-position-analysis.py` for three specific sites:
```bash
python run_for_sites.py query-position-analysis.py https://www.example.com https://www.example.co.uk https://www.example.org
```

To run `snapshot-report.py` for all sites listed in `my_sites.txt` for the last 7 days:
```bash
# First, create my_sites.txt
# https://www.example.com
# https://www.croneri.co.uk

python run_for_sites.py snapshot-report.py --sites-file my_sites.txt --last-7-days
```

---

## run_all_reports_for_site.py

Executes all primary, monthly useful analysis scripts for a single specified Google Search Console property. This automates the generation of a full suite of common reports for a given site.

### Usage

```bash
python run_all_reports_for_site.py <site_url> [additional_arguments_for_scripts]
```
The `<site_url>` is the full URL of the site property (e.g., `https://www.example.com`) or a domain property (e.g., `sc-domain:example.com`). Any `additional_arguments_for_scripts` provided will be passed to each individual analysis script (e.g., `--last-month`, `--compare-to-previous-year`).

### Example

To run all reports for `https://www.example.com` for the last complete month:
```bash
python run_all_reports_for_site.py https://www.example.com --last-month
```

---

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
