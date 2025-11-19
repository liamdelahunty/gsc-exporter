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
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(CLIENT_SECRET_FILE):
                print(f"Error: {CLIENT_SECRET_FILE} not found.")
                return None
            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_FILE, 'w') as token:
            token.write(creds.to_json())
    return build('webmasters', 'v3', credentials=creds)

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
    html_parts = [
        f'<!DOCTYPE html>\n<html lang="en">\n<head>\n<meta charset="UTF-8">\n<meta name="viewport" content="width=device-width, initial-scale=1.0">\n<title>{page_title}</title>',
        '<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">',
        '<style>body{padding:20px;}.list-group-item a{text-decoration:none;word-break:break-all;}.list-group-item:hover{background-color:#f8f9fa;}</style>',
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

    html_parts.extend(['</div></div></body></html>'])
    return "".join(html_parts)

def main():
    """Main function to run the page exporter and generate CSV and HTML."""
    parser = argparse.ArgumentParser(description='Export Google Search Console pages to CSV and HTML.')
    parser.add_argument('site_url', help='The URL of the site to export pages for.\nUse sc-domain: for the property.')
    
    # Create a mutually exclusive group for date range options
    date_group = parser.add_mutually_exclusive_group()
    date_group.add_argument('--start-date', help='Start date in YYYY-MM-DD format.')
    date_group.add_argument('--last-quarter', action='store_true', help='Set date range to the last quarter.')
    date_group.add_argument('--last-6-months', action='store_true', help='Set date range to the last 6 months.')
    date_group.add_argument('--last-12-months', action='store_true', help='Set date range to the last 12 months.')
    date_group.add_argument('--last-16-months', action='store_true', help='Set date range to the last 16 months.')
    
    parser.add_argument('--end-date', help='End date in YYYY-MM-DD format. Used only with --start-date.')
    
    args = parser.parse_args()
    site_url = args.site_url
    start_date = args.start_date
    end_date = args.end_date
    
    today = date.today()

    # Determine the date range based on the provided flags
    if args.start_date and args.end_date:
        start_date = args.start_date
        end_date = args.end_date
    elif args.last_quarter:
        start_date = (today - relativedelta(months=3)).strftime('%Y-%m-%d')
        end_date = today.strftime('%Y-%m-%d')
    elif args.last_6_months:
        start_date = (today - relativedelta(months=6)).strftime('%Y-%m-%d')
        end_date = today.strftime('%Y-%m-%d')
    elif args.last_12_months:
        start_date = (today - relativedelta(months=12)).strftime('%Y-%m-%d')
        end_date = today.strftime('%Y-%m-%d')
    elif args.last_16_months:
        start_date = (today - relativedelta(months=16)).strftime('%Y-%m-%d')
        end_date = today.strftime('%Y-%m-%d')
    else:
        # Default to the previous calendar month if no date range is specified
        first_day_of_current_month = today.replace(day=1)
        last_day_of_previous_month = first_day_of_current_month - timedelta(days=1)
        start_date = last_day_of_previous_month.replace(day=1).strftime('%Y-%m-%d')
        end_date = last_day_of_previous_month.strftime('%Y-%m-%d')

    service = get_gsc_service()
    if not service:
        return

    pages = get_all_pages(service, site_url, start_date, end_date)
    
    if pages:
        sorted_pages = sorted(pages)
        num_links = len(sorted_pages)
        print(f"\nTotal unique pages found: {num_links}")

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
        
        df = pd.DataFrame(sorted_pages, columns=['Page'])
        df.to_csv(csv_output_path, index=False)
        print(f"Successfully exported CSV to {csv_output_path}")

        html_file_name = f"{host_for_filename}-links-{start_date}-to-{end_date}.html"
        html_output_path = os.path.join(output_dir, html_file_name)
        
        html_output = create_html_page(sorted_pages, f"Links for {host_dir}", NUM_COLUMNS, start_date, end_date, num_links)
        with open(html_output_path, 'w', encoding='utf-8') as f:
            f.write(html_output)
        print(f"Successfully created HTML page at {html_output_path}")
    else:
        print("No pages found for the given site and date range.")

if __name__ == '__main__':
    main()
