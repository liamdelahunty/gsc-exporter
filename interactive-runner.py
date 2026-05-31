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
    report_files = sorted([f for f in os.listdir(reports_dir) if f.endswith('.py') and f != '__init__.py'])
    
    reports = {}
    print("\nAvailable Reports:")
    
    for i, filename in enumerate(report_files):
        file_path = os.path.join(reports_dir, filename)
        
        # Try to extract a name from the docstring
        name = filename.replace('_', ' ').replace('.py', '').title()
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                # Simple docstring extraction
                match = re.search(r'"""\s*(.*?)\s*"""', content, re.DOTALL)
                if match:
                    doc = match.group(1).split('\n')[0].strip()
                    if doc:
                        name = doc.rstrip('.')
        except Exception:
            pass
            
        key = str(i + 1)
        reports[key] = {'name': name, 'file': file_path}
        print(f"  {key:2}: {name}")
        
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
    
    print("\nEnter any additional flags (e.g., --start-date YYYY-MM-DD --end-date YYYY-MM-DD, or --last-month).")
    additional_flags = input("Flags: ")
    
    # Since all reports are now standardised, we encourage using at least one date flag
    if not any(f in additional_flags for f in ['--start-date', '--end-date', '--last-month']):
        print(f"\n[!] Note: All reports now support standard date flags. Defaulting to --last-month for consistency.")
        additional_flags = "--last-month " + additional_flags

    command = ["python", selected_report['file'], selected_site]
    
    if additional_flags:
        command.extend(additional_flags.split())
        
    print(f"\nRunning: {' '.join(command)}\n")
    subprocess.run(command)

if __name__ == '__main__':
    main()
