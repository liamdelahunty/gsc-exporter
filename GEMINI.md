# GSC Exporter Project Instructions

This repository contains a modular suite of tools for exporting and analysing Google Search Console data.

## Project Structure

- `core/`: Centralised library for shared logic.
    - `client.py`: GSC API authentication and service creation.
    - `cache.py`: Hash-based caching with monthly fragmentation.
    - `naming.py`: Standardised property-based directory and filename generation.
    - `brand.py`: Brand detection and query classification.
- `reports/`: Modular report scripts. Each script should follow the underscore naming convention (e.g., `page_level_report.py`) and provide a `run_report` function.
- `templates/`: HTML templates for report generation (Jinja2).
- `output/`: Generated CSV and HTML reports, organised by property (e.g., `output/sc-domain.example.com/`).
- `cache/`: Cached GSC API responses (fragmented by month).

## Conventions

- **Naming**: 
    - Output directories: Dot-notation for hostnames (e.g., `sc-domain.example.com`).
    - Output filenames: Hyphen-separated for SEO and readability (e.g., `snapshot-report-sc-domain-example-com-...`).
    - Python modules: Underscore-separated for import compatibility.
- **CLI Interface**: All reports must support the standard arguments:
    - `--start-date YYYY-MM-DD`
    - `--end-date YYYY-MM-DD`
    - `--last-month` (Anchor for historical reports)
- **Language**: Use British English in documentation, comments, and responses. Avoid em dashes.
- **Reporting**: Every report run should generate at least one CSV and one HTML file. Console output must explicitly list the paths to these files.

## Workflows

- **Run Reports**: Use `interactive-runner.py` for guided execution or `run-monthly-reports.py` for batch processing.
- **Validation**: Use `utilities/validate_all_reports.py` to verify that all modular reports are functioning correctly.

## Planned interactive-runner.py Improvements

- **Interactive Date & Flag Prompter**: Guide users step-by-step through date selection (last month, preset ranges, or custom input validation) and parameter selection (e.g. limits), rather than requesting raw CLI flags.
- **Property Search & Filter**: Prompt users to filter GSC properties by typing search terms to quickly narrow down large lists.
- **Execution History Memory**: Save the last 5 successful executions to `config/runner-history.json` and offer a quick rerun option on launch.
- **Sequential Multi-Property Run**: Enable running a report across multiple comma-separated properties or all properties sequentially.
- **Direct Link Printout**: Parse output paths from console streams and print active `file://` links to generated HTML and CSV files upon execution success.
