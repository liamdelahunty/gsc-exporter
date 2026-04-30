"""
An interactive command-line tool to run Google Search Console reports.

This script guides the user through selecting a GSC property, choosing a report,
and providing flags, before executing the chosen report script.
"""
import os
import subprocess
import sys
import argparse
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.auth import exceptions
from urllib.parse import urlparse

# --- Configuration ---
SCOPES = ['https://www.googleapis.com/auth/webmasters.readonly']
CLIENT_SECRET_FILE = 'client_secret.json'
TOKEN_FILE = 'token.json'

def get_gsc_service():
    """Authenticates and returns a Google Search Console service object."""
    creds = None
    if os.path.exists(TOKEN_FILE):
        try:
            creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
        except Exception as e:
            print(f"Could not load credentials from {TOKEN_FILE}. Error: {e}")
            print("Will attempt to re-authenticate.")
            creds = None

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                print("Credentials have expired. Attempting to refresh...")
                creds.refresh(Request())
            except exceptions.RefreshError as e:
                print(f"Error refreshing token: {e}")
                print("The refresh token is expired or revoked. Deleting it and re-authenticating.")
                if os.path.exists(TOKEN_FILE):
                    os.remove(TOKEN_FILE)
                creds = None
        
        if not creds:
            if not os.path.exists(CLIENT_SECRET_FILE):
                print(f"Error: {CLIENT_SECRET_FILE} not found. Please follow setup instructions in README.md.")
                return None
            
            # Optimized for Cloud Shell: we expect the user to have generated a token already.
            print(f"Error: {TOKEN_FILE} not found.")
            print(f"Please run 'python auth-cloud-shell.py' to generate authentication.")
            return None
        
        with open(TOKEN_FILE, 'w') as token:
            token.write(creds.to_json())
            print("Authentication successful. Credentials saved.")

    return build('webmasters', 'v3', credentials=creds)

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
        '1': {'name': 'Snapshot Report', 'file': 'snapshot-report.py'},
        '2': {'name': 'Performance Analysis', 'file': 'performance-analysis.py'},
        '3': {'name': 'Page-Level Report', 'file': 'page-level-report.py'},
        '4': {'name': 'Queries & Pages Detailed', 'file': 'gsc-pages-queries.py'},
        '5': {'name': 'Key Performance Metrics', 'file': 'key-performance-metrics.py'},
        '6': {'name': 'Discover Performance Metrics', 'file': 'discover-key-performance-metrics.py'},
        '7': {'name': 'Queries & Pages Summary', 'file': 'queries-pages-analysis.py'},
        '8': {'name': 'Query Position Analysis', 'file': 'query-position-analysis.py'},
        '9': {'name': 'Query Segmentation Report', 'file': 'query-segmentation-report.py'},
        '10': {'name': 'Keyword Cannibalisation Report', 'file': 'keyword-cannibalisation-report.py'},
        '11': {'name': 'Page Performance Over Time', 'file': 'page-performance-over-time.py'},
        '12': {'name': 'Monthly Summary Report', 'file': 'monthly-summary-report.py'},
        '13': {'name': 'Export All Pages', 'file': 'gsc_pages_exporter.py'},
        '14': {'name': 'URL Inspection Report', 'file': 'url-inspection-report.py'},
        '15': {'name': 'Generate GSC Wrapped', 'file': 'generate_gsc_wrapped.py'},
        '16': {'name': 'Monthly Search Type Performance Report', 'file': 'monthly-search-type-performance-report.py'},
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
    
    print("\nEnter any additional flags (e.g., --last-7-days). Press Enter for none.")
    additional_flags = input("Flags: ")
    
    command = ["python", selected_report['file'], selected_site]
    
    if additional_flags:
        command.extend(additional_flags.split())
        
    print(f"\nRunning: {' '.join(command)}\n")
    subprocess.run(command)

if __name__ == '__main__':
    main()
