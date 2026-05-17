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
    - `keyword_cannibalisation_report.py`
- **Standardisation**: Renamed all migrated report files to use underscores (e.g., `page_level_report.py`) to satisfy Python's module import requirements for automated testing.
- **Integration Testing**:
    - Implemented `tests/test_reports.py` using `pytest` and `pytest-mock`.
    - Verified that all 11 migrated reports (2 pilots + 9 alphabetical) execute successfully and generate output without errors.
    - Achieved a 100% pass rate for the integration test suite.
- Updated `interactive-runner.py` to point to the new underscored filenames in the `reports/` directory.
