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
    start_date, end_date = get_last_month_dates()
    
    reports = [
        ["reports/snapshot_report.py", site_url, "--start-date", start_date, "--end-date", end_date],
        ["reports/performance_analysis.py", site_url, "--start-date", start_date, "--end-date", end_date],
        ["reports/page_level_report.py", site_url, "--start-date", start_date, "--end-date", end_date],
        ["reports/gsc_pages_queries.py", site_url, "--start-date", start_date, "--end-date", end_date],
        ["reports/key_performance_metrics.py", site_url], # Uses --months default
        ["reports/discover_key_performance_metrics.py", site_url],
        ["reports/queries_pages_analysis.py", site_url, "--start-date", start_date, "--end-date", end_date],
        ["reports/query_position_analysis.py", site_url, "--start-date", start_date, "--end-date", end_date],
        ["reports/query_segmentation_report.py", site_url, "--start-date", start_date, "--end-date", end_date],
        ["reports/keyword_cannibalisation_report.py", site_url, "--start-date", start_date, "--end-date", end_date],
        ["reports/page_performance_over_time.py", site_url],
        ["reports/page_performance_single_page.py", site_url, "https://navigate-safety.croneri.co.uk/"], # Example URL
        ["reports/monthly_summary_report.py", site_url],
        ["reports/historical_summary_report.py", site_url],
        ["reports/consolidated_traffic_report.py", site_url],
        ["reports/image_performance_report.py", site_url],
        ["reports/monthly_search_type_performance_report.py", site_url, "--start-date", start_date, "--end-date", end_date],
        ["reports/search_type_performance.py", site_url, "--start-date", start_date, "--end-date", end_date],
        ["reports/gsc_pages_exporter.py", site_url, "--start-date", start_date, "--end-date", end_date],
        ["reports/generate_gsc_wrapped.py", site_url],
        ["reports/seasonal_performance_report.py", site_url],
        ["reports/seasonal_page_spike_report.py", site_url],
        ["reports/seasonal_query_spike_report.py", site_url],
    ]

    for report in reports:
        run_command(["python"] + report)

if __name__ == "__main__":
    main()
