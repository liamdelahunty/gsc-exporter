"""
An interactive command-line tool to run Google Search Console reports.

This script guides the user through selecting a GSC property, choosing a report,
and providing flags, before executing the chosen report script.
"""
import os
import subprocess
import sys
from google_auth_oauthlib.flow import InstalledAppFlow
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
            
            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        
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
    """Creates a sort key for a site URL to group by root domain."""
    if site_url.startswith('sc-domain:'):
        root_domain = site_url.replace('sc-domain:', '')
        # Sort sc-domain properties first
        return (root_domain, 0)
    else:
        netloc = urlparse(site_url).netloc
        parts = netloc.split('.')
        # A simple way to get the root domain, not perfect but good for sorting
        if len(parts) > 2 and parts[-2] in ['co', 'com', 'org', 'net', 'gov', 'edu']:
             root_domain = '.'.join(parts[-3:])
        else:
             root_domain = '.'.join(parts[-2:])
        # Sort non-sc-domain properties second
        return (root_domain, 1)

def select_property(sites):
    """Displays a sorted list of sites and prompts the user to select one."""
    if not sites:
        print("No sites found in your GSC account.")
        return None
    
    sorted_sites = sorted(sites, key=get_sort_key)
    
    print("\nAvailable Google Search Console Properties:")
    for i, site in enumerate(sorted_sites):
        print(f"  {i + 1}: {site}")
        
    while True:
        try:
            choice = input(f"\nPlease select a property (1-{len(sorted_sites)}): ")
            choice_index = int(choice) - 1
            if 0 <= choice_index < len(sorted_sites):
                return sorted_sites[choice_index]
            else:
                print("Invalid selection. Please try again.")
        except ValueError:
            print("Invalid input. Please enter a number.")

def select_report():
    """Displays a list of available reports and prompts the user to select one."""
    reports = {
        '1': {'name': 'Snapshot Report', 'file': 'snapshot-report.py'},
        '2': {'name': 'Performance Analysis (Period Comparison)', 'file': 'performance-analysis.py'},
        '3': {'name': 'Page-Level Report', 'file': 'page-level-report.py'},
        '4': {'name': 'Queries & Pages Detailed (gsc-pages-queries)', 'file': 'gsc-pages-queries.py'},
        '5': {'name': 'Key Performance Metrics (16 months)', 'file': 'key-performance-metrics.py'},
        '6': {'name': 'Discover Performance Metrics (16 months)', 'file': 'discover-key-performance-metrics.py'},
        '7': {'name': 'Queries & Pages Summary (16 months)', 'file': 'queries-pages-analysis.py'},
        '8': {'name': 'Query Position Analysis (16 months)', 'file': 'query-position-analysis.py'},
        '9': {'name': 'Query Segmentation Report', 'file': 'query-segmentation-report.py'},
        '10': {'name': 'Keyword Cannibalisation Report', 'file': 'keyword-cannibalisation-report.py'},
        '11': {'name': 'Page Performance Over Time (Top 250)', 'file': 'page-performance-over-time.py'},
        '12': {'name': 'Monthly Summary Report (All/Single Site)', 'file': 'monthly-summary-report.py'},
        '13': {'name': 'Export All Pages', 'file': 'gsc_pages_exporter.py'},
        '14': {'name': 'URL Inspection Report', 'file': 'url-inspection-report.py'},
        '15': {'name': 'Generate GSC Wrapped', 'file': 'generate_gsc_wrapped.py'},
    }

    print("\nAvailable Reports:")
    # Sort keys as integers to ensure numerical order
    for key in sorted(reports.keys(), key=int):
        report = reports[key]
        print(f"  {key:2}: {report['name']} ({report['file']})")

    while True:
        choice = input(f"\nSelect a report to run (1-{len(reports)}): ")
        if choice in reports:
            return reports[choice]
        else:
            print("Invalid selection. Please try again.")

def get_report_flags():
    """Prompts the user to enter any additional flags for the report."""
    print("\nEnter any additional flags for the report (e.g., --last-7-days --compare-to-previous-year).")
    print("Press Enter to run without additional flags.")
    return input("Flags: ")

def main():
    """Main function to run the interactive report generator."""
    service = get_gsc_service()
    if not service:
        print("Failed to get GSC service. Exiting.")
        sys.exit(1)
        
    sites = get_all_sites(service)
    selected_site = select_property(sites)
    
    if not selected_site:
        sys.exit(1)
        
    selected_report = select_report()
    
    # Special handling for single-page report (it takes a page URL, not a site URL)
    # But for now I'll just keep the ones that take site_url as the main argument.
    
    additional_flags = get_report_flags()
    
    command = [
        "python",
        selected_report['file'],
        selected_site
    ]
    
    if additional_flags:
        # Split the flags string into a list of arguments
        command.extend(additional_flags.split())
        
    print("\n" + "-"*50)
    print(f"Running command: {' '.join(command)}")
    print("-"*50 + "\n")
    
    try:
        # Using subprocess.run to execute the command and stream output
        process = subprocess.run(command)
    except FileNotFoundError:
        print(f"Error: The script '{selected_report['file']}' was not found.")
    except subprocess.CalledProcessError as e:
        print(f"An error occurred while running the report: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == '__main__':
    main()
