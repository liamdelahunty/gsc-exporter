# Python Scripts Overview

This document provides a concise overview of the Python scripts available in this repository, grouped by their primary purpose.

## Analysis and Reporting Scripts

These scripts generate detailed reports (HTML and CSV) for single sites or all properties in your account.

*   **`key-performance-metrics.py`**: A 16-month overview of high-level metrics (Clicks, Impressions, CTR, Position).
*   **`discover-key-performance-metrics.py`**: A 16-month overview specifically for Google Discover data.
*   **`monthly-summary-report.py`**: A concise summary of performance for the last complete calendar month.
*   **`historical-summary-report.py`**: Consolidates multiple monthly summary CSVs into a single historical trend report with charts.
*   **`consolidated-traffic-report.py`**: Fetches and combines performance data for Web, Discover, and News over a specified number of months.
*   **`monthly-search-type-performance-report.py`**: Generates a performance report for a specific search type (web, image, video, news) for the last complete month.
*   **`search-type-performance-report.py`**: Generates a performance report for a specific search type for a given date range.
*   **`snapshot-report.py`**: A detailed single-period snapshot, broken down by device and country.
*   **`performance-analysis.py`**: Compares two time periods (e.g., month-over-month) to highlight performance changes.
*   **`queries-pages-analysis.py`**: Extends high-level metrics with unique query and page counts.
*   **`query-position-analysis.py`**: Tracks the distribution of query ranking positions over time with visualization.
*   **`query-segmentation-report.py`**: Groups top queries into position buckets to identify performance at different ranking levels.
*   **`keyword-cannibalisation-report.py`**: Identifies keywords where multiple pages are ranking, highlighting potential SEO issues.
*   **`page-performance-over-time.py`**: Tracks the performance of top pages over the last 16 months.
*   **`page-performance-single-page.py`**: Tracks the performance of a specific URL over the last 16 months.
*   **`gsc-pages-queries.py`**: Explores the relationship between specific queries and the pages they lead to.
*   **`page-level-report.py`**: Generates a page-level report with unique query counts for each URL.
*   **`seasonal-performance-report.py`**: Compares page-level performance for the same month across multiple years. Useful for identifying seasonal content successes.
*   **`seasonal-page-spike-report.py`**: Identifies pages with "out of the ordinary" traffic spikes by analyzing monthly data over time using Z-scores.
*   **`seasonal-query-spike-report.py`**: Identifies queries with significant traffic spikes compared to their historical average.
*   **`image-performance-report.py`**: A specialized success report for Google Image Search, tracking queries, landing pages, and visual trends.
*   **`url-inspection-report.py`**: Fetches detailed GSC URL inspection data for a single URL or a list.
*   **`generate_gsc_wrapped.py`**: Creates a fun, "Spotify Wrapped"-style annual performance summary.
*   **`sitemap_generator.py`**: Generates an XML sitemap and a discovery summary based on Google Search Console data to ensure maximum URL discovery.
*   **`period_comparison_report.py`**: Compares performance across two time periods, providing charts and query-level delta analysis.
*   **`monitoring/canary_report.py`**: Provides a weekly snapshot of key GSC metrics (clicks, impressions, ctr, position) for configured properties to track proactive performance.

## Utility and Management Scripts

These scripts provide helper functions, automation, or alternative ways to run reports.

*   **`interactive-runner.py`**: An interactive CLI tool that guides you through selecting a property and a report.
*   **`show_available_domains.py`**: Lists all properties in your account, grouped by root domain.
*   **`show_data_range.py`**: Displays the first and last available data dates for a Google Search Console property.
*   **`cache_warmer.py`**: Proactively fetches and caches Google Search Console data for multiple sites to prime 'Golden Caches' (Page, Query, Page+Query, and Date) for 16 months. Automatically caps multi-dimensional granular queries to a default of 100,000 rows to prevent API pagination lag (configurable via the `--max-rows` flag).
*   **`generate_cache_inventory.py`**: Generates an inventory of cached data to track storage usage and coverage.
*   **`auth-cloud-shell.py`**: Authenticates GSC Exporter specifically for Google Cloud Shell environments, allowing custom token naming.
*   **`generate_brand_files.py`**: Automatically generates default brand-term configuration files for your sites.
*   **`gsc_pages_exporter.py`**: Exports a simple, bulk list of all discovered pages for a date range.
*   **`run_for_sites.py`**: Runs a specific analysis script for a custom list of sites.
*   **`run_all_reports_for_site.py`**: Runs a full suite of primary reports for a single site.
*   **`run-monthly-reports.py`**: Runs a suite of reports for the last calendar month for multiple sites defined in a text file.
*   **`run_wrapped_for_all_properties.py`**: Automates running the "Wrapped" report for every site in your account.
*   **`generate_index.py`**: Creates an `index.html` file linking to all reports generated for a specific site.
*   **`show_help.py`**: Displays a quick help menu with script descriptions.
