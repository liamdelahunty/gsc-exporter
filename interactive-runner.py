"""
An interactive command-line tool to run Google Search Console reports.

This script guides the user through selecting a GSC property, choosing a report,
and providing flags, before executing the chosen report script.
"""
import os
import subprocess
import sys
import argparse
import importlib.util
from urllib.parse import urlparse
from core.client import get_gsc_service

def get_all_sites(service):
    """Fetches a list of all sites in the user's GSC account."""
    sites = []
    try:
        site_list = service.sites().list().execute()
        if 'siteEntry' in site_list:
            sites = [s['siteUrl'] for s in site_list['siteEntry']]
    except HttpError as e:
        print(f"An HTTP error occurred while fetching sites: {e}")
    return sites

def get_sort_key(site_url):
    """Creates a hierarchical sort key: root domain -> type -> subdomain."""
    if site_url.startswith('sc-domain:'):
        hostname = site_url.replace('sc-domain:', '')
        priority = 0
    else:
        hostname = urlparse(site_url).netloc
        if hostname.startswith('www.'):
            priority = 1
        else:
            priority = 2

    # Extract root domain for grouping (e.g., 'croneri.co.uk')
    parts = hostname.split('.')
    # Handle common multi-part TLDs like .co.uk, .org.uk, etc.
    if len(parts) > 2 and parts[-2] in ['co', 'com', 'org', 'net', 'gov', 'edu', 'ac']:
        root_domain = '.'.join(parts[-3:])
    else:
        root_domain = '.'.join(parts[-2:])
        
    return (root_domain, priority, hostname)
def select_property(sites):
    """Displays a sorted list of sites with indentation for subdomains."""
    if not sites:
        return None

    # Create a list of (site, sort_key) tuples
    site_data = []
    for site in sites:
        site_data.append((site, get_sort_key(site)))

    # Sort the list based on the hierarchical key
    sorted_items = sorted(site_data, key=lambda x: x[1])

    print("\nAvailable Google Search Console Properties:")

    last_root = None
    for i, (site, key) in enumerate(sorted_items):
        root_domain, priority, hostname = key

        # Determine indentation
        # Indent if this isn't the first property we've seen for this root domain
        indent = ""
        if root_domain == last_root:
            indent = "    "  # 4 spaces indentation

        print(f"  {i + 1:2}: {indent}{site}")
        last_root = root_domain

    while True:
        try:
            choice = input(f"\nPlease select a property (1-{len(sorted_items)}): ")
            choice_index = int(choice) - 1
            if 0 <= choice_index < len(sorted_items):
                return sorted_items[choice_index][0]
            else:
                print("Invalid selection. Please try again.")
        except ValueError:
            print("Invalid input. Please enter a number.")

def select_report():
    """Displays a list of available reports and prompts the user to select one."""
    reports = {
        '1': {'name': 'Snapshot Report', 'file': 'reports/snapshot_report.py'},
        '2': {'name': 'Performance Analysis', 'file': 'reports/performance_analysis.py'},
        '3': {'name': 'Page-Level Report', 'file': 'reports/page_level_report.py'},
        '4': {'name': 'Queries & Pages Detailed', 'file': 'reports/gsc_pages_queries.py'},
        '5': {'name': 'Key Performance Metrics', 'file': 'reports/key_performance_metrics.py'},
        '6': {'name': 'Discover Performance Metrics', 'file': 'reports/discover_key_performance_metrics.py'},
        '7': {'name': 'Queries & Pages Summary', 'file': 'reports/queries_pages_analysis.py'},
        '8': {'name': 'Query Position Analysis', 'file': 'reports/query_position_analysis.py'},
        '9': {'name': 'Query Segmentation Report', 'file': 'reports/query_segmentation_report.py'},
        '10': {'name': 'Keyword Cannibalisation Report', 'file': 'reports/keyword_cannibalisation_report.py'},
        '11': {'name': 'Page Performance Over Time', 'file': 'reports/page_performance_over_time.py'},
        '12': {'name': 'Single Page Performance', 'file': 'reports/page_performance_single_page.py'},
        '13': {'name': 'Monthly Summary Report', 'file': 'reports/monthly_summary_report.py'},
        '14': {'name': 'Historical Summary Report', 'file': 'reports/historical_summary_report.py'},
        '15': {'name': 'Consolidated Traffic Report', 'file': 'reports/consolidated_traffic_report.py'},
        '16': {'name': 'Image Performance Report', 'file': 'reports/image_performance_report.py'},
        '17': {'name': 'Monthly Search Type Performance', 'file': 'reports/monthly_search_type_performance_report.py'},
        '18': {'name': 'Search Type Performance Report', 'file': 'reports/search_type_performance.py'},
        '19': {'name': 'URL Inspection Report', 'file': 'reports/url_inspection_report.py'},
        '20': {'name': 'Export All Pages', 'file': 'reports/gsc_pages_exporter.py'},
        '21': {'name': 'Generate GSC Wrapped', 'file': 'reports/generate_gsc_wrapped.py'},
        '22': {'name': 'Seasonal Performance (Year-over-Year)', 'file': 'reports/seasonal_performance_report.py'},
        '23': {'name': 'Seasonal Page Spikes (Z-Score)', 'file': 'reports/seasonal_page_spike_report.py'},
        '24': {'name': 'Seasonal Query Spikes (Z-Score)', 'file': 'reports/seasonal_query_spike_report.py'},
    }
    print("\nAvailable Reports:")
    for key in sorted(reports.keys(), key=int):
        print(f"  {key:2}: {reports[key]['name']}")
    while True:
        choice = input(f"\nSelect a report (1-{len(reports)}): ")
        if choice in reports:
            return reports[choice]
        print("Invalid selection.")

def main():
    service = get_gsc_service()
    if not service:
        sys.exit(1)
        
    sites = get_all_sites(service)
    selected_site = select_property(sites)
    if not selected_site:
        sys.exit(1)
        
    selected_report = select_report()
    
    # Reports that require date arguments
    DATE_REQUIRING_SCRIPTS = [
        'reports/snapshot_report.py',
        'reports/performance_analysis.py',
        'reports/page_level_report.py',
        'reports/gsc_pages_queries.py',
        'reports/discover_key_performance_metrics.py',
        'reports/keyword_cannibalisation_report.py',
        'reports/page_performance_over_time.py',
        'reports/monthly_summary_report.py',
        'reports/gsc_pages_exporter.py',
        'reports/monthly_search_type_performance_report.py',
        'reports/search_type_performance.py'
    ]
    
    # Reports that use --months instead of --start-date/--end-date
    MONTHS_BASED_SCRIPTS = [
        'reports/queries_pages_analysis.py',
        'reports/query_position_analysis.py',
        'reports/key_performance_metrics.py'
    ]

    print("\nEnter any additional flags (e.g., --start-date YYYY-MM-DD --end-date YYYY-MM-DD, or --last-month).")
    additional_flags = input("Flags: ")
    
    # If report needs dates and no date flag was provided, append --last-month
    if selected_report['file'] in DATE_REQUIRING_SCRIPTS:
        if not any(f in additional_flags for f in ['--start-date', '--end-date', '--last-month', '--last-7-days', '--last-28-days']):
            print(f"\n[!] Note: {selected_report['name']} requires date flags. Defaulting to --last-month.")
            additional_flags = "--last-month " + additional_flags
    # If report needs --months, do nothing as it's not a date flag report
    elif selected_report['file'] in MONTHS_BASED_SCRIPTS:
        pass    
    command = ["python", selected_report['file'], selected_site]
    
    if additional_flags:
        command.extend(additional_flags.split())
        
    print(f"\nRunning: {' '.join(command)}\n")
    subprocess.run(command)

if __name__ == '__main__':
    main()
