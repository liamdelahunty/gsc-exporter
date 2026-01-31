"""
Exports all pages from a Google Search Console property to a CSV and an HTML file.

This script authenticates with the Google Search Console API, fetches all pages for a
specified site, and then saves the list of pages to a CSV file and an HTML file.

Usage:
    python gsc_pages_exporter.py <site_url> [--start-date <start_date>] [--end-date <end_date>]

Example:
    python gsc_pages_exporter.py https://www.example.com
    python gsc_pages_exporter.py https://www.example.com --start-date 2025-01-01 --end-date 2025-01-31
"""
import os
import pandas as pd
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.auth import exceptions
from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta
from urllib.parse import urlparse
import math
import argparse

# --- Configuration ---
SCOPES = ['https://www.googleapis.com/auth/webmasters.readonly']
CLIENT_SECRET_FILE = 'client_secret.json'
TOKEN_FILE = 'token.json'
NUM_COLUMNS = 3

def get_gsc_service():
    """Authenticates and returns a Google Search Console service object."""
    creds = None
    # 1. Try to load existing credentials
    if os.path.exists(TOKEN_FILE):
        try:
            creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
        except Exception as e:
            print(f"Could not load credentials from {TOKEN_FILE}. Error: {e}")
            print("Will attempt to re-authenticate.")
            creds = None

    # 2. If there are no credentials or they are invalid, refresh or re-authenticate
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except exceptions.RefreshError as e:
                print(f"Error refreshing token: {e}")
                print("The refresh token is expired or revoked. Deleting it and re-authenticating.")
                if os.path.exists(TOKEN_FILE):
                    os.remove(TOKEN_FILE)
                creds = None  # Force re-authentication
        
        if not creds:
            if not os.path.exists(CLIENT_SECRET_FILE):
                print(f"Error: {CLIENT_SECRET_FILE} not found. Please follow setup instructions in README.md.")
                return None
            
            print("A browser window will open for you to authorize access.")
            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        
        # Save the new or refreshed credentials for the next run
        with open(TOKEN_FILE, 'w') as token:
            token.write(creds.to_json())
            print("Authentication successful. Credentials saved.")

    return build('webmasters', 'v3', credentials=creds)

def get_latest_available_gsc_date(service, site_url, max_retries=5):
    """
    Determines the latest date for which GSC data is available by querying
    backwards from today.
    """
    current_date = date.today()
    for i in range(max_retries):
        check_date = current_date - timedelta(days=i)
        check_date_str = check_date.strftime('%Y-%m-%d')
        
        print(f"Checking for GSC data availability on: {check_date_str}...")
        try:
            request = {
                'startDate': check_date_str,
                'endDate': check_date_str,
                'dimensions': ['date'], # Only need to check for any data
                'rowLimit': 1,
                'startRow': 0
            }
            response = service.searchanalytics().query(siteUrl=site_url, body=request).execute()
            
            if 'rows' in response and response['rows']:
                print(f"Latest available GSC data found for: {check_date_str}")
                return check_date
            else:
                print(f"No data for {check_date_str}, checking previous day.")
        except HttpError as e:
            # GSC returns 400 if date range is too recent (no data yet)
            if e.resp.status == 400:
                print(f"No data for {check_date_str}, checking previous day (HTTP 400).")
            else:
                print(f"An HTTP error occurred while checking date {check_date_str}: {e}")
                print("Continuing to check previous days.")
        except Exception as e:
            print(f"An unexpected error occurred while checking date {check_date_str}: {e}")
            print("Continuing to check previous days.")
            
    print(f"Could not determine latest available GSC date within {max_retries} days. Using today's date as a fallback.")
    return current_date # Fallback to today if no data found after retries


def get_all_pages(service, site_url, start_date, end_date):
    """Fetches all pages from Google Search Console for a given date range."""
    all_pages = []
    start_row = 0
    row_limit = 25000
    print(f"Fetching pages for {site_url} from {start_date} to {end_date}...")
    while True:
        try:
            request = {'startDate': start_date, 'endDate': end_date, 'dimensions': ['page'], 'rowLimit': row_limit, 'startRow': start_row}
            response = service.searchanalytics().query(siteUrl=site_url, body=request).execute()
            if 'rows' in response:
                pages = [row['keys'][0] for row in response['rows']]
                all_pages.extend(pages)
                print(f"Retrieved {len(pages)} pages... (Total: {len(all_pages)})")
                if len(response['rows']) < row_limit:
                    break
                start_row += row_limit
            else:
                break
        except HttpError as e:
            print(f"An HTTP error occurred: {e}")
            return None
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
            return None
    return all_pages

def create_html_page(urls, page_title, num_columns, start_date, end_date, num_links):
    """Generates an HTML page with links arranged in columns using a list-join pattern."""
    footer_style = 'footer{margin-top:2rem;padding-top:1rem;border-top:1px solid #dee2e6;text-align:center;font-size:0.9rem;color:#6c757d;}'
    html_parts = [
        f'<!DOCTYPE html>\n<html lang="en">\n<head>\n<meta charset="UTF-8">\n<meta name="viewport" content="width=device-width, initial-scale=1.0">\n<title>{page_title}</title>',
        '<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">',
        f'<style>body{{padding:20px;}}.list-group-item a{{text-decoration:none;word-break:break-all;}}.list-group-item:hover{{background-color:#f8f9fa;}}{footer_style}</style>',
        f'</head>\n<body>\n<div class="container-fluid">\n<h1 class="mb-4">{page_title}</h1>\n'
        f'<h2 class="mb-4">Date Range: {start_date} to {end_date}</h2>\n'
        f'<h3 class="mb-4">Total Links: {num_links}</h3>\n'
        f'<div class="row">\n'
    ]
    
    items_per_column = math.ceil(len(urls) / num_columns)
    url_chunks = [urls[i:i + items_per_column] for i in range(0, len(urls), items_per_column)]

    for chunk in url_chunks:
        html_parts.append(f'<div class="col-md-{12 // num_columns}">')
        html_parts.append('<ul class="list-group">\n')
        for url in chunk:
            url_str = str(url).strip()
            html_parts.append(f'<li class="list-group-item"><a href="{url_str}" target="_blank">{url_str}</a></li>\n')
        html_parts.append('</ul>\n')
        html_parts.append('</div>')

    html_parts.extend(['</div></div><footer><p><a href="https://github.com/liamdelahunty/gsc-exporter" target="_blank">gsc-exporter</a></p></footer></body></html>'])
    return "".join(html_parts)

def main():
    """Main function to run the page exporter and generate CSV and HTML."""
    parser = argparse.ArgumentParser(description='Export Google Search Console pages to CSV and HTML.')
    parser.add_argument('site_url', help='The URL of the site to export pages for.\nUse sc-domain: for the property.')
    parser.add_argument('--use-cache', action='store_true', help='Use a cached CSV file from a previous run if it exists.')
    
    # Create a mutually exclusive group for date range options
    date_group = parser.add_mutually_exclusive_group()
    date_group.add_argument('--start-date', help='Start date in YYYY-MM-DD format.')
    date_group.add_argument('--last-24-hours', action='store_true', help='Set date range to the last 24 hours.')
    date_group.add_argument('--last-7-days', action='store_true', help='Set date range to the last 7 days.')
    date_group.add_argument('--last-28-days', action='store_true', help='Set date range to the last 28 days.')
    date_group.add_argument('--last-month', action='store_true', help='Set date range to the last calendar month.')
    date_group.add_argument('--last-quarter', action='store_true', help='Set date range to the last quarter.')
    date_group.add_argument('--last-3-months', action='store_true', help='Set date range to the last 3 months.')
    date_group.add_argument('--last-6-months', action='store_true', help='Set date range to the last 6 months.')
    date_group.add_argument('--last-12-months', action='store_true', help='Set date range to the last 12 months.')
    date_group.add_argument('--last-16-months', action='store_true', help='Set date range to the last 16 months.')
    
    parser.add_argument('--end-date', help='End date in YYYY-MM-DD format. Used only with --start-date.')
    
    args = parser.parse_args()
    site_url = args.site_url
    
    # Authenticate GSC service once
    service = get_gsc_service()
    if not service:
        return

    latest_available_date = get_latest_available_gsc_date(service, site_url)

    # Set default date range if none is chosen
    if not any([
        args.start_date, args.last_24_hours, args.last_7_days, args.last_28_days,
        args.last_month, args.last_quarter, args.last_3_months,
        args.last_6_months, args.last_12_months, args.last_16_months
    ]):
        args.last_month = True

    # Determine the date range based on the provided flags
    if args.start_date and args.end_date:
        start_date = args.start_date
        end_date = args.end_date
    elif args.last_24_hours:
        start_date = (latest_available_date - timedelta(days=1)).strftime('%Y-%m-%d')
        end_date = (latest_available_date - timedelta(days=1)).strftime('%Y-%m-%d')
    elif args.last_7_days:
        start_date = (latest_available_date - timedelta(days=6)).strftime('%Y-%m-%d')
        end_date = latest_available_date.strftime('%Y-%m-%d')
    elif args.last_28_days:
        start_date = (latest_available_date - timedelta(days=27)).strftime('%Y-%m-%d')
        end_date = latest_available_date.strftime('%Y-%m-%d')
    elif args.last_month:
        first_day_of_current_month = latest_available_date.replace(day=1)
        last_day_of_previous_month = first_day_of_current_month - timedelta(days=1)
        start_date = last_day_of_previous_month.replace(day=1).strftime('%Y-%m-%d')
        end_date = last_day_of_previous_month.strftime('%Y-%m-%d')
    elif args.last_quarter:
        current_quarter = (latest_available_date.month - 1) // 3
        end_date_dt = datetime(latest_available_date.year, 3 * current_quarter + 1, 1).date() - timedelta(days=1)
        start_date_dt = end_date_dt.replace(day=1) - relativedelta(months=2)
        start_date = start_date_dt.strftime('%Y-%m-%d')
        end_date = end_date_dt.strftime('%Y-%m-%d')
    elif args.last_3_months:
        start_date = (latest_available_date - relativedelta(months=3) + timedelta(days=1)).strftime('%Y-%m-%d')
        end_date = latest_available_date.strftime('%Y-%m-%d')
    elif args.last_6_months:
        start_date = (latest_available_date - relativedelta(months=6) + timedelta(days=1)).strftime('%Y-%m-%d')
        end_date = latest_available_date.strftime('%Y-%m-%d')
    elif args.last_12_months:
        start_date = (latest_available_date - relativedelta(months=12) + timedelta(days=1)).strftime('%Y-%m-%d')
        end_date = latest_available_date.strftime('%Y-%m-%d')
    elif args.last_16_months:
        start_date = (latest_available_date - relativedelta(months=16) + timedelta(days=1)).strftime('%Y-%m-%d')
        end_date = latest_available_date.strftime('%Y-%m-%d')
    
    # Define output paths
    if site_url.startswith('sc-domain:'):
        host_plain = site_url.replace('sc-domain:', '')
    else:
        host_plain = urlparse(site_url).netloc
    
    host_dir = host_plain.replace('www.', '')
    output_dir = os.path.join('output', host_dir)
    os.makedirs(output_dir, exist_ok=True)
    host_for_filename = host_dir.replace('.', '-')
    
    csv_file_name = f"gsc-pages-{host_for_filename}-{start_date}-to-{end_date}.csv"
    csv_output_path = os.path.join(output_dir, csv_file_name)
    
    html_file_name = f"{host_for_filename}-links-{start_date}-to-{end_date}.html"
    html_output_path = os.path.join(output_dir, html_file_name)

    pages = []
    if args.use_cache and os.path.exists(csv_output_path):
        print(f"Found cached data at {csv_output_path}. Using it to generate report.")
        try:
            df = pd.read_csv(csv_output_path)
            if 'Page' in df.columns:
                pages = df['Page'].tolist()
            else:
                print(f"Warning: Cached CSV at {csv_output_path} does not contain 'Page' column. Re-fetching data.")
        except Exception as e:
            print(f"Error reading cached CSV: {e}. Re-fetching data.")
        
    if not pages: # If cache not used, or cache read failed, fetch fresh data
        # service is already authenticated above
        # if not service:
        #     return

        pages = get_all_pages(service, site_url, start_date, end_date)
        
        if pages:
            try:
                df = pd.DataFrame(pages, columns=['Page'])
                df.to_csv(csv_output_path, index=False)
                print(f"Successfully exported CSV to {csv_output_path}")
                print(f"Hint: To recreate this report from the saved data, use the --use-cache flag.")
            except PermissionError:
                print(f"\nError: Permission denied when trying to write to the output directory.")
                print(f"Please make sure you have write permissions for the directory: {output_dir}")
                print(f"Also, check if the file is already open in another program: {csv_file_name}")
                return
        else:
            print("No pages found for the given site and date range.")
            return

    if pages:
        sorted_pages = sorted(pages)
        num_links = len(sorted_pages)
        print(f"\nTotal unique pages found: {num_links}")

        try:
            html_output = create_html_page(sorted_pages, f"Google Organic Pages for {host_dir}", NUM_COLUMNS, start_date, end_date, num_links)
            with open(html_output_path, 'w', encoding='utf-8') as f:
                f.write(html_output)
            print(f"Successfully created HTML page at {html_output_path}")
        except PermissionError:
            print(f"\nError: Permission denied when trying to write to the output directory.")
            print(f"Please make sure you have write permissions for the directory: {output_dir}")
            print(f"Also, check if the file is already open in another program: {html_file_name}")
    else:
        print("No pages found for the given site and date range.")

if __name__ == '__main__':
    main()
