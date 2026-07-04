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
import re
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
    reports_dir = 'reports'
    exclude_files = {'drupal_dato_migration_analysis.py', 'generate_gsc_wrapped.py'}
    
    categories = [
        "High-Level Performance Summary Reports",
        "Multi-Month Trend & Historical Analysis",
        "Granular Pages & Queries Audits",
        "Specialized Traffic & Search Type Dashboards",
        "Seasonality & Spike Detection",
        "Technical SEO & Editorial Utilities",
        "Other Reports"
    ]
    
    category_mapping = {
        "snapshot_report.py": "High-Level Performance Summary Reports",
        "performance_analysis.py": "High-Level Performance Summary Reports",
        "monthly_summary_report.py": "High-Level Performance Summary Reports",
        "historical_summary_report.py": "High-Level Performance Summary Reports",
        
        "key_performance_metrics.py": "Multi-Month Trend & Historical Analysis",
        "page_performance_over_time.py": "Multi-Month Trend & Historical Analysis",
        "page_performance_single_page.py": "Multi-Month Trend & Historical Analysis",
        
        "page_level_report.py": "Granular Pages & Queries Audits",
        "gsc_pages_queries.py": "Granular Pages & Queries Audits",
        "queries_pages_analysis.py": "Granular Pages & Queries Audits",
        "keyword_cannibalisation_report.py": "Granular Pages & Queries Audits",
        "query_position_analysis.py": "Granular Pages & Queries Audits",
        "query_segmentation_report.py": "Granular Pages & Queries Audits",
        "gsc_pages_exporter.py": "Granular Pages & Queries Audits",
        
        "consolidated_traffic_report.py": "Specialized Traffic & Search Type Dashboards",
        "discover_key_performance_metrics.py": "Specialized Traffic & Search Type Dashboards",
        "image_performance_report.py": "Specialized Traffic & Search Type Dashboards",
        "search_type_performance.py": "Specialized Traffic & Search Type Dashboards",
        "monthly_search_type_performance_report.py": "Specialized Traffic & Search Type Dashboards",
        "search_appearance_report.py": "Specialized Traffic & Search Type Dashboards",
        
        "seasonal_performance_report.py": "Seasonality & Spike Detection",
        "seasonal_page_spike_report.py": "Seasonality & Spike Detection",
        "seasonal_query_spike_report.py": "Seasonality & Spike Detection",
        
        "sitemap_generator.py": "Technical SEO & Editorial Utilities",
        "url_inspection_report.py": "Technical SEO & Editorial Utilities",
        "weekly_editorial_summary_report.py": "Technical SEO & Editorial Utilities"
    }

    # Dynamically read all report files
    all_files = [f for f in os.listdir(reports_dir) if f.endswith('.py') and f != '__init__.py' and f not in exclude_files]
    
    # Group files into categories
    grouped_reports = {cat: [] for cat in categories}
    for filename in all_files:
        cat = category_mapping.get(filename, "Other Reports")
        grouped_reports[cat].append(filename)
        
    # Sort files alphabetically inside each category
    for cat in categories:
        grouped_reports[cat].sort()
        
    reports = {}
    print("\nAvailable Reports:")
    
    global_idx = 1
    for cat in categories:
        files_in_cat = grouped_reports[cat]
        if not files_in_cat:
            continue
            
        print(f"\n* {cat}:")
        for filename in files_in_cat:
            file_path = os.path.join(reports_dir, filename)
            doc_description = ""
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    match = re.search(r'"""\s*(.*?)\s*"""', content, re.DOTALL)
                    if match:
                        doc = match.group(1).split('\n')[0].strip()
                        if doc:
                            doc_description = f" - {doc.rstrip('.')}"
            except Exception:
                pass
                
            display_name = f"{filename}{doc_description}"
            key = str(global_idx)
            reports[key] = {'name': filename, 'file': file_path}
            print(f"  {global_idx:2}: {display_name}")
            global_idx += 1
            
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
    
    # Show available flags for the selected report
    print(f"\nAvailable flags for {selected_report['name']}:")
    try:
        help_output = subprocess.check_output(["python", selected_report['file'], "--help"], text=True)
        # Extract only the options section
        options_match = re.search(r'(options:|optional arguments:)(.*)', help_output, re.DOTALL | re.IGNORECASE)
        if options_match:
            print(options_match.group(2).strip())
        else:
            print("  (Could not parse help message. Refer to script documentation.)")
    except Exception:
        print("  (Could not load flags for this report.)")
    
    print("\nEnter any additional flags (e.g., --start-date YYYY-MM-DD --end-date YYYY-MM-DD, or --last-month).")
    additional_flags = input("Flags: ")
    
    # Since all reports are now standardised, we encourage using at least one date flag
    if not any(f in additional_flags for f in ['--start-date', '--end-date', '--last-month', '--lookback-months']):
        print(f"\n[!] Note: All reports now support standard date flags. Defaulting to --last-month for consistency.")
        additional_flags = "--last-month " + additional_flags

    command = ["python", selected_report['file'], selected_site]
    
    if additional_flags:
        command.extend(additional_flags.split())
        
    print(f"\nRunning: {' '.join(command)}\n")
    subprocess.run(command)

if __name__ == '__main__':
    main()
