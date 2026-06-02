# Google Search Console Exporter

A modular suite of tools for exporting and analysing Google Search Console data into CSV and HTML formats.

## Architecture

The project has been refactored into a modular structure:
- `core/`: Centralised library for caching, naming, and GSC API clients.
- `reports/`: All analysis scripts, standardised with a unified CLI interface.
- `templates/`: Jinja2 HTML templates for visual reporting.
- `output/`: Generated reports, organised by property (e.g., `output/www.example.com/`).
- `cache/`: Hash-based GSC API cache, fragmented by month for maximum reusability.

## Standard CLI Interface

All reports in the `reports/` directory support a standardised set of arguments:

- `python reports/[report_name].py <site_url>`
- `--last-7-days`: Run for the last 7 full days of available data.
- `--last-28-days`: Run for the last 28 full days.
- `--last-month`: Run for the last complete calendar month.
- `--start-date YYYY-MM-DD`: Specify a custom start date.
- `--end-date YYYY-MM-DD`: Specify a custom end date.

*Note: Date flags are dynamic and anchored to the latest available data in GSC, accounting for the typical 2-3 day processing lag.*

## Key Reports

| Report | Description |
| --- | --- |
| `period_comparison_report.py` | **NEW:** Compare performance between two periods with interactive charts and query deltas. |
| `performance_analysis.py` | Detailed comparison highlighting rising stars, content decay, and high-value opportunities. |
| `page_level_report.py` | Page-centric view with unique query counts and core performance metrics. |
| `gsc_pages_queries.py` | Interactive "drill-down" report exploring the relationship between pages and queries. |
| `key_performance_metrics.py` | High-level 16-month overview of account or site health. |
| `query_position_analysis.py` | Tracks ranking distribution over 16 months with trend charts. |
| `snapshot_report.py` | Detailed single-period overview including device and country breakdowns. |
| `keyword_cannibalisation_report.py` | Identifies queries where multiple pages are competing in search results. |

## Dynamic Runners

Instead of running individual reports, you can use our dynamic runners:

### 1. Interactive Runner
Guided execution to help you select a property and report.
```bash
python interactive-runner.py
```

### 2. Monthly Batch Runner
Runs a suite of reports for the last calendar month for multiple sites.
```bash
python run-monthly-reports.py --sites-file site-lists/sites.txt
```

### 3. Site Suite Runner
Runs all primary analysis reports for a single domain in one command.
```bash
python run_all_reports_for_site.py <site_url> --last-month
```

## Setup

1. **Credentials**: Place your Google Cloud OAuth `client_secret.json` in the root directory.
2. **Dependencies**: `pip install -r requirements.txt`
3. **Authorisation**: Run any script to trigger the one-time browser authorisation flow.

For detailed guides and scenario analysis, see the `resources/` directory or view the [Index](resources/index.html).
