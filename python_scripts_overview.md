# Python Scripts Overview

This document provides an overview of the Python scripts in this repository.

## monthly-summary-report.py

Generates a concise account-wide or single-site summary of Google Search Console performance for the last complete calendar month. This report consolidates key performance metrics (clicks, impressions, CTR, position) and unique query/page counts into a single overview table.

## gsc_pages_exporter.py

Exports all known pages from a GSC property for a given date range into CSV and HTML files.

## gsc-pages-queries.py

Generates a detailed report showing the relationship between queries and the pages they drive traffic to, and vice-versa. The output is a CSV file and an interactive HTML report. The script can either download live data or efficiently generate reports from an existing CSV file, and includes options to limit the report size for better performance.

## performance-analysis.py

Fetches and compares key performance metrics (clicks, impressions, CTR, position) between two time periods to identify trends. The output is a detailed CSV file and an HTML report.

## snapshot-report.py

Provides a single-period overview of GSC performance, presenting various observations to understand a site's organic search presence. The output is a CSV file and an HTML report.

## key-performance-metrics.py

Provides a monthly overview of key performance metrics (clicks, impressions, CTR, average position). It can run for a single site or for all properties in a GSC account. The output is a CSV file and an HTML report.

## queries-pages-analysis.py

Extends the `key-performance-metrics.py` script by also fetching the number of unique queries and pages for each month. It can also run for a single site or for all properties in a GSC account. The output is a CSV file and an HTML report.

## query-position-analysis.py

Focuses on the distribution of query positions, breaking down clicks and impressions into predefined ranking buckets. It can also run for a single site or for all properties in a GSC account. The output is a CSV file and an HTML report.

## query-segmentation-report.py

Generates a report that segments top queries by their ranking position buckets (1-3, 4-10, 11-20, and 21+). The HTML report includes summary charts providing a visual overview of the distribution of clicks, impressions, CTR, and query counts across these segments, followed by tables showing the top queries for each bucket.

## page-performance-over-time.py

Generates a report showing the performance of the top 250 pages over the last 16 months. It identifies the top pages from the most recently completed calendar month and then fetches their performance data for each of the last 16 complete months, displaying the trends in both a CSV and an HTML file.

## generate_gsc_wrapped.py

Creates a "Google Organic Wrapped"-style annual summary for a single site. It highlights key metrics like total clicks and impressions, top-performing pages and queries, and the busiest month in a visually engaging HTML report. Date ranges can be customised.
