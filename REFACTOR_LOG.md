# Refactor Log: Modular GSC Exporter

## 2026-05-16: Initialisation
- Created branch `modular-refactor-setup`.
- Researched GA4 API Explorer caching and structure.
- Drafted `resources/caching-recommendations.html`.
- Drafted `resources/codebase-improvement-plan.html`.
- Standardised naming convention: Dot-notation for directories, hyphenation for filenames.
- Identified filename collision issues between www and sc-domain properties.
- Explicitly defined "Cross-report reusability" as a requirement for the new caching system.
- Added requirement for monthly fragmentation in the caching system. Long-range requests will be broken down into monthly chunks to maximise cache reusability.

## 2026-05-17: Phase 1 - Core and Pilot Reports
- Created `core/` directory with centralised logic:
    - `core/naming.py`: Dot-directory and hyphen-filename standardisation.
    - `core/client.py`: Authentication and GSC service creation.
    - `core/cache.py`: Hash-based caching with monthly fragmentation and data re-aggregation.
- Created `reports/` directory for modularised reports.
- Migrated pilot reports to `reports/`:
    - `reports/page_level_report.py`: Fully refactored to use `core.cache` and `core.naming`.
    - `reports/seasonal_page_spike_report.py`: Refactored to leverage monthly caching for historical baselines.
- Updated `interactive-runner.py`:
    - Now uses `core.client` for all authentication.
    - Points to new locations in `reports/` for pilot scripts.
- Updated `run-monthly-reports.py`:
    - Now supports modular report paths.
    - Sets `PYTHONPATH` dynamically to ensure `core` library is discoverable.
- **Automated Testing**:
    - Initialised `tests/` directory.
    - Implemented unit tests for `core/naming.py` and `core/cache.py` using `pytest`.
    - Verified 100% pass rate for naming logic and monthly data aggregation.

## 2026-05-18: Phase 2 - Alphabetical Migration and Integration Testing
- **Report Migration**: Successfully migrated and refactored the following reports:
    - `consolidated_traffic_report.py`
    - `discover_key_performance_metrics.py`
    - `generate_gsc_wrapped.py`
    - `gsc_pages_exporter.py`
    - `gsc_pages_queries.py`
    - `historical_summary_report.py`
    - `image_performance_report.py`
    - `key_performance_metrics.py`
    - `seasonal-performance-report.py`: Refactored to use `core.cache` and `core.naming`.
- `seasonal-query-spike-report.py`: Refactored to use `core.cache` and `core.naming`.
- `snapshot-report.py`: Refactored to use `core.cache` and `core.naming`.
- `url-inspection-report.py`: Refactored to use `core.naming`.
- **Standardisation**: Renamed all migrated report files to use underscores (e.g., `page_level_report.py`) to satisfy Python's module import requirements for automated testing.
- **Integration Testing**:
    - Implemented `tests/test_reports.py` using `pytest` and `pytest-mock`.
    - Verified that all 11 migrated reports (2 pilots + 9 alphabetical) execute successfully and generate output without errors.
    - Achieved a 100% pass rate for the integration test suite.
- Updated `interactive-runner.py` to point to the new underscored filenames in the `reports/` directory.

## 2026-05-20: Phase 4 - Final Synchronisation and Templating
- **Standardisation & Bug Fixes**:
    - Refactored `discover_key_performance_metrics.py`, `page_performance_over_time.py`, and `query_segmentation_report.py` to support standard CLI arguments (`--last-month`, `--start-date`, `--end-date`).
    - Fixed `KeyError: 'month'` in `historical_summary_report.py` by adding robust column detection and derivation.
    - Resolved `NameError` and pathing issues in `consolidated_traffic_report.py` by integrating `FileSystemLoader` for templates.
    - Corrected template context in `generate_gsc_wrapped.py` to ensure all "Wrapped" metrics (Impressions, CTR, Position) render correctly.
    - Updated `url_inspection_report.py` to use standard `run_report(service, site_url, ...)` signature for better integration with batch runners.
- **HTML Templating (Phase 4)**:
    - Migrated `performance_analysis.py` to use a dedicated Jinja2 template (`templates/performance-analysis-template.html`).
    - Standardised CSS and layout across migrated reports for visual consistency.
- **Standardisation & Console Transparency**:
    - **Uniform Output**: Audited all 24 reports to ensure they generate at least one CSV and one HTML file per run.
    - **Standard Announcements**: Standardised console output to explicitly list file paths: `CSV saved to: [path]` and `HTML saved to: [path]`.
    - **Expanded Reporting**: Added HTML generation to previously CSV-only reports (`Query Segmentation`, `URL Inspection`, `Seasonal Spikes`).
    - **Data Persistence**: Ensured primary data tables in visual reports (`GSC Wrapped`, `Image Performance`) are also exported to CSV for external analysis.
- **Validation**:
    - Implemented a temporary test suite to verify all 24 reports against a live GSC property.
    - Achieved a 100% pass rate for CSV and HTML generation across the entire modular suite.
- **Cleanup**:
    - Final purge of temporary test scripts and root-level artifacts.
    - Verified `PYTHONPATH` handling in all primary runners.

## 2026-05-28: State of the Project & Standardisation Roadmap
- **Investigation**: Conducted a comprehensive audit of the refactored suite.
- **Findings**:
    - **Argument Incompatibility**: Many reports lack support for standard flags (`--last-month`, `--start-date`, `--end-date`), causing crashes in batch runs.
    - **Inconsistent Definitions**: The meaning of `--last-month` varies between a single month snapshot and a 16-month trend.
    - **Runner Desynchronisation**: `interactive-runner.py` and `run-monthly-reports.py` use outdated lists of "supported" reports and flags.
    - **Documentation Drift**: `INSTRUCTIONS.md` and other resources still reference old root-level scripts.
- **Roadmap for Phase 5 (Standardisation & Validation)**:
    1. **Global Argument Standardisation**: Implement a unified CLI interface across all 24 reports.
    2. **Runner Synchronisation**: Update all runners to dynamically detect and support the standardised reports.
    3. **Historical Anchor Logic**: Standardise how date flags affect trend-based reports (e.g., dates act as the end-point for historical lookbacks).
    4. **Template Audit**: Confirm all reports correctly utilise `templates/` and `resources/` for visual consistency.
    5. **Final Validation**: Update `validate_all_reports.py` and achieve a 100% verified pass rate.

- **Phase 5 Completion (2026-05-31)**:
    - **Global Argument Standardisation**: Successfully updated all 24 reports in `reports/` to use `core.date_utils.parse_standard_date_args`.
    - **Dynamised Runners**: 
        - Refactored `interactive-runner.py` to dynamically discover reports by scanning the `reports/` directory and extracting names from docstrings.
        - Refactored `run-monthly-reports.py` to automatically include all reports in the `reports/` directory (excluding manual-input scripts like `url_inspection_report.py`).
    - **Logic Refinement**: Standardised historical lookback reports (e.g., `queries_pages_analysis.py`, `page_performance_over_time.py`) to use the passed `end_date` as the anchor for analysis.
    - **Output Standardisation**: Updated `url_inspection_report.py` to follow the standard output path and filename patterns.
    - **Final Validation**: Ran `validate_all_reports.py` and confirmed a 100% pass rate for the entire suite.

## Next Steps: Phase 6 - Cleanup & Documentation
1. **Final Purge**: Delete the `reports/original/` directory and any legacy root-level scripts.
2. **Documentation Overhaul**: 
    - Update `README.md` with the new modular architecture and unified CLI usage.
    - Refresh `INSTRUCTIONS.md` to guide users on the new dynamic runners.
3. **Refine Output Consistency**: Audit all generated filenames for strict adherence to hyphenated, SEO-friendly standards.
4. **Unit Test Expansion**: Add tests for `core/date_utils.py` and the dynamic discovery logic in runners.

## Future Enhancements
- **Concurrent Execution**: Support multi-threaded report generation for faster batch processing.
- **Enhanced Visuals**: Integrate more interactive charting libraries (e.g., Plotly) for deeper data exploration.
- **Automated Delivery**: Add support for automated email or Slack delivery of generated reports.
- **BI Connector**: Create an exporter specifically for Looker Studio or Power BI data ingestion.
