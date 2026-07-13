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
    """Displays a list of available sites (filtered by search term if requested)."""
    if not sites:
        return None

    filter_term = input("Enter search term to filter properties (or press Enter to list all): ").strip().lower()
    
    while True:
        filtered_sites = sites
        if filter_term:
            filtered_sites = [s for s in sites if filter_term in s.lower()]
            if not filtered_sites:
                print(f"\n[!] No properties matched '{filter_term}'. Showing all properties instead.")
                filtered_sites = sites
                filter_term = ""
        
        # Build site list with keys
        site_data = []
        for site in filtered_sites:
            site_data.append((site, get_sort_key(site)))
            
        sorted_items = sorted(site_data, key=lambda x: x[1])
        
        print("\nAvailable Google Search Console Properties:")
        if filter_term:
            print(f"(Filtered by: '{filter_term}')")
            print("  0: Reset search filter")
            
        last_root = None
        for i, (site, key) in enumerate(sorted_items):
            root_domain, priority, hostname = key
            indent = ""
            # Only indent subdomains if we're not currently filtering
            if not filter_term and root_domain == last_root:
                indent = "    "
            print(f"  {i + 1:2}: {indent}{site}")
            last_root = root_domain
            
        prompt_limit = f"1-{len(sorted_items)}"
        if filter_term:
            prompt_limit = f"0-{len(sorted_items)}"
            
        choice = input(f"\nPlease select a property ({prompt_limit}): ").strip()
        if not choice:
            continue
            
        try:
            choice_index = int(choice)
            if filter_term and choice_index == 0:
                filter_term = input("\nEnter search term to filter properties (or press Enter to list all): ").strip().lower()
                continue
                
            choice_index = choice_index - 1
            if 0 <= choice_index < len(sorted_items):
                return sorted_items[choice_index][0]
            else:
                print("Invalid selection. Please try again.")
        except ValueError:
            print("Invalid input. Please enter a valid number.")

def select_report():
    """Displays a list of available reports and prompts the user to select one."""
    reports_dir = 'reports'
    exclude_files = {
        'drupal_dato_migration_analysis.py',
        'drupal_dato_gsc_comparison_report.py',
        'generate_gsc_wrapped.py',
        'dato_pages_performance_report.py',
        'generate_migration_index.py',
        'library_marketing_migration_prioritisation_report.py',
        'library_marketing_migration_analysis.py',
        'library_quick_links_performance_report.py',
        'generate_library_migration_index.py'
    }
    
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
        "library_marketing_migration_prioritisation_report.py": "Granular Pages & Queries Audits",
        "library_marketing_migration_analysis.py": "Granular Pages & Queries Audits",
        "library_quick_links_performance_report.py": "Granular Pages & Queries Audits",
        
        "consolidated_traffic_report.py": "Specialized Traffic & Search Type Dashboards",
        "daily_performance_matrix.py": "Specialized Traffic & Search Type Dashboards",
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

def prompt_for_run_arguments(service, selected_site, selected_report):
    """
    Guides the user to build the date range and optional parameters interactively,
    and returns a list of command arguments.
    """
    from datetime import datetime, timedelta
    from dateutil.relativedelta import relativedelta
    from core.date_utils import get_latest_available_date
    
    # 1. Fetch latest GSC date for dynamic calendar options
    latest_date = get_latest_available_date(service, selected_site)
    
    # 2. Build list of last 6 calendar months
    first_of_this_month = latest_date.replace(day=1)
    months_options = []
    for i in range(1, 7):
        m_start = first_of_this_month - relativedelta(months=i)
        m_end = (first_of_this_month - relativedelta(months=i-1)) - timedelta(days=1)
        month_name = m_start.strftime("%B %Y")
        months_options.append((month_name, m_start.strftime("%Y-%m-%d"), m_end.strftime("%Y-%m-%d")))
        
    print("\nSelect Date Range Option:")
    print("  1: Last completed calendar month (Calculated automatically by GSC)")
    for idx, (name, _, _) in enumerate(months_options):
        print(f"  {idx + 2}: Specific calendar month: {name}")
    print(f"  8: Last 7 days")
    print(f"  9: Custom date range (Specify start and end dates)")
    
    date_flags = []
    while True:
        try:
            choice = input(f"Enter option (1-9): ").strip()
            if not choice:
                date_flags = ["--last-month"]
                break
            choice_val = int(choice)
            if choice_val == 1:
                date_flags = ["--last-month"]
                break
            elif 2 <= choice_val <= 7:
                month_info = months_options[choice_val - 2]
                date_flags = ["--start-date", month_info[1], "--end-date", month_info[2]]
                print(f"Selected period: {month_info[0]} ({month_info[1]} to {month_info[2]})")
                break
            elif choice_val == 8:
                date_flags = ["--last-7-days"]
                break
            elif choice_val == 9:
                start_date = ""
                while True:
                    s_input = input("Enter start date (YYYY-MM-DD): ").strip()
                    try:
                        datetime.strptime(s_input, "%Y-%m-%d")
                        start_date = s_input
                        break
                    except ValueError:
                        print("Invalid date format. Please use YYYY-MM-DD.")
                
                end_date = ""
                while True:
                    e_input = input("Enter end date (YYYY-MM-DD): ").strip()
                    try:
                        datetime.strptime(e_input, "%Y-%m-%d")
                        end_date = e_input
                        break
                    except ValueError:
                        print("Invalid date format. Please use YYYY-MM-DD.")
                date_flags = ["--start-date", start_date, "--end-date", end_date]
                break
            else:
                print("Invalid selection. Please enter a number between 1 and 9.")
        except ValueError:
            print("Invalid input. Please enter a valid number.")

    # 3. Discover and prompt for report-specific options
    discovered_flags = []
    try:
        help_output = subprocess.check_output(["python", selected_report['file'], "--help"], text=True)
        options_match = re.search(r'(options:|optional arguments:)(.*)', help_output, re.DOTALL | re.IGNORECASE)
        if options_match:
            options_text = options_match.group(2)
            # Find flag and metavar
            arg_lines = re.findall(r'^\s*(--[a-zA-Z0-9_\-]+)(?:\s+([A-Z0-9_\-]+))?.*$', options_text, re.MULTILINE)
            ignore_flags = {'--help', '--start-date', '--end-date', '--last-month', '--last-7-days'}
            for flag, metavar in arg_lines:
                if flag in ignore_flags:
                    continue
                if any(df['flag'] == flag for df in discovered_flags):
                    continue
                discovered_flags.append({
                    'flag': flag,
                    'metavar': metavar if metavar else None,
                    'options_text': options_text
                })
    except Exception:
        pass

    extra_flags = []
    if discovered_flags:
        print("\nReport-Specific Parameters Discovered:")
        for df in discovered_flags:
            flag = df['flag']
            metavar = df['metavar']
            options_txt = df['options_text']
            
            # Match description
            desc = ""
            flag_escaped = re.escape(flag)
            desc_match = re.search(rf'^\s*{flag_escaped}(?:\s+[A-Z0-9_\-]+)?\s+(.+)$', options_txt, re.MULTILINE)
            if desc_match:
                desc = desc_match.group(1).strip()
                
            desc_str = f" ({desc})" if desc else ""
            if metavar:
                user_val = input(f"  {flag}{desc_str} - Enter value (or press Enter to skip): ").strip()
                if user_val:
                    extra_flags.extend([flag, user_val])
            else:
                user_val = input(f"  {flag}{desc_str} - Enable? (y/N): ").strip().lower()
                if user_val in ['y', 'yes']:
                    extra_flags.append(flag)

    print("\nEnter any remaining custom/positional arguments (or press Enter to skip):")
    custom_input = input("Custom arguments: ").strip()
    if custom_input:
        extra_flags.extend(custom_input.split())
        
    return date_flags + extra_flags

def main():
    service = get_gsc_service()
    if not service:
        sys.exit(1)
        
    sites = get_all_sites(service)
    selected_site = select_property(sites)
    if not selected_site:
        sys.exit(1)
        
    selected_report = select_report()
    
    additional_flags = prompt_for_run_arguments(service, selected_site, selected_report)
    
    command = ["python", selected_report['file'], selected_site] + additional_flags
    
    print(f"\nRunning: {' '.join(command)}\n")
    subprocess.run(command)

if __name__ == '__main__':
    main()
