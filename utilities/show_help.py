
def show_help():
    """
    Displays an overview of what each Python script in the project does.
    """
    scripts_info = {
        "key-performance-metrics.py": "Provides a monthly overview of high-level metrics (Clicks, Impressions, CTR, Position).",
        "discover-key-performance-metrics.py": "Provides a monthly overview specifically for Google Discover data.",
        "monthly-summary-report.py": "Provides a concise summary of performance for the last complete calendar month.",
        "snapshot-report.py": "Provides a detailed single-period snapshot, broken down by device and country.",
        "performance-analysis.py": "Compares two time periods (e.g., month-over-month) to identify trends.",
        "queries-pages-analysis.py": "Extends high-level metrics with unique query and page counts.",
        "query-position-analysis.py": "Tracks the distribution of query ranking positions over time with visualization.",
        "query-segmentation-report.py": "Groups top queries into position buckets to identify performance at different ranking levels.",
        "keyword-cannibalisation-report.py": "Identifies keywords where multiple pages are ranking, highlighting potential SEO issues.",
        "page-performance-over-time.py": "Tracks the performance of top pages over the last 16 months.",
        "page-performance-single-page.py": "Tracks the performance of a specific URL over the last 16 months.",
        "gsc-pages-queries.py": "Generates a detailed report showing the relationship between queries and the pages they drive traffic to.",
        "page-level-report.py": "Generates a page-level report including clicks, impressions, CTR, position, and unique query counts.",
        "url-inspection-report.py": "Fetches detailed GSC URL inspection data for a single URL or a list.",
        "generate_gsc_wrapped.py": "Creates a fun, 'Spotify Wrapped'-style annual performance summary.",
        "interactive-runner.py": "An interactive CLI tool that guides you through selecting a property and a report.",
        "show_available_domains.py": "Lists all properties in your account, grouped by root domain.",
        "generate_brand_files.py": "Automatically generates default brand-term configuration files for your sites.",
        "gsc_pages_exporter.py": "Exports all known pages from a GSC property for a given date range into CSV and HTML files.",
        "run_for_sites.py": "Executes a specified analysis script for a predefined list of GSC properties.",
        "run_all_reports_for_site.py": "Runs all primary, monthly useful GSC analysis scripts for a single domain.",
        "run_wrapped_for_all_properties.py": "Automates running the 'Wrapped' report for every site in your account.",
        "generate_index.py": "Creates an index.html file linking to all reports generated for a specific site.",
        "show_help.py": "Displays this help information."
    }

    print("="*80)
    print("Python Scripts Overview")
    print("="*80)
    
    for script, description in scripts_info.items():
        print(f"\n{script}")
        print(f"  {description}")
        
    print(f"\nFor more detailed usage, please refer to the README.md file.")
    print("="*80)

if __name__ == '__main__':
    show_help()
