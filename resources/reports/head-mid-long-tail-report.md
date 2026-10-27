# Head, Mid Tail & Long Tail Search Traffic Report

Analyses and breaks down organic search performance into **Head**, **Mid Tail**, and **Long Tail** query segments across both lexical word length and traffic volume demand curve tiers.

---

## Command Line Usage

### Standard Example
```bash
python reports/head_mid_long_tail_report.py sc-domain:example.com --last-month
```

### Argument Reference
* **`site_url`** *(positional)*: The GSC property URL (e.g. `sc-domain:example.com` or `https://example.com/`).
* **`--start-date YYYY-MM-DD`**: Specify a custom start date for the analysis.
* **`--end-date YYYY-MM-DD`**: Specify a custom end date for the analysis.
* **`--last-month`**: Automatically run the report for the last complete calendar month.
* **`--last-7-days`**: Run for the last 7 full days of available data.
* **`--limit`**: Maximum number of top queries rendered in the interactive HTML table (default: `500`). Full queries are always saved in the companion CSV.

---

## Expected Output Files

This report generates the following files in the site output directory:

* `output/<property>/head-mid-long-tail-{slug}-{start_date}-to-{end_date}-summary.csv` (Segmented KPIs and demand curve aggregates)
* `output/<property>/head-mid-long-tail-{slug}-{start_date}-to-{end_date}-queries.csv` (Complete query dataset with word count, tail classifications, and brand tagging)
* `output/<property>/head-mid-long-tail-{slug}-{start_date}-to-{end_date}.html` (Interactive visual dashboard with Chart.js visualisations and filterable query explorer)

---

## Segmentation Methodology

The report analyses query distribution across two standard industry dimensions:

### 1. Lexical Word-Count Segmentation
* **Head Queries (1 to 2 words)**: Broad, high-level terms that frequently represent high competition and brand navigational searches.
* **Mid-Tail Queries (3 to 4 words)**: Specific multi-word phrases displaying moderate search intent.
* **Long-Tail Queries (5+ words)**: Highly specific, question-based, or problem-solving queries that typically exhibit higher conversion intent.

### 2. Search Demand Curve (Click Volume Tiers)
* **Head / High Volume**: Queries generating 50 or more clicks during the period.
* **Mid Tail / Moderate Volume**: Queries generating between 5 and 49 clicks.
* **Long Tail / Low Volume**: Queries generating 1 to 4 clicks.
* **Zero-Click Queries**: Queries that received impressions but 0 clicks.

### 3. Brand vs Non-Brand Intersect
Each query is checked against domain brand terms using automatic detection and custom configuration (`config/brand-terms-{slug}.txt`) to evaluate how much head and long-tail visibility stems from brand equity versus generic organic reach.

---

## Recommendations and Best Practices

1. **Protect Head Terms with Brand Defence**: High click volume head queries often contain brand terms or core category keywords. Ensure canonical tags and metadata are optimised.
2. **Expand Content Clusters for Long Tail**: Long-tail queries that achieve high impressions but low click-through rates reveal prime opportunities to publish targeted FAQ sections and detailed content guides.
3. **Warm the Cache First**: Run `python utilities/cache_warmer.py` or fetch with standard date ranges to leverage local monthly fragmented caching.
