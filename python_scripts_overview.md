# Python Scripts Overview

This document provides an overview of the Python scripts in this repository.

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
