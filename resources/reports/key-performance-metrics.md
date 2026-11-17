# Key Performance Metrics

Performs analysis of Google Search Console data, gathering key performance metrics.
Refactored for modular GSC Exporter.

---

## Command Line Usage

### Standard Example (Monthly)
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

* **`--months`**: Number of months for monthly report (default: `16`).
* **`--weekly`**: Produce reports aggregated on a weekly basis, starting on Monday and ending on Sunday.
* **`--weeks`**: Number of weeks to report on (default: `4`). Automatically enables weekly mode.

---

## Expected Output Files

This report generates the following files in the output directory:

* Monthly mode:
  * `output/<domain>/key-metrics-{slug}-{month}.csv`
  * `output/<domain>/key-metrics-{slug}-{month}.html`
* Weekly mode:
  * `output/<domain>/key-metrics-weekly-{slug}-{end-date}.csv`
  * `output/<domain>/key-metrics-weekly-{slug}-{end-date}.html`

---

## How to Interpret the Key Performance Metrics Report

A macro-level dashboard tracking site health and search type distribution over a 16-month period.

### 1. Seasonal Trends
* Spot year-over-year (YoY) changes, holiday dips, or quarterly industry trends.

### 2. Search Type Distribution
* Segment traffic across **Web, Image, Video, and News** search.
* Identify if image search or video search is a major traffic contributor, which warrants additional media optimization.

### 3. Historical Trajectory
* Assess whether SEO strategies are yielding long-term compound growth or if site-wide visibility is in decline.

---

## Recommendations and Best Practices

1. **Warm the Cache First**: Run `python utilities/cache_warmer.py --file site-lists/sites.txt` to populate GSC data locally before executing batch reports.
2. **Frequency**: Generate this report monthly to identify seasonal trends and monitor organic visibility performance.
3. **Bespoke Branding**: Custom logo, primary colours, and support links can be configured in `config/branding.json`.
