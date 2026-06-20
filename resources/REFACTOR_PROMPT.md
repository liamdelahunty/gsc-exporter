# Modular Refactor: Implementation Prompt

Use the following prompt to execute the next phase of the GSC Exporter refactor.

---

**Prompt:**

Execute a modular refactor of the GSC Exporter codebase based on the plan in `resources/codebase-improvement-plan.html`.

1. **Centralise Naming Logic:** Create `core/naming.py` to standardise property-based naming. Directories must use dot-notation to preserve the exact hostname (e.g., `output/www.example.com/`). Filenames must use hyphens for SEO and readability (e.g., `page-level-report-www-example-com-...`). Ensure that domain properties are prefixed with `sc-domain.` to prevent collisions.

2. **Unified Caching:** Implement the hash-based caching system in `core/cache.py`. Use CSV for storing large tabular GSC data and JSON for accompanying metadata. The cache should be fragmented by month; if a report requests a multi-month range, the system must break this into individual monthly requests (where possible) to maximise reusability across different reports. The filename should be an MD5 hash of the granular request parameters (site_url, specific month, dimensions).

3. **Restructure Reports:** Create a `reports/` directory. Migrate `seasonal-page-spike-report.py` and `page-level-report.py` into this folder as the first "pilot" modules. Each should have a standard `run_report` function that accepts the GSC service, site URL, and relevant parameters.

4. **Core Utilities:** Move authentication and service creation into `core/client.py`. 

5. **Validation:** Update the `interactive-runner.py` to dynamically import and run these migrated reports from the new directory structure. Ensure that all generated files follow the new dot-directory and hyphen-filename convention.

Adhere to British English in all documentation and comments. Do not use em dashes.

---
