
"""
A helper script to batch run GSC reports for validation.
"""
import subprocess
import os
import sys
from datetime import datetime, timedelta

def get_last_month_dates():
    today = datetime.now()
    first_day_current_month = today.replace(day=1)
    last_day_last_month = first_day_current_month - timedelta(days=1)
    first_day_last_month = last_day_last_month.replace(day=1)
    return first_day_last_month.strftime('%Y-%m-%d'), last_day_last_month.strftime('%Y-%m-%d')

def run_command(command):
    print(f"\nRunning: {' '.join(command)}")
    result = subprocess.run(command, capture_output=True, text=True)
    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print(f"ERRORS:\n{result.stderr}")
    return result.returncode

def main():
    site_url = "sc-domain:croneri-navigate-safety.co.uk"
    
    reports = [
        ["reports/snapshot_report.py", site_url, "--last-month"],
        ["reports/performance_analysis.py", site_url, "--last-month"],
        ["reports/page_level_report.py", site_url, "--last-month"],
        ["reports/gsc_pages_queries.py", site_url, "--last-month"],
        ["reports/key_performance_metrics.py", site_url, "--last-month"],
        ["reports/discover_key_performance_metrics.py", site_url, "--last-month"],
        ["reports/queries_pages_analysis.py", site_url, "--last-month"],
        ["reports/query_position_analysis.py", site_url, "--last-month"],
        ["reports/query_segmentation_report.py", site_url, "--last-month"],
        ["reports/keyword_cannibalisation_report.py", site_url, "--last-month"],
        ["reports/page_performance_over_time.py", site_url, "--last-month"],
        ["reports/page_performance_single_page.py", site_url, "https://navigate-safety.croneri.co.uk/", "--last-month"],
        ["reports/monthly_summary_report.py", site_url, "--last-month"],
        ["reports/historical_summary_report.py", site_url, "--last-month"],
        ["reports/consolidated_traffic_report.py", site_url, "--last-month"],
        ["reports/image_performance_report.py", site_url, "--last-month"],
        ["reports/monthly_search_type_performance_report.py", site_url, "--last-month"],
        ["reports/search_type_performance.py", site_url, "--last-month"],
        ["reports/gsc_pages_exporter.py", site_url, "--last-month"],
        ["reports/generate_gsc_wrapped.py", site_url, "--last-month"],
        ["reports/seasonal_performance_report.py", site_url, "--last-month"],
        ["reports/seasonal_page_spike_report.py", site_url, "--last-month"],
        ["reports/seasonal_query_spike_report.py", site_url, "--last-month"],
        ["reports/url_inspection_report.py", site_url, "--last-month"],
        ["reports/search_appearance_report.py", site_url, "--last-month"],
        ["reports/consolidated_performance_overview_report.py", site_url, "--last-month"],
    ]

    for report in reports:
        run_command(["python"] + report)

if __name__ == "__main__":
    main()
