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

* `output/<domain>/key-metrics-weekly-{slug}-{end_date}.csv` (CSV dataset)
* `output/<domain>/key-metrics-weekly-{slug}-{end_date}.html` (HTML report)
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
