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
- **Validation**: Use `validate_all_reports.py` to verify that all modular reports are functioning correctly.
