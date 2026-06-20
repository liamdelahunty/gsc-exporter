# GSC Exporter Instructions

This guide provides instructions on how to use and customise the modular GSC Exporter suite.

## Customising HTML Reports

Most reports in the `reports/` directory generate visual HTML outputs using standardised styles. If you wish to customise the appearance of a specific report, you can modify the CSS or HTML structure within the `create_single_site_html_report` function (or equivalent) in the respective report script.

For example, in `reports/key_performance_metrics.py`, you can find the CSS styles within the f-string in `create_single_site_html_report`.

### Standard Table Header Styling

All tables in the HTML reports use a consistent dark header style. This is typically defined in the `<style>` block:

```css
.table thead th {
    background-color: #434343;
    color: #ffffff;
    text-align: left;
}
```

You can adjust these values in any individual report script to change the branding or layout.

## GSC Monitoring Report

The GSC Monitoring Report provides a weekly snapshot of key GSC metrics (`clicks`, `impressions`, `ctr`, `position`) for configured properties, allowing for proactive performance tracking.

### Usage

The report script is located at `reports/monitoring/canary_report.py`. 

To generate a report using default settings:

```bash
python reports/monitoring/canary_report.py
```

### Configuration

The script uses a JSON configuration file to define which properties to monitor. The default configuration file is `config/properties.json`.

You can specify a different configuration file using the `--config` flag:

```bash
python reports/monitoring/canary_report.py --config config/my_properties.json
```

### Options

*   `--config`: Path to the property configuration JSON file (default: `config/properties.json`).
*   `--output-dir`: Directory where the HTML report will be saved (default: `output/account`).
*   `--start-date`: Optionally set the week start date (format: `YYYY-MM-DD`). If omitted, the script dynamically detects the latest available data date from GSC to define the reporting week.
*   `--last-month`: Run for the last complete calendar month.
*   `--last-7-days`: Run for the last 7 available days.