
def show_help():
    """
    Displays an overview of what each Python script in the project does.
    """
    scripts_info = {
        "gsc_pages_exporter.py": "Exports all known pages from a GSC property for a given date range into CSV and HTML files.",
        "gsc-pages-queries.py": "Generates a detailed report showing the relationship between queries and the pages they drive traffic to, and vice-versa. The output is a CSV file and an interactive HTML report.",
        "page-level-report.py": "Generates a page-level report including clicks, impressions, CTR, position, and unique query counts for each URL.",
        "performance-analysis.py": "Fetches and compares key performance metrics (clicks, impressions, CTR, position) between two time periods to identify trends. The output is a detailed CSV file and an HTML report.",
        "snapshot-report.py": "Provides a single-period overview of GSC performance, presenting various observations to understand a site's organic search presence. The output is a CSV file and an HTML report.",
        "key-performance-metrics.py": "Provides a monthly overview of key performance metrics (clicks, impressions, CTR, average position). It can run for a single site or for all properties in a GSC account. The output is a CSV file and an HTML report.",
        "queries-pages-analysis.py": "Extends the `key-performance-metrics.py` script by also fetching the number of unique queries and pages for each month. It can also run for a single site or for all properties in a GSC account. The output is a CSV file and an HTML report.",
        "query-position-analysis.py": "Focuses on the distribution of query positions, breaking down clicks and impressions into predefined ranking buckets. It can also run for a single site or for all properties in a GSC account. The output is a CSV file and an HTML report.",
        "query-segmentation-report.py": "Groups top queries into position buckets (1-3, 4-10, etc.) to identify high-performance keywords at different ranking levels.",
        "run_for_sites.py": "Executes a specified analysis script for a predefined list of GSC properties. This is useful for running reports on a specific subset of your sites.",
        "run_all_reports_for_site.py": "Runs all primary, monthly useful GSC analysis scripts for a single specified domain, automating the generation of a full suite of common reports.",
        "run_all.bat": "Executes all python scripts for a given site URL. After the scripts finish running, an index.html file will be generated in the output/<hostname>/ directory. This index.html file will contain links to all the generated HTML reports for that specific site.",
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
