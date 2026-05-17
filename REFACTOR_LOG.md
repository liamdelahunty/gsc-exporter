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
    - `reports/page-level-report.py`: Fully refactored to use `core.cache` and `core.naming`.
    - `reports/seasonal-page-spike-report.py`: Refactored to leverage monthly caching for historical baselines.
- Updated `interactive-runner.py`:
    - Now uses `core.client` for all authentication.
    - Points to new locations in `reports/` for pilot scripts.
- Verified that modular reports follow the new naming convention (dot-notation for directories, hyphens for filenames).
