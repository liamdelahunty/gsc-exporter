# GSC Exporter - Consolidated Reports Documentation

This file contains the complete documentation for all generated report types.

## Table of Contents

- [Consolidated Performance Overview Report](#consolidated-performance-overview-report)
- [Consolidated Traffic Report](#consolidated-traffic-report)
- [Discover Key Performance Metrics](#discover-key-performance-metrics)
- [Generate Gsc Wrapped](#generate-gsc-wrapped)
- [Gsc Pages Exporter](#gsc-pages-exporter)
- [Gsc Pages Queries](#gsc-pages-queries)
- [Historical Summary Report](#historical-summary-report)
- [Image Performance Report](#image-performance-report)
- [Key Performance Metrics](#key-performance-metrics)
- [Keyword Cannibalisation Report](#keyword-cannibalisation-report)
- [Monthly Search Type Performance Report](#monthly-search-type-performance-report)
- [Monthly Summary Report](#monthly-summary-report)
- [Page Level Report](#page-level-report)
- [Page Performance Over Time](#page-performance-over-time)
- [Page Performance Single Page](#page-performance-single-page)
- [Performance Analysis](#performance-analysis)
- [Period Comparison Report](#period-comparison-report)
- [Queries Pages Analysis](#queries-pages-analysis)
- [Query Position Analysis](#query-position-analysis)
- [Query Segmentation Report](#query-segmentation-report)
- [Search Appearance Report](#search-appearance-report)
- [Search Type Performance](#search-type-performance)
- [Seasonal Page Spike Report](#seasonal-page-spike-report)
- [Seasonal Performance Report](#seasonal-performance-report)
- [Seasonal Query Spike Report](#seasonal-query-spike-report)
- [Sitemap Generator](#sitemap-generator)
- [Snapshot Report](#snapshot-report)
- [Url Inspection Report](#url-inspection-report)

---

<a name="consolidated-performance-overview-report"></a>

# Consolidated Performance Overview Report

Generates a consolidated performance overview report across all properties in the GSC account.
Consolidates both Search Type performance and Search Appearance performance, highlighting overlaps and structural differences.

---

## Command Line Usage

### Standard Example
```bash
python reports/consolidated_performance_overview_report.py <site_url> --last-month
```

### Argument Reference
* **`site_url`** *(positional)*: The GSC property URL (e.g. `sc-domain:example.com` or `https://example.com/`).
* **`--start-date YYYY-MM-DD`**: Specify a custom start date for the analysis.
* **`--end-date YYYY-MM-DD`**: Specify a custom end date.
* **`--last-month`**: Automatically run the report for the last complete calendar month.
* **`--last-7-days`**: Run for the last 7 full days of available data.

No custom optional arguments defined for this report.


---

## Expected Output Files

This report generates the following files in the output directory:

* `output/<domain>/{file_prefix}-search-types.csv` (CSV dataset)
* `output/<domain>/{file_prefix}-search-appearances.csv` (CSV dataset)
* `output/<domain>/report-blank.html` (HTML report)
* `output/<domain>/{file_prefix}.html` (HTML report)
* `output/<domain>/consolidated-performance-overview-by-property-{start_date}-to-{end_date}.html` (HTML report)

---

## How to Interpret the Report Metrics

* **Clicks**: Represents the number of times a user clicked your search result to visit your site.
* **Impressions**: The number of times your search result appeared in search results.
* **CTR (Click-Through Rate)**: The percentage of impressions that resulted in a click (`Clicks / Impressions`). A low CTR indicates snippet styling or metadata needs improvement.
* **Average Position**: The average ranking position of your URLs for the queries. A lower position (closer to 1) is better. Monitor position trends to spot algorithm updates or competitor improvements.

---

## Recommendations and Best Practices

1. **Warm the Cache First**: Run `python utilities/cache_warmer.py --file site-lists/sites.txt` to populate GSC data locally before executing batch reports.
2. **Frequency**: Generate this report monthly to identify seasonal trends and monitor organic visibility performance.
3. **Bespoke Branding**: Custom logo, primary colours, and support links can be configured in `config/branding.json`.


---

<a name="consolidated-traffic-report"></a>

# Consolidated Traffic Report

No overview description available.

---

## Command Line Usage

### Standard Example
```bash
python reports/consolidated_traffic_report.py <site_url> --last-month
```

### Argument Reference
* **`site_url`** *(positional)*: The GSC property URL (e.g. `sc-domain:example.com` or `https://example.com/`).
* **`--start-date YYYY-MM-DD`**: Specify a custom start date for the analysis.
* **`--end-date YYYY-MM-DD`**: Specify a custom end date.
* **`--last-month`**: Automatically run the report for the last complete calendar month.
* **`--last-7-days`**: Run for the last 7 full days of available data.

### Optional Arguments

* **`--months`**: No description available. (default: `16`)


---

## Expected Output Files

This report generates the following files in the output directory:

* `output/<domain>/{file_prefix}.csv` (CSV dataset)
* `output/<domain>/consolidated-traffic-report-template.html` (HTML report)
* `output/<domain>/{file_prefix}.html` (HTML report)

---

## How to Interpret the Report Metrics

* **Clicks**: Represents the number of times a user clicked your search result to visit your site.
* **Impressions**: The number of times your search result appeared in search results.
* **CTR (Click-Through Rate)**: The percentage of impressions that resulted in a click (`Clicks / Impressions`). A low CTR indicates snippet styling or metadata needs improvement.
* **Average Position**: The average ranking position of your URLs for the queries. A lower position (closer to 1) is better. Monitor position trends to spot algorithm updates or competitor improvements.

---

## Recommendations and Best Practices

1. **Warm the Cache First**: Run `python utilities/cache_warmer.py --file site-lists/sites.txt` to populate GSC data locally before executing batch reports.
2. **Frequency**: Generate this report monthly to identify seasonal trends and monitor organic visibility performance.
3. **Bespoke Branding**: Custom logo, primary colours, and support links can be configured in `config/branding.json`.


---

<a name="discover-key-performance-metrics"></a>

# Discover Key Performance Metrics

Performs an analysis of Google Search Console Discover data, gathering key performance metrics.
Refactored for modular GSC Exporter.

---

## Command Line Usage

### Standard Example
```bash
python reports/discover_key_performance_metrics.py <site_url> --last-month
```

### Argument Reference
* **`site_url`** *(positional)*: The GSC property URL (e.g. `sc-domain:example.com` or `https://example.com/`).
* **`--start-date YYYY-MM-DD`**: Specify a custom start date for the analysis.
* **`--end-date YYYY-MM-DD`**: Specify a custom end date.
* **`--last-month`**: Automatically run the report for the last complete calendar month.
* **`--last-7-days`**: Run for the last 7 full days of available data.

### Optional Arguments

* **`--months`**: No description available. (default: `16`)


---

## Expected Output Files

This report generates the following files in the output directory:

* `output/<domain>/{file_prefix}.csv` (CSV dataset)
* `output/<domain>/{file_prefix}.html` (HTML report)

---

## How to Interpret the Google Discover Report

Google Discover is a query-less feed based on user interests rather than search intent.

### 1. Volatility and Spikes
* Discover traffic is notoriously spike-heavy and short-lived. Expect rapid impression surges followed by steep declines.

### 2. High CTR Expectations
* Discover CTRs are often much higher than standard organic web CTR (often 5% to 15%+).
* Analyse high-performing Discover topics to identify content themes that resonate with your target audience's interest feed.

---

## Recommendations and Best Practices

1. **Warm the Cache First**: Run `python utilities/cache_warmer.py --file site-lists/sites.txt` to populate GSC data locally before executing batch reports.
2. **Frequency**: Generate this report monthly to identify seasonal trends and monitor organic visibility performance.
3. **Bespoke Branding**: Custom logo, primary colours, and support links can be configured in `config/branding.json`.


---

<a name="generate-gsc-wrapped"></a>

# Generate Gsc Wrapped

Generates a "Google Organic Wrapped"-style report for Google Search Console data.
Refactored for modular GSC Exporter.

---

## Command Line Usage

### Standard Example
```bash
python reports/generate_gsc_wrapped.py <site_url> --last-month
```

### Argument Reference
* **`site_url`** *(positional)*: The GSC property URL (e.g. `sc-domain:example.com` or `https://example.com/`).
* **`--start-date YYYY-MM-DD`**: Specify a custom start date for the analysis.
* **`--end-date YYYY-MM-DD`**: Specify a custom end date.
* **`--last-month`**: Automatically run the report for the last complete calendar month.
* **`--last-7-days`**: Run for the last 7 full days of available data.

### Optional Arguments

* **`--last-12-months`**: Run for the last 12 months.


---

## Expected Output Files

This report generates the following files in the output directory:

* `output/<domain>/gsc-wrapped-{slug}-pages-{start_date}-to-{end_date}.csv` (CSV dataset)
* `output/<domain>/gsc-wrapped-{slug}-queries-{start_date}-to-{end_date}.csv` (CSV dataset)
* `output/<domain>/gsc-wrapped-template.html` (HTML report)
* `output/<domain>/gsc-wrapped-{slug}-{start_date}-to-{end_date}.html` (HTML report)

---

## How to Interpret the Report Metrics

* **Clicks**: Represents the number of times a user clicked your search result to visit your site.
* **Impressions**: The number of times your search result appeared in search results.
* **CTR (Click-Through Rate)**: The percentage of impressions that resulted in a click (`Clicks / Impressions`). A low CTR indicates snippet styling or metadata needs improvement.
* **Average Position**: The average ranking position of your URLs for the queries. A lower position (closer to 1) is better. Monitor position trends to spot algorithm updates or competitor improvements.

---

## Recommendations and Best Practices

1. **Warm the Cache First**: Run `python utilities/cache_warmer.py --file site-lists/sites.txt` to populate GSC data locally before executing batch reports.
2. **Frequency**: Generate this report monthly to identify seasonal trends and monitor organic visibility performance.
3. **Bespoke Branding**: Custom logo, primary colours, and support links can be configured in `config/branding.json`.


---

<a name="gsc-pages-exporter"></a>

# Gsc Pages Exporter

Exports all pages from a Google Search Console property to a CSV and an HTML file.
Refactored for modular GSC Exporter.

---

## Command Line Usage

### Standard Example
```bash
python reports/gsc_pages_exporter.py <site_url> --last-month
```

### Argument Reference
* **`site_url`** *(positional)*: The GSC property URL (e.g. `sc-domain:example.com` or `https://example.com/`).
* **`--start-date YYYY-MM-DD`**: Specify a custom start date for the analysis.
* **`--end-date YYYY-MM-DD`**: Specify a custom end date.
* **`--last-month`**: Automatically run the report for the last complete calendar month.
* **`--last-7-days`**: Run for the last 7 full days of available data.

No custom optional arguments defined for this report.


---

## Expected Output Files

This report generates the following files in the output directory:

* `output/<domain>/{file_prefix}.csv` (CSV dataset)
* `output/<domain>/{file_prefix}.html` (HTML report)

---

## How to Interpret the Report Metrics

* **Clicks**: Represents the number of times a user clicked your search result to visit your site.
* **Impressions**: The number of times your search result appeared in search results.
* **CTR (Click-Through Rate)**: The percentage of impressions that resulted in a click (`Clicks / Impressions`). A low CTR indicates snippet styling or metadata needs improvement.
* **Average Position**: The average ranking position of your URLs for the queries. A lower position (closer to 1) is better. Monitor position trends to spot algorithm updates or competitor improvements.

---

## Recommendations and Best Practices

1. **Warm the Cache First**: Run `python utilities/cache_warmer.py --file site-lists/sites.txt` to populate GSC data locally before executing batch reports.
2. **Frequency**: Generate this report monthly to identify seasonal trends and monitor organic visibility performance.
3. **Bespoke Branding**: Custom logo, primary colours, and support links can be configured in `config/branding.json`.


---

<a name="gsc-pages-queries"></a>

# Gsc Pages Queries

Exports a report of queries and their corresponding pages from a Google 
Search Console property.
Refactored for modular GSC Exporter.

---

## Command Line Usage

### Standard Example
```bash
python reports/gsc_pages_queries.py <site_url> --last-month
```

### Argument Reference
* **`site_url`** *(positional)*: The GSC property URL (e.g. `sc-domain:example.com` or `https://example.com/`).
* **`--start-date YYYY-MM-DD`**: Specify a custom start date for the analysis.
* **`--end-date YYYY-MM-DD`**: Specify a custom end date.
* **`--last-month`**: Automatically run the report for the last complete calendar month.
* **`--last-7-days`**: Run for the last 7 full days of available data.

### Optional Arguments

* **`--report-limit`**: No description available. (default: `250`)
* **`--sub-table-limit`**: No description available. (default: `100`)
* **`--brand-terms`**: Custom brand terms.
* **`--brand-terms-file`**: Path to a file containing brand terms.
* **`--no-brand-detection`**: Disable brand detection.


---

## Expected Output Files

This report generates the following files in the output directory:

* `output/<domain>/{file_prefix}.csv` (CSV dataset)
* `output/<domain>/{file_prefix}.html` (HTML report)

---

## How to Interpret the Report Metrics

* **Clicks**: Represents the number of times a user clicked your search result to visit your site.
* **Impressions**: The number of times your search result appeared in search results.
* **CTR (Click-Through Rate)**: The percentage of impressions that resulted in a click (`Clicks / Impressions`). A low CTR indicates snippet styling or metadata needs improvement.
* **Average Position**: The average ranking position of your URLs for the queries. A lower position (closer to 1) is better. Monitor position trends to spot algorithm updates or competitor improvements.

---

## Recommendations and Best Practices

1. **Warm the Cache First**: Run `python utilities/cache_warmer.py --file site-lists/sites.txt` to populate GSC data locally before executing batch reports.
2. **Frequency**: Generate this report monthly to identify seasonal trends and monitor organic visibility performance.
3. **Bespoke Branding**: Custom logo, primary colours, and support links can be configured in `config/branding.json`.


---

<a name="historical-summary-report"></a>

# Historical Summary Report

No overview description available.

---

## Command Line Usage

### Standard Example
```bash
python reports/historical_summary_report.py <site_url> --last-month
```

### Argument Reference
* **`site_url`** *(positional)*: The GSC property URL (e.g. `sc-domain:example.com` or `https://example.com/`).
* **`--start-date YYYY-MM-DD`**: Specify a custom start date for the analysis.
* **`--end-date YYYY-MM-DD`**: Specify a custom end date.
* **`--last-month`**: Automatically run the report for the last complete calendar month.
* **`--last-7-days`**: Run for the last 7 full days of available data.

No custom optional arguments defined for this report.


---

## Expected Output Files

This report generates the following files in the output directory:

* `output/<domain>/monthly-summary-report-{slug}-*.csv` (CSV dataset)
* `output/<domain>/{file_prefix}.csv` (CSV dataset)
* `output/<domain>/report-blank.html` (HTML report)
* `output/<domain>/{file_prefix}.html` (HTML report)

---

## How to Interpret the Report Metrics

* **Clicks**: Represents the number of times a user clicked your search result to visit your site.
* **Impressions**: The number of times your search result appeared in search results.
* **CTR (Click-Through Rate)**: The percentage of impressions that resulted in a click (`Clicks / Impressions`). A low CTR indicates snippet styling or metadata needs improvement.
* **Average Position**: The average ranking position of your URLs for the queries. A lower position (closer to 1) is better. Monitor position trends to spot algorithm updates or competitor improvements.

---

## Recommendations and Best Practices

1. **Warm the Cache First**: Run `python utilities/cache_warmer.py --file site-lists/sites.txt` to populate GSC data locally before executing batch reports.
2. **Frequency**: Generate this report monthly to identify seasonal trends and monitor organic visibility performance.
3. **Bespoke Branding**: Custom logo, primary colours, and support links can be configured in `config/branding.json`.


---

<a name="image-performance-report"></a>

# Image Performance Report

Generates a specialized success report for Google Image Search performance.
Refactored for modular GSC Exporter.

---

## Command Line Usage

### Standard Example
```bash
python reports/image_performance_report.py <site_url> --last-month
```

### Argument Reference
* **`site_url`** *(positional)*: The GSC property URL (e.g. `sc-domain:example.com` or `https://example.com/`).
* **`--start-date YYYY-MM-DD`**: Specify a custom start date for the analysis.
* **`--end-date YYYY-MM-DD`**: Specify a custom end date.
* **`--last-month`**: Automatically run the report for the last complete calendar month.
* **`--last-7-days`**: Run for the last 7 full days of available data.

No custom optional arguments defined for this report.


---

## Expected Output Files

This report generates the following files in the output directory:

* `output/<domain>/{file_prefix}-queries.csv` (CSV dataset)
* `output/<domain>/{file_prefix}-pages.csv` (CSV dataset)
* `output/<domain>/{file_prefix}-matrix.csv` (CSV dataset)
* `output/<domain>/{file_prefix}.html` (HTML report)

---

## How to Interpret the Report Metrics

* **Clicks**: Represents the number of times a user clicked your search result to visit your site.
* **Impressions**: The number of times your search result appeared in search results.
* **CTR (Click-Through Rate)**: The percentage of impressions that resulted in a click (`Clicks / Impressions`). A low CTR indicates snippet styling or metadata needs improvement.
* **Average Position**: The average ranking position of your URLs for the queries. A lower position (closer to 1) is better. Monitor position trends to spot algorithm updates or competitor improvements.

---

## Recommendations and Best Practices

1. **Warm the Cache First**: Run `python utilities/cache_warmer.py --file site-lists/sites.txt` to populate GSC data locally before executing batch reports.
2. **Frequency**: Generate this report monthly to identify seasonal trends and monitor organic visibility performance.
3. **Bespoke Branding**: Custom logo, primary colours, and support links can be configured in `config/branding.json`.


---

<a name="key-performance-metrics"></a>

# Key Performance Metrics

Performs analysis of Google Search Console data, gathering key performance metrics on a monthly or weekly basis.
Refactored for modular GSC Exporter.

---

## Command Line Usage

### Standard Example
```bash
python reports/key_performance_metrics.py <site_url> --last-month
```

### Weekly Reporting Example
```bash
python reports/key_performance_metrics.py <site_url> --weekly --weeks 4
```

### Argument Reference
* **`site_url`** *(positional)*: The GSC property URL (e.g. `sc-domain:example.com` or `https://example.com/`).
* **`--start-date YYYY-MM-DD`**: Specify a custom start date for the analysis.
* **`--end-date YYYY-MM-DD`**: Specify a custom end date.
* **`--last-month`**: Automatically run the report for the last complete calendar month.
* **`--last-7-days`**: Run for the last 7 full days of available data.

### Optional Arguments

* **`--months`**: Number of months for monthly report, defaulting to 16. (default: `16`)
* **`--weekly`**: Run report on a weekly basis with weeks starting on Monday.
* **`--weeks`**: Number of weeks for weekly report, defaulting to 4. Automatically enables weekly mode. (default: `None`)


---

## Expected Output Files

This report generates the following files in the output directory:

* `output/<domain>/key-metrics-weekly-{slug}-{start_date}-{end_date}.csv` (CSV dataset)
* `output/<domain>/key-metrics-weekly-{slug}-{start_date}-{end_date}.html` (HTML report)
* `output/<domain>/key-metrics-{slug}-{most_recent}.csv` (CSV dataset)
* `output/<domain>/key-metrics-{slug}-{most_recent}.html` (HTML report)

---

## How to Interpret the Key Performance Metrics Report

A macro-level dashboard tracking site health and organic visibility over monthly (16-month) or weekly intervals.

### 1. Seasonal Trends and Weekly Cadence
* Spot year-over-year (YoY) changes, holiday dips, or quarterly industry trends in monthly mode.
* Track short-term week-on-week fluctuations and recent campaign momentum in weekly mode.

### 2. Search Performance Metrics
* Track absolute clicks and impressions alongside click-through rates (CTR) and average search positions.

### 3. Historical Trajectory
* Assess whether SEO strategies are yielding compound growth or if site-wide visibility is in decline.

---

## Recommendations and Best Practices

1. **Warm the Cache First**: Run `python utilities/cache_warmer.py --file site-lists/sites.txt` to populate GSC data locally before executing batch reports.
2. **Frequency**: Generate this report monthly to identify seasonal trends and monitor organic visibility performance.
3. **Bespoke Branding**: Custom logo, primary colours, and support links can be configured in `config/branding.json`.


---

<a name="keyword-cannibalisation-report"></a>

# Keyword Cannibalisation Report

Generates a report that highlights keyword cannibalisation issues.
Refactored for modular GSC Exporter.

---

## Command Line Usage

### Standard Example
```bash
python reports/keyword_cannibalisation_report.py <site_url> --last-month
```

### Argument Reference
* **`site_url`** *(positional)*: The GSC property URL (e.g. `sc-domain:example.com` or `https://example.com/`).
* **`--start-date YYYY-MM-DD`**: Specify a custom start date for the analysis.
* **`--end-date YYYY-MM-DD`**: Specify a custom end date.
* **`--last-month`**: Automatically run the report for the last complete calendar month.
* **`--last-7-days`**: Run for the last 7 full days of available data.

No custom optional arguments defined for this report.


---

## Expected Output Files

This report generates the following files in the output directory:

* `output/<domain>/{file_prefix}.csv` (CSV dataset)
* `output/<domain>/{file_prefix}.html` (HTML report)

---

## How to Interpret the Keyword Cannibalisation Report

Keyword cannibalisation occurs when multiple pages on your site compete for the same search query.

### 1. Identifying Competitor Pages
* Look for queries where multiple URLs rank with similar average positions.
* If a query lists multiple ranking URLs with split clicks, it indicates search engines are confused about which page is most relevant.

### 2. Assessing the Impact
* **Diluted Authority**: Link equity and click-through rates are split across pages.
* **Rank Fluctuations**: Search engines may constantly alternate which page ranks, causing position instability.

### 3. Actions to Resolve Cannibalisation
* **Canonicalisation**: Set the canonical tag of the weaker page to point to the primary page if they serve the same intent.
* **301 Redirects**: Redirect the redundant page to the primary page and merge their content.
* **De-optimisation**: Remove the target keyword from the metadata and headings of the secondary page.
* **Content Restructuring**: Re-write the pages to target distinct search intents (e.g. informational vs. transactional).

---

## Recommendations and Best Practices

1. **Warm the Cache First**: Run `python utilities/cache_warmer.py --file site-lists/sites.txt` to populate GSC data locally before executing batch reports.
2. **Frequency**: Generate this report monthly to identify seasonal trends and monitor organic visibility performance.
3. **Bespoke Branding**: Custom logo, primary colours, and support links can be configured in `config/branding.json`.


---

<a name="monthly-search-type-performance-report"></a>

# Monthly Search Type Performance Report

Generates a monthly Google Search Console performance report by search type.
Adapted for the modular GSC Exporter.

---

## Command Line Usage

### Standard Example
```bash
python reports/monthly_search_type_performance_report.py <site_url> --last-month
```

### Argument Reference
* **`site_url`** *(positional)*: The GSC property URL (e.g. `sc-domain:example.com` or `https://example.com/`).
* **`--start-date YYYY-MM-DD`**: Specify a custom start date for the analysis.
* **`--end-date YYYY-MM-DD`**: Specify a custom end date.
* **`--last-month`**: Automatically run the report for the last complete calendar month.
* **`--last-7-days`**: Run for the last 7 full days of available data.

No custom optional arguments defined for this report.


---

## Expected Output Files

This report generates the following files in the output directory:

* `output/<domain>/{file_prefix}.csv` (CSV dataset)
* `output/<domain>/{file_prefix}.html` (HTML report)

---

## How to Interpret the Report Metrics

* **Clicks**: Represents the number of times a user clicked your search result to visit your site.
* **Impressions**: The number of times your search result appeared in search results.
* **CTR (Click-Through Rate)**: The percentage of impressions that resulted in a click (`Clicks / Impressions`). A low CTR indicates snippet styling or metadata needs improvement.
* **Average Position**: The average ranking position of your URLs for the queries. A lower position (closer to 1) is better. Monitor position trends to spot algorithm updates or competitor improvements.

---

## Recommendations and Best Practices

1. **Warm the Cache First**: Run `python utilities/cache_warmer.py --file site-lists/sites.txt` to populate GSC data locally before executing batch reports.
2. **Frequency**: Generate this report monthly to identify seasonal trends and monitor organic visibility performance.
3. **Bespoke Branding**: Custom logo, primary colours, and support links can be configured in `config/branding.json`.


---

<a name="monthly-summary-report"></a>

# Monthly Summary Report

Generates a summary report of Google Search Console performance data for various date ranges.
Adapted for the modular GSC Exporter.

---

## Command Line Usage

### Standard Example
```bash
python reports/monthly_summary_report.py <site_url> --last-month
```

### Argument Reference
* **`site_url`** *(positional)*: The GSC property URL (e.g. `sc-domain:example.com` or `https://example.com/`).
* **`--start-date YYYY-MM-DD`**: Specify a custom start date for the analysis.
* **`--end-date YYYY-MM-DD`**: Specify a custom end date.
* **`--last-month`**: Automatically run the report for the last complete calendar month.
* **`--last-7-days`**: Run for the last 7 full days of available data.

### Optional Arguments

* **`--sites-file`**: Text file with site URLs.


---

## Expected Output Files

This report generates the following files in the output directory:

* `output/<domain>/{file_prefix}.csv` (CSV dataset)
* `output/<domain>/report-blank.html` (HTML report)
* `output/<domain>/{file_prefix}.html` (HTML report)

---

## How to Interpret the Report Metrics

* **Clicks**: Represents the number of times a user clicked your search result to visit your site.
* **Impressions**: The number of times your search result appeared in search results.
* **CTR (Click-Through Rate)**: The percentage of impressions that resulted in a click (`Clicks / Impressions`). A low CTR indicates snippet styling or metadata needs improvement.
* **Average Position**: The average ranking position of your URLs for the queries. A lower position (closer to 1) is better. Monitor position trends to spot algorithm updates or competitor improvements.

---

## Recommendations and Best Practices

1. **Warm the Cache First**: Run `python utilities/cache_warmer.py --file site-lists/sites.txt` to populate GSC data locally before executing batch reports.
2. **Frequency**: Generate this report monthly to identify seasonal trends and monitor organic visibility performance.
3. **Bespoke Branding**: Custom logo, primary colours, and support links can be configured in `config/branding.json`.


---

<a name="page-level-report"></a>

# Page Level Report

Generates a page-level report with key performance metrics and unique query counts.
Adapted for the modular GSC Exporter.

---

## Command Line Usage

### Standard Example
```bash
python reports/page_level_report.py <site_url> --last-month
```

### Argument Reference
* **`site_url`** *(positional)*: The GSC property URL (e.g. `sc-domain:example.com` or `https://example.com/`).
* **`--start-date YYYY-MM-DD`**: Specify a custom start date for the analysis.
* **`--end-date YYYY-MM-DD`**: Specify a custom end date.
* **`--last-month`**: Automatically run the report for the last complete calendar month.
* **`--last-7-days`**: Run for the last 7 full days of available data.

### Optional Arguments

* **`--search-type`**: No description available. (default: `'web'`)
* **`--limit`**: Limit for HTML report. (default: `250`)
* **`--strip-query-strings`**: Remove query strings.


---

## Expected Output Files

This report generates the following files in the output directory:

* `output/<domain>/{file_prefix}.csv` (CSV dataset)
* `output/<domain>/{file_prefix}.html` (HTML report)

---

## How to Interpret the Page Level Report

A page-centric view of performance focusing on organic traffic distribution and query complexity.

### 1. Unique Query Counts (Query #)
* **Long-Tail Depth**: Pages with a high number of unique queries are successfully capturing long-tail search traffic.
* **Narrow Intent**: Pages with high clicks but a low unique query count typically rank highly for a single, high-volume keyword.

### 2. Traffic Skew
* Typically, 20% of your pages drive 80% of your traffic. Use this report to verify if traffic is diversified or heavily reliant on a single landing page.
* Check pages with high unique queries but low clicks—they may require small content expansions to move long-tail rankings from page 2 to page 1.

---

## Recommendations and Best Practices

1. **Warm the Cache First**: Run `python utilities/cache_warmer.py --file site-lists/sites.txt` to populate GSC data locally before executing batch reports.
2. **Frequency**: Generate this report monthly to identify seasonal trends and monitor organic visibility performance.
3. **Bespoke Branding**: Custom logo, primary colours, and support links can be configured in `config/branding.json`.


---

<a name="page-performance-over-time"></a>

# Page Performance Over Time

Tracks the performance of top pages over the last 16 months.
Adapted for the modular GSC Exporter.

---

## Command Line Usage

### Standard Example
```bash
python reports/page_performance_over_time.py <site_url> --last-month
```

### Argument Reference
* **`site_url`** *(positional)*: The GSC property URL (e.g. `sc-domain:example.com` or `https://example.com/`).
* **`--start-date YYYY-MM-DD`**: Specify a custom start date for the analysis.
* **`--end-date YYYY-MM-DD`**: Specify a custom end date.
* **`--last-month`**: Automatically run the report for the last complete calendar month.
* **`--last-7-days`**: Run for the last 7 full days of available data.

### Optional Arguments

* **`--limit`**: Number of top pages to track. (default: `25`)
* **`--months`**: Number of months for historical lookback. (default: `16`)


---

## Expected Output Files

This report generates the following files in the output directory:

* `output/<domain>/{file_prefix}.csv` (CSV dataset)
* `output/<domain>/{file_prefix}.html` (HTML report)

---

## How to Interpret the Report Metrics

* **Clicks**: Represents the number of times a user clicked your search result to visit your site.
* **Impressions**: The number of times your search result appeared in search results.
* **CTR (Click-Through Rate)**: The percentage of impressions that resulted in a click (`Clicks / Impressions`). A low CTR indicates snippet styling or metadata needs improvement.
* **Average Position**: The average ranking position of your URLs for the queries. A lower position (closer to 1) is better. Monitor position trends to spot algorithm updates or competitor improvements.

---

## Recommendations and Best Practices

1. **Warm the Cache First**: Run `python utilities/cache_warmer.py --file site-lists/sites.txt` to populate GSC data locally before executing batch reports.
2. **Frequency**: Generate this report monthly to identify seasonal trends and monitor organic visibility performance.
3. **Bespoke Branding**: Custom logo, primary colours, and support links can be configured in `config/branding.json`.


---

<a name="page-performance-single-page"></a>

# Page Performance Single Page

Generates a report showing the performance of a single page over the last 16 months.
Adapted for the modular GSC Exporter.

---

## Command Line Usage

### Standard Example
```bash
python reports/page_performance_single_page.py sc-domain:example.com https://example.com/page-url --last-month
```

### Argument Reference
* **`site_url`** *(positional)*: The GSC property URL (e.g. `sc-domain:example.com` or `https://example.com/`).
* **`--start-date YYYY-MM-DD`**: Specify a custom start date for the analysis.
* **`--end-date YYYY-MM-DD`**: Specify a custom end date.
* **`--last-month`**: Automatically run the report for the last complete calendar month.
* **`--last-7-days`**: Run for the last 7 full days of available data.

### Optional Arguments

* **`page_url`**: The URL of the page to analyse.
* **`--site-url`**: No description available.
* **`--months`**: Number of months for historical lookback. (default: `16`)


---

## Expected Output Files

This report generates the following files in the output directory:

* `output/<domain>/{file_prefix}.csv` (CSV dataset)
* `output/<domain>/{file_prefix}.html` (HTML report)

---

## How to Interpret the Report Metrics

* **Clicks**: Represents the number of times a user clicked your search result to visit your site.
* **Impressions**: The number of times your search result appeared in search results.
* **CTR (Click-Through Rate)**: The percentage of impressions that resulted in a click (`Clicks / Impressions`). A low CTR indicates snippet styling or metadata needs improvement.
* **Average Position**: The average ranking position of your URLs for the queries. A lower position (closer to 1) is better. Monitor position trends to spot algorithm updates or competitor improvements.

---

## Recommendations and Best Practices

1. **Warm the Cache First**: Run `python utilities/cache_warmer.py --file site-lists/sites.txt` to populate GSC data locally before executing batch reports.
2. **Frequency**: Generate this report monthly to identify seasonal trends and monitor organic visibility performance.
3. **Bespoke Branding**: Custom logo, primary colours, and support links can be configured in `config/branding.json`.


---

<a name="performance-analysis"></a>

# Performance Analysis

A script for performance analysis of Google Search Console data.

This script fetches performance data (clicks, impressions, CTR, position) for two 
different time periods, compares them, and generates a report highlighting best/worst 
performing pages and pages with low CTR.

Usage:
    python performance-analysis.py <site_url> [comparison_flag] [filter_flags]

Examples:
    python performance-analysis.py https://www.example.com --last-month

---

## Command Line Usage

### Standard Example
```bash
python reports/performance_analysis.py <site_url> --last-month
```

### Argument Reference
* **`site_url`** *(positional)*: The GSC property URL (e.g. `sc-domain:example.com` or `https://example.com/`).
* **`--start-date YYYY-MM-DD`**: Specify a custom start date for the analysis.
* **`--end-date YYYY-MM-DD`**: Specify a custom end date.
* **`--last-month`**: Automatically run the report for the last complete calendar month.
* **`--last-7-days`**: Run for the last 7 full days of available data.

No custom optional arguments defined for this report.


---

## Expected Output Files

This report generates the following files in the output directory:

* `output/<domain>/performance-analysis-{slug}-{start_date}-to-{end_date}.csv` (CSV dataset)
* `output/<domain>/performance-analysis-template.html` (HTML report)
* `output/<domain>/performance-analysis-{slug}-{start_date}-to-{end_date}.html` (HTML report)

---

## How to Interpret the Report Metrics

* **Clicks**: Represents the number of times a user clicked your search result to visit your site.
* **Impressions**: The number of times your search result appeared in search results.
* **CTR (Click-Through Rate)**: The percentage of impressions that resulted in a click (`Clicks / Impressions`). A low CTR indicates snippet styling or metadata needs improvement.
* **Average Position**: The average ranking position of your URLs for the queries. A lower position (closer to 1) is better. Monitor position trends to spot algorithm updates or competitor improvements.

---

## Recommendations and Best Practices

1. **Warm the Cache First**: Run `python utilities/cache_warmer.py --file site-lists/sites.txt` to populate GSC data locally before executing batch reports.
2. **Frequency**: Generate this report monthly to identify seasonal trends and monitor organic visibility performance.
3. **Bespoke Branding**: Custom logo, primary colours, and support links can be configured in `config/branding.json`.


---

<a name="period-comparison-report"></a>

# Period Comparison Report

A script to compare performance across two time periods, providing charts
and query-level delta analysis.

---

## Command Line Usage

### Standard Example
```bash
python reports/period_comparison_report.py <site_url> --last-month
```

### Argument Reference
* **`site_url`** *(positional)*: The GSC property URL (e.g. `sc-domain:example.com` or `https://example.com/`).
* **`--start-date YYYY-MM-DD`**: Specify a custom start date for the analysis.
* **`--end-date YYYY-MM-DD`**: Specify a custom end date.
* **`--last-month`**: Automatically run the report for the last complete calendar month.
* **`--last-7-days`**: Run for the last 7 full days of available data.

No custom optional arguments defined for this report.


---

## Expected Output Files

This report generates the following files in the output directory:

* `output/<domain>/period-comparison-{slug}-{start_date}-to-{end_date}.csv` (CSV dataset)
* `output/<domain>/period-comparison-template.html` (HTML report)
* `output/<domain>/period-comparison-{slug}-{start_date}-to-{end_date}.html` (HTML report)

---

## How to Interpret the Period Comparison Report

This report tracks performance changes between a current period and a previous period of equal length.

### 1. Interactive Charts
* Visualise query-level deltas to quickly distinguish broad traffic changes from page-specific fluctuations.

### 2. Query Deltas (Clicks & Impressions)
* **Positive Delta (+)**: Marks search terms that have gained visibility and clicks ("Rising Stars").
* **Negative Delta (-)**: Highlights search terms that have lost traction ("Decaying Keywords").

### 3. Position Deltas
* **Negative Delta (-)**: Represents a positive change (ranking moved closer to position 1).
* **Positive Delta (+)**: Indicates ranking slippage.

### 4. Content Decay & Opportunity Analysis
* Sort by click delta descending to find the biggest winners.
* Sort by click delta ascending to locate decaying pages/queries that require content updates or backlink acquisition.
* Focus on queries with stable or rising impressions but falling clicks—this indicates a drop in snippet relevance or increased competitor ad spend.

---

## Recommendations and Best Practices

1. **Warm the Cache First**: Run `python utilities/cache_warmer.py --file site-lists/sites.txt` to populate GSC data locally before executing batch reports.
2. **Frequency**: Generate this report monthly to identify seasonal trends and monitor organic visibility performance.
3. **Bespoke Branding**: Custom logo, primary colours, and support links can be configured in `config/branding.json`.


---

<a name="queries-pages-analysis"></a>

# Queries Pages Analysis

No overview description available.

---

## Command Line Usage

### Standard Example
```bash
python reports/queries_pages_analysis.py <site_url> --last-month
```

### Argument Reference
* **`site_url`** *(positional)*: The GSC property URL (e.g. `sc-domain:example.com` or `https://example.com/`).
* **`--start-date YYYY-MM-DD`**: Specify a custom start date for the analysis.
* **`--end-date YYYY-MM-DD`**: Specify a custom end date.
* **`--last-month`**: Automatically run the report for the last complete calendar month.
* **`--last-7-days`**: Run for the last 7 full days of available data.

### Optional Arguments

* **`--months`**: Number of months to analyse for historical report.


---

## Expected Output Files

This report generates the following files in the output directory:

* `output/<domain>/{file_prefix}.csv` (CSV dataset)
* `output/<domain>/{file_prefix}.html` (HTML report)

---

## How to Interpret the Report Metrics

* **Clicks**: Represents the number of times a user clicked your search result to visit your site.
* **Impressions**: The number of times your search result appeared in search results.
* **CTR (Click-Through Rate)**: The percentage of impressions that resulted in a click (`Clicks / Impressions`). A low CTR indicates snippet styling or metadata needs improvement.
* **Average Position**: The average ranking position of your URLs for the queries. A lower position (closer to 1) is better. Monitor position trends to spot algorithm updates or competitor improvements.

---

## Recommendations and Best Practices

1. **Warm the Cache First**: Run `python utilities/cache_warmer.py --file site-lists/sites.txt` to populate GSC data locally before executing batch reports.
2. **Frequency**: Generate this report monthly to identify seasonal trends and monitor organic visibility performance.
3. **Bespoke Branding**: Custom logo, primary colours, and support links can be configured in `config/branding.json`.


---

<a name="query-position-analysis"></a>

# Query Position Analysis

No overview description available.

---

## Command Line Usage

### Standard Example
```bash
python reports/query_position_analysis.py <site_url> --last-month
```

### Argument Reference
* **`site_url`** *(positional)*: The GSC property URL (e.g. `sc-domain:example.com` or `https://example.com/`).
* **`--start-date YYYY-MM-DD`**: Specify a custom start date for the analysis.
* **`--end-date YYYY-MM-DD`**: Specify a custom end date.
* **`--last-month`**: Automatically run the report for the last complete calendar month.
* **`--last-7-days`**: Run for the last 7 full days of available data.

### Optional Arguments

* **`--months`**: Number of months to analyse. (default: `16`)


---

## Expected Output Files

This report generates the following files in the output directory:

* `output/<domain>/query-position-analysis-{slug}-{start_date}-to-{end_date}.csv` (CSV dataset)
* `output/<domain>/query-position-analysis-{slug}-{start_date}-to-{end_date}.html` (HTML report)

---

## How to Interpret the Query Position Analysis Report

Tracks how your keywords are distributed across different ranking groups over time.

### 1. Position Buckets
* Monitors the count and trend of keywords ranking in:
  * **Top 3**: Primary traffic drivers.
  * **Positions 4-10**: Page 1 visibility; prime candidates for optimization to push into Top 3.
  * **Positions 11-20**: Page 2 visibility; requires content improvements or link additions to reach page 1.
  * **Positions 21-100**: Long-tail or low-relevance queries.

### 2. Trend Identification
* If Top 3 keywords are declining while Positions 11-20 are increasing, it indicates site-wide ranking deflation or increased competitor activity.

---

## Recommendations and Best Practices

1. **Warm the Cache First**: Run `python utilities/cache_warmer.py --file site-lists/sites.txt` to populate GSC data locally before executing batch reports.
2. **Frequency**: Generate this report monthly to identify seasonal trends and monitor organic visibility performance.
3. **Bespoke Branding**: Custom logo, primary colours, and support links can be configured in `config/branding.json`.


---

<a name="query-segmentation-report"></a>

# Query Segmentation Report

No overview description available.

---

## Command Line Usage

### Standard Example
```bash
python reports/query_segmentation_report.py <site_url> --last-month
```

### Argument Reference
* **`site_url`** *(positional)*: The GSC property URL (e.g. `sc-domain:example.com` or `https://example.com/`).
* **`--start-date YYYY-MM-DD`**: Specify a custom start date for the analysis.
* **`--end-date YYYY-MM-DD`**: Specify a custom end date.
* **`--last-month`**: Automatically run the report for the last complete calendar month.
* **`--last-7-days`**: Run for the last 7 full days of available data.

No custom optional arguments defined for this report.


---

## Expected Output Files

This report generates the following files in the output directory:

* `output/<domain>/query-segmentation-{slug}-{start_date}-to-{end_date}.csv` (CSV dataset)
* `output/<domain>/query-segmentation-{slug}-{start_date}-to-{end_date}.html` (HTML report)

---

## How to Interpret the Report Metrics

* **Clicks**: Represents the number of times a user clicked your search result to visit your site.
* **Impressions**: The number of times your search result appeared in search results.
* **CTR (Click-Through Rate)**: The percentage of impressions that resulted in a click (`Clicks / Impressions`). A low CTR indicates snippet styling or metadata needs improvement.
* **Average Position**: The average ranking position of your URLs for the queries. A lower position (closer to 1) is better. Monitor position trends to spot algorithm updates or competitor improvements.

---

## Recommendations and Best Practices

1. **Warm the Cache First**: Run `python utilities/cache_warmer.py --file site-lists/sites.txt` to populate GSC data locally before executing batch reports.
2. **Frequency**: Generate this report monthly to identify seasonal trends and monitor organic visibility performance.
3. **Bespoke Branding**: Custom logo, primary colours, and support links can be configured in `config/branding.json`.


---

<a name="search-appearance-report"></a>

# Search Appearance Report

Generates a search appearance report for a single property or all properties in the account.
Exposes performance metrics (clicks, impressions, CTR, average position) segmented by Search Appearance.

---

## Command Line Usage

### Standard Example
```bash
python reports/search_appearance_report.py <site_url> --last-month
```

### Argument Reference
* **`site_url`** *(positional)*: The GSC property URL (e.g. `sc-domain:example.com` or `https://example.com/`).
* **`--start-date YYYY-MM-DD`**: Specify a custom start date for the analysis.
* **`--end-date YYYY-MM-DD`**: Specify a custom end date.
* **`--last-month`**: Automatically run the report for the last complete calendar month.
* **`--last-7-days`**: Run for the last 7 full days of available data.

### Optional Arguments

* **`--all-properties`**: Retrieve data for all properties in the GSC account.


---

## Expected Output Files

This report generates the following files in the output directory:

* `output/<domain>/{file_prefix}.csv` (CSV dataset)
* `output/<domain>/report-blank.html` (HTML report)
* `output/<domain>/{file_prefix}.html` (HTML report)

---

## How to Interpret the Search Appearance Report

Segment your performance metrics by Google Rich Result types (e.g. Review Snippets, FAQs, Videos, AMP, Products).

### 1. Rich Result Efficiency
* Compare CTRs of search appearances against standard web search. Rich results generally exhibit significantly higher CTR.

### 2. Schema Markup Verification
* If you deployed Structured Data (e.g. Product or FAQ Schema) but see zero impressions for that type, your schema may be invalid or not yet indexed by Google.
* Use this report to calculate the direct traffic ROI of your structured data implementation efforts.

---

## Recommendations and Best Practices

1. **Warm the Cache First**: Run `python utilities/cache_warmer.py --file site-lists/sites.txt` to populate GSC data locally before executing batch reports.
2. **Frequency**: Generate this report monthly to identify seasonal trends and monitor organic visibility performance.
3. **Bespoke Branding**: Custom logo, primary colours, and support links can be configured in `config/branding.json`.


---

<a name="search-type-performance"></a>

# Search Type Performance

No overview description available.

---

## Command Line Usage

### Standard Example
```bash
python reports/search_type_performance.py <site_url> --last-month
```

### Argument Reference
* **`site_url`** *(positional)*: The GSC property URL (e.g. `sc-domain:example.com` or `https://example.com/`).
* **`--start-date YYYY-MM-DD`**: Specify a custom start date for the analysis.
* **`--end-date YYYY-MM-DD`**: Specify a custom end date.
* **`--last-month`**: Automatically run the report for the last complete calendar month.
* **`--last-7-days`**: Run for the last 7 full days of available data.

No custom optional arguments defined for this report.


---

## Expected Output Files

This report generates the following files in the output directory:

* `output/<domain>/search-type-performance-{slug}-{start_date}-to-{end_date}.csv` (CSV dataset)
* `output/<domain>/search-type-performance-{slug}-{start_date}-to-{end_date}.html` (HTML report)

---

## How to Interpret the Report Metrics

* **Clicks**: Represents the number of times a user clicked your search result to visit your site.
* **Impressions**: The number of times your search result appeared in search results.
* **CTR (Click-Through Rate)**: The percentage of impressions that resulted in a click (`Clicks / Impressions`). A low CTR indicates snippet styling or metadata needs improvement.
* **Average Position**: The average ranking position of your URLs for the queries. A lower position (closer to 1) is better. Monitor position trends to spot algorithm updates or competitor improvements.

---

## Recommendations and Best Practices

1. **Warm the Cache First**: Run `python utilities/cache_warmer.py --file site-lists/sites.txt` to populate GSC data locally before executing batch reports.
2. **Frequency**: Generate this report monthly to identify seasonal trends and monitor organic visibility performance.
3. **Bespoke Branding**: Custom logo, primary colours, and support links can be configured in `config/branding.json`.


---

<a name="seasonal-page-spike-report"></a>

# Seasonal Page Spike Report

Generates a report identifying pages with "out of the ordinary" traffic spikes.
Adapted for the modular GSC Exporter.

---

## Command Line Usage

### Standard Example
```bash
python reports/seasonal_page_spike_report.py <site_url> --last-month
```

### Argument Reference
* **`site_url`** *(positional)*: The GSC property URL (e.g. `sc-domain:example.com` or `https://example.com/`).
* **`--start-date YYYY-MM-DD`**: Specify a custom start date for the analysis.
* **`--end-date YYYY-MM-DD`**: Specify a custom end date.
* **`--last-month`**: Automatically run the report for the last complete calendar month.
* **`--last-7-days`**: Run for the last 7 full days of available data.

### Optional Arguments

* **`--threshold`**: Z-score threshold. (default: `2.0`)
* **`--search-type`**: The search type. (default: `'web'`)


---

## Expected Output Files

This report generates the following files in the output directory:

* `output/<domain>/{file_prefix}.csv` (CSV dataset)
* `output/<domain>/{file_prefix}.html` (HTML report)

---

## How to Interpret the Report Metrics

* **Clicks**: Represents the number of times a user clicked your search result to visit your site.
* **Impressions**: The number of times your search result appeared in search results.
* **CTR (Click-Through Rate)**: The percentage of impressions that resulted in a click (`Clicks / Impressions`). A low CTR indicates snippet styling or metadata needs improvement.
* **Average Position**: The average ranking position of your URLs for the queries. A lower position (closer to 1) is better. Monitor position trends to spot algorithm updates or competitor improvements.

---

## Recommendations and Best Practices

1. **Warm the Cache First**: Run `python utilities/cache_warmer.py --file site-lists/sites.txt` to populate GSC data locally before executing batch reports.
2. **Frequency**: Generate this report monthly to identify seasonal trends and monitor organic visibility performance.
3. **Bespoke Branding**: Custom logo, primary colours, and support links can be configured in `config/branding.json`.


---

<a name="seasonal-performance-report"></a>

# Seasonal Performance Report

Generates a seasonal performance report by comparing page-level data for the same month across multiple years.
Adapted for the modular GSC Exporter.

---

## Command Line Usage

### Standard Example
```bash
python reports/seasonal_performance_report.py <site_url> --last-month
```

### Argument Reference
* **`site_url`** *(positional)*: The GSC property URL (e.g. `sc-domain:example.com` or `https://example.com/`).
* **`--start-date YYYY-MM-DD`**: Specify a custom start date for the analysis.
* **`--end-date YYYY-MM-DD`**: Specify a custom end date.
* **`--last-month`**: Automatically run the report for the last complete calendar month.
* **`--last-7-days`**: Run for the last 7 full days of available data.

### Optional Arguments

* **`--years`**: Number of years to look back. (default: `3`)


---

## Expected Output Files

This report generates the following files in the output directory:

* `output/<domain>/{file_prefix}.csv` (CSV dataset)
* `output/<domain>/{file_prefix}.html` (HTML report)

---

## How to Interpret the Report Metrics

* **Clicks**: Represents the number of times a user clicked your search result to visit your site.
* **Impressions**: The number of times your search result appeared in search results.
* **CTR (Click-Through Rate)**: The percentage of impressions that resulted in a click (`Clicks / Impressions`). A low CTR indicates snippet styling or metadata needs improvement.
* **Average Position**: The average ranking position of your URLs for the queries. A lower position (closer to 1) is better. Monitor position trends to spot algorithm updates or competitor improvements.

---

## Recommendations and Best Practices

1. **Warm the Cache First**: Run `python utilities/cache_warmer.py --file site-lists/sites.txt` to populate GSC data locally before executing batch reports.
2. **Frequency**: Generate this report monthly to identify seasonal trends and monitor organic visibility performance.
3. **Bespoke Branding**: Custom logo, primary colours, and support links can be configured in `config/branding.json`.


---

<a name="seasonal-query-spike-report"></a>

# Seasonal Query Spike Report

Generates a report identifying queries with "out of the ordinary" traffic spikes.
Adapted for the modular GSC Exporter.

---

## Command Line Usage

### Standard Example
```bash
python reports/seasonal_query_spike_report.py <site_url> --last-month
```

### Argument Reference
* **`site_url`** *(positional)*: The GSC property URL (e.g. `sc-domain:example.com` or `https://example.com/`).
* **`--start-date YYYY-MM-DD`**: Specify a custom start date for the analysis.
* **`--end-date YYYY-MM-DD`**: Specify a custom end date.
* **`--last-month`**: Automatically run the report for the last complete calendar month.
* **`--last-7-days`**: Run for the last 7 full days of available data.

### Optional Arguments

* **`--threshold`**: Z-score threshold. (default: `2.0`)
* **`--min-clicks`**: Minimum clicks. (default: `10`)


---

## Expected Output Files

This report generates the following files in the output directory:

* `output/<domain>/{file_prefix}.csv` (CSV dataset)
* `output/<domain>/{file_prefix}.html` (HTML report)

---

## How to Interpret the Report Metrics

* **Clicks**: Represents the number of times a user clicked your search result to visit your site.
* **Impressions**: The number of times your search result appeared in search results.
* **CTR (Click-Through Rate)**: The percentage of impressions that resulted in a click (`Clicks / Impressions`). A low CTR indicates snippet styling or metadata needs improvement.
* **Average Position**: The average ranking position of your URLs for the queries. A lower position (closer to 1) is better. Monitor position trends to spot algorithm updates or competitor improvements.

---

## Recommendations and Best Practices

1. **Warm the Cache First**: Run `python utilities/cache_warmer.py --file site-lists/sites.txt` to populate GSC data locally before executing batch reports.
2. **Frequency**: Generate this report monthly to identify seasonal trends and monitor organic visibility performance.
3. **Bespoke Branding**: Custom logo, primary colours, and support links can be configured in `config/branding.json`.


---

<a name="sitemap-generator"></a>

# Sitemap Generator

Generates an XML sitemap and a discovery summary based on Google Search Console data.
Uses a long date range (default 16 months) to ensure maximum URL discovery.
Refactored for modular GSC Exporter.

---

## Command Line Usage

### Standard Example
```bash
python reports/sitemap_generator.py <site_url> --last-month
```

### Argument Reference
* **`site_url`** *(positional)*: The GSC property URL (e.g. `sc-domain:example.com` or `https://example.com/`).
* **`--start-date YYYY-MM-DD`**: Specify a custom start date for the analysis.
* **`--end-date YYYY-MM-DD`**: Specify a custom end date.
* **`--last-month`**: Automatically run the report for the last complete calendar month.
* **`--last-7-days`**: Run for the last 7 full days of available data.

### Optional Arguments

* **`--lookback-months`**: No description available. (default: `16`)
* **`--min-impressions`**: Minimum impressions to include a URL. (default: `0`)


---

## Expected Output Files

This report generates the following files in the output directory:

* `output/<domain>/sitemap-urls{file_prefix}.csv` (CSV dataset)
* `output/<domain>/sitemap-summary{file_prefix}.html` (HTML report)

---

## How to Interpret the Sitemap Generator Report

This tool discovers active URLs based on GSC historical query data and outputs a search-validated XML sitemap.

### 1. Active vs. Orphaned URLs
* Compares URLs in GSC that received impressions/clicks against your internal database.
* Identifies "active" pages that Google is currently crawling and serving.

### 2. Crawl Budget Efficiency
* Sitemap files generated from search-validated URLs ensure Google prioritises crawls on pages that actually generate search visibility, optimizing your crawl budget.
* Exclude low-impression, low-value pages to prevent Google from wasting crawl resources.

---

## Recommendations and Best Practices

1. **Warm the Cache First**: Run `python utilities/cache_warmer.py --file site-lists/sites.txt` to populate GSC data locally before executing batch reports.
2. **Frequency**: Generate this report monthly to identify seasonal trends and monitor organic visibility performance.
3. **Bespoke Branding**: Custom logo, primary colours, and support links can be configured in `config/branding.json`.


---

<a name="snapshot-report"></a>

# Snapshot Report

Generates a single-period performance snapshot for a Google Search Console property.
Adapted for the modular GSC Exporter.

---

## Command Line Usage

### Standard Example
```bash
python reports/snapshot_report.py <site_url> --last-month
```

### Argument Reference
* **`site_url`** *(positional)*: The GSC property URL (e.g. `sc-domain:example.com` or `https://example.com/`).
* **`--start-date YYYY-MM-DD`**: Specify a custom start date for the analysis.
* **`--end-date YYYY-MM-DD`**: Specify a custom end date.
* **`--last-month`**: Automatically run the report for the last complete calendar month.
* **`--last-7-days`**: Run for the last 7 full days of available data.

No custom optional arguments defined for this report.


---

## Expected Output Files

This report generates the following files in the output directory:

* `output/<domain>/{base_file_prefix}-pages.csv` (CSV dataset)
* `output/<domain>/{base_file_prefix}-devices.csv` (CSV dataset)
* `output/<domain>/{base_file_prefix}-countries.csv` (CSV dataset)
* `output/<domain>/{base_file_prefix}-report.html` (HTML report)

---

## How to Interpret the Snapshot Report

This report provides a multi-dimensional summary of a site's performance for a single period.

### 1. Overall Performance Summary
* **Clicks & Impressions**: Establish the absolute traffic and visibility baseline.
* **Average CTR**: High-level indicator of search snippet relevance and clickability.
* **Average Position**: The weighted average ranking position across all query impressions.

### 2. Top Pages by Clicks & Impressions
* Identify your **Top Traffic Drivers** (high clicks) and **Brand Visibility Leaders** (high impressions).
* A page with high impressions but low clicks indicates a major click-through rate optimization opportunity.

### 3. High Impressions, Low CTR Opportunities
* Lists pages with **>= 1,000 impressions** and **< 1% CTR**.
* **Actionable Insight**: These pages are highly visible in search results but fail to attract clicks. Prioritise them for search snippet optimization (rewriting title tags, improving meta descriptions, and adding structured schema).

### 4. Performance by Device
* **Mobile vs. Desktop vs. Tablet**: Evaluate the mobile-friendliness of your site. If mobile impressions are high but CTR/Position is low, check mobile page speed, rendering, and content presentation.

### 5. Performance by Country
* Analyse geographic traffic distribution. Useful for identifying international expansion opportunities or localising content for top-performing regions.

---

## Recommendations and Best Practices

1. **Warm the Cache First**: Run `python utilities/cache_warmer.py --file site-lists/sites.txt` to populate GSC data locally before executing batch reports.
2. **Frequency**: Generate this report monthly to identify seasonal trends and monitor organic visibility performance.
3. **Bespoke Branding**: Custom logo, primary colours, and support links can be configured in `config/branding.json`.


---

<a name="url-inspection-report"></a>

# Url Inspection Report

Generates a report using the Google Search Console URL Inspection API.
Adapted for the modular GSC Exporter with intelligent property detection.

---

## Command Line Usage

### Standard Example
```bash
python reports/url_inspection_report.py --last-month
```

### Argument Reference
* **`site_url`** *(positional)*: The GSC property URL (e.g. `sc-domain:example.com` or `https://example.com/`).
* **`--start-date YYYY-MM-DD`**: Specify a custom start date for the analysis.
* **`--end-date YYYY-MM-DD`**: Specify a custom end date.
* **`--last-month`**: Automatically run the report for the last complete calendar month.
* **`--last-7-days`**: Run for the last 7 full days of available data.

### Optional Arguments

* **`site_url_or_prop`**: GSC property OR a specific URL to inspect.
* **`--url`**: No description available.
* **`--sites-file`**: File with a list of URLs to inspect.


---

## Expected Output Files

This report generates the following files in the output directory:

* `output/<domain>/{base_filename}.csv` (CSV dataset)
* `output/<domain>/{base_filename}.html` (HTML report)

---

## How to Interpret the Report Metrics

* **Clicks**: Represents the number of times a user clicked your search result to visit your site.
* **Impressions**: The number of times your search result appeared in search results.
* **CTR (Click-Through Rate)**: The percentage of impressions that resulted in a click (`Clicks / Impressions`). A low CTR indicates snippet styling or metadata needs improvement.
* **Average Position**: The average ranking position of your URLs for the queries. A lower position (closer to 1) is better. Monitor position trends to spot algorithm updates or competitor improvements.

---

## Recommendations and Best Practices

1. **Warm the Cache First**: Run `python utilities/cache_warmer.py --file site-lists/sites.txt` to populate GSC data locally before executing batch reports.
2. **Frequency**: Generate this report monthly to identify seasonal trends and monitor organic visibility performance.
3. **Bespoke Branding**: Custom logo, primary colours, and support links can be configured in `config/branding.json`.


---

