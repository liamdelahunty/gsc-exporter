# Future Developments for Google Search Console Exporter

Following the completion of the modular refactor (Release Candidate 1), this document outlines proposed future developments for the `gsc-exporter` codebase. These enhancements are grouped by area of impact.

---

## 1. Performance and Orchestration

### Concurrent Batch Execution
* **Current State**: The batch runner ([run-monthly-reports.py](file:///home/liamvictor/Code/gsc-exporter/run-monthly-reports.py)) and the site runner ([run_all_reports_for_site.py](file:///home/liamvictor/Code/gsc-exporter/run_all_reports_for_site.py)) execute reports sequentially.
* **Proposed Enhancement**: Implement thread-based concurrent execution using Python's `concurrent.futures` module. This will speed up multi-site and multi-report generation, particularly since execution is largely file-I/O and network-bound.
* **Benefit**: Dramatically reduces the run time of monthly batch exports across dozens of properties.

### Smart Cache Invalidation and Refresh Flags
* **Current State**: The caching layer in [core/cache.py](file:///home/liamvictor/Code/gsc-exporter/core/cache.py) retrieves files based on hashed query parameters. There is no mechanism to bypass the cache.
* **Proposed Enhancement**: 
  * Add a global `--bypass-cache` (or `--refresh`) command-line flag to force-refresh data from the GSC API.
  * Implement an optional Time-To-Live (TTL) or maximum age check for cached partial months (e.g. current month data) to prevent stale data.
* **Benefit**: Ensures access to the latest data when Search Console retroactively corrects historical reports.

---

## 2. Interactive Visualisation and Interface

### Lightweight Web Dashboard
* **Current State**: Orchestration is CLI-based via [interactive-runner.py](file:///home/liamvictor/Code/gsc-exporter/interactive-runner.py), and outputs are static HTML pages.
* **Proposed Enhancement**: Build a browser-based dashboard application (using a framework like Streamlit, Flask, or FastAPI). The interface would feature a premium dark-mode theme, letting users select properties, select date ranges, trigger reports, and inspect visual tables interactively.
* **Benefit**: Lowers the barrier to entry for non-technical stakeholders and offers a centralised workspace.

### Interactive Plotly Charts
* **Current State**: HTML reports use static Bootstrap tables and basic Chart.js line charts.
* **Proposed Enhancement**: Upgrade to Plotly or integrate dynamic, responsive Chart.js extensions. This will allow for zoomable, hoverable time-series charts, scatter plots for query positioning, and dynamic comparison sliders.
* **Benefit**: Enhances data exploration, allowing analysts to drill down into specific data points without running new reports.

---

## 3. Data Analytics and Intelligence

### Semantic Query and Topic Clustering
* **Current State**: Brand classification ([core/brand.py](file:///home/liamvictor/Code/gsc-exporter/core/brand.py)) splits queries into brand vs non-brand. Segment reports rely on hardcoded query rules.
* **Proposed Enhancement**: Integrate a lightweight Natural Language Processing (NLP) or TF-IDF clustering utility. This will automatically group keywords into semantic topics and intents (informational, transactional, navigational).
* **Benefit**: Automatically groups hundreds of long-tail queries into digestible themes.

### Automated Anomaly Detection and Alerts
* **Current State**: [canary_report.py](file:///home/liamvictor/Code/gsc-exporter/reports/monitoring/canary_report.py) calculates week-on-week, month-on-month, and year-on-year changes but relies on fixed percentage thresholds.
* **Proposed Enhancement**: Incorporate statistical anomaly detection (such as standard deviation thresholding or isolation forests) to identify sudden, statistically significant drops in clicks or impressions.
* **Benefit**: Flags algorithmic penalties or technical website issues automatically without manual inspection.

---

## 4. Distribution and Integrations

### Automated Stakeholder Delivery
* **Current State**: Reports are saved locally to the [output/](file:///home/liamvictor/Code/gsc-exporter/output/) directory.
* **Proposed Enhancement**: 
  * Add a Slack webhook integration to send high-level text summaries and HTML download links directly to channels.
  * Add SMTP or SendGrid support to email PDF/HTML attachments to a mailing list.
* **Benefit**: Streamlines reporting workflows and ensures automated weekly or monthly delivery.

### Business Intelligence and BigQuery Connectors
* **Current State**: Outputs are limited to CSV files and standalone HTML files.
* **Proposed Enhancement**: Create a utility to export cleaned GSC datasets directly to a Google BigQuery table or a structured schema suited for Looker Studio and Power BI.
* **Benefit**: Facilitates standard reporting pipelines and multi-data source blending.

---

## 5. Export Extensions

### Multi-Tab Excel Export
* **Current State**: Individual tables are saved as separate CSV files.
* **Proposed Enhancement**: Create an Excel exporter using `openpyxl` or `xlsxwriter` that packages all CSVs from a single report run into a single multi-tab spreadsheet.
* **Benefit**: Improves document management and simplifies sharing data sets with clients.
