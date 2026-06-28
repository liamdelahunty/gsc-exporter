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
| `search_appearance_report.py` | Shows clicks, impressions, CTR, and average position segmented by Search Appearance (rich results). |
| `consolidated_performance_overview_report.py` | Account-wide overview of search types and search appearances across all properties (generates both section-grouped and property-grouped HTML reports). |

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

## Recommended Monthly Workflow

To generate reports most efficiently, it is highly recommended to "warm" the cache first. This process fetches the core data sets (the "Golden Caches") from the GSC API and stores them locally. Subsequent report generations will then read from this local cache, drastically reducing execution time and API quota usage.

### 1. Warm the Cache
Prime the cache for your sites (defaulting to 16 months of historical data).
```bash
python utilities/cache_warmer.py --file site-lists/sites.txt
```

### 2. Run Batch Reports
Execute the suite of standard reports for the last calendar month using the batch runner. Because the cache is warmed, this step will execute almost instantly.
```bash
python run-monthly-reports.py --sites-file site-lists/sites.txt
```

### 3. Export and Import Cache between Machines
To transfer cached responses to another machine (for example, to avoid duplicate API queries or rate-limiting), you can use the [utilities/cache_exporter.py](file:///home/liamvictor/projects/gsc-exporter/utilities/cache_exporter.py) utility:

* **Export the cache** to a compressed archive (supporting `.tar.gz`, `.tgz`, or `.zip` formats):
  ```bash
  # Export the entire cache (defaults to a dated tarball in the root directory)
  python utilities/cache_exporter.py export

  # Export cache only for a specific domain/property substring
  python utilities/cache_exporter.py export --property care-inform.com

  # Export cache filtered by date range
  python utilities/cache_exporter.py export --start-date 2026-01-01 --end-date 2026-05-31 --output my-cache.tar.gz
  ```

* **Import the cache** from an archive:
  ```bash
  # Import files without overwriting existing local cache
  python utilities/cache_exporter.py import my-cache.tar.gz

  # Import and overwrite existing local cache files
  python utilities/cache_exporter.py import my-cache.tar.gz --overwrite
  ```

## Setup

1. **Credentials**: Place your Google Cloud OAuth `client_secret.json` in the `config/` directory.
2. **Dependencies**: `pip install -r requirements.txt`
3. **Authorisation**: Run any script to trigger the one-time browser authorisation flow. It will automatically generate `config/token.json`.

## Branding Options

You can add custom branding (logos, links, text, and custom colours) to the headers and footers of generated HTML reports.

### Configuration

Create or modify `config/branding.json`. Here is a standard configuration example:

```json
{
  "enabled": true,
  "theme": {
    "primary_colour": "#2c3e50",
    "text_colour": "#ffffff",
    "font_family": "'Outfit', 'Segoe UI', sans-serif"
  },
  "header": {
    "enabled": true,
    "logo_url": "https://example.com/logo.png",
    "link_url": "https://example.com",
    "text": "My Custom Company",
    "mode": "inject"
  },
  "footer": {
    "enabled": true,
    "logo_url": "https://example.com/footer-logo.png",
    "link_url": "https://example.com",
    "text": "Generated by GSC Exporter. Customised Branding active.",
    "links": [
      {"text": "Custom Support", "url": "https://example.com/support"},
      {"text": "Privacy Policy", "url": "https://example.com/privacy"}
    ],
    "mode": "inject"
  }
}
```

### Branding Modes

For both the header and footer, you can select one of the following modes:
- `inject` (Default): Inserts your custom branding directly into the existing report header/footer while keeping the original layout and titles.
- `replace`: Completely replaces the original header/footer with your custom branded header/footer.
- `bar`: Adds a thin, modern, full-width branded bar at the very top of the page (above the header) and at the very bottom (below the footer).

### Custom Configuration Path

By default, the application looks for `config/branding.json`. You can override this:
- **Environment Variable**: Set the `GSC_BRANDING_CONFIG` environment variable to your custom JSON path.
- **Command Line**: Pass the `--branding-config <path>` flag to any report script.

For detailed guides and scenario analysis, see the `resources/` directory or view the [Index](resources/index.html).

