"""
Generates a seasonal performance report by comparing page-level data for the same month across multiple years.

This script fetches performance data for a specific month (e.g., April) and compares it with
the same month from previous years. It helps identify content that performs well seasonally.

Usage:
    python seasonal-performance-report.py <site_url> [--month <YYYY-MM>] [--years <number_of_years>]

Example:
    python seasonal-performance-report.py https://www.example.com --month 2026-04 --years 3
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
import argparse
import json
import glob

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
            creds = None

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except exceptions.RefreshError as e:
                print(f"Error refreshing token: {e}")
                if os.path.exists(TOKEN_FILE):
                    os.remove(TOKEN_FILE)
                creds = None
        
        if not creds:
            if not os.path.exists(CLIENT_SECRET_FILE):
                print(f"Error: {CLIENT_SECRET_FILE} not found.")
                return None
            
            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        
        with open(TOKEN_FILE, 'w') as token:
            token.write(creds.to_json())

    return build('webmasters', 'v3', credentials=creds)

def get_latest_available_gsc_date(service, site_url):
    """Determines the latest date for which GSC data is available."""
    current_date = date.today()
    for i in range(5):
        check_date = current_date - timedelta(days=i)
        check_date_str = check_date.strftime('%Y-%m-%d')
        try:
            request = {'startDate': check_date_str, 'endDate': check_date_str, 'dimensions': ['date'], 'rowLimit': 1}
            response = service.searchanalytics().query(siteUrl=site_url, body=request).execute()
            if 'rows' in response and response['rows']:
                return check_date
        except HttpError:
            pass
    return current_date

def fetch_page_data(service, site_url, start_date, end_date):
    """Fetches page-level performance data from GSC."""
    all_pages = []
    start_row = 0
    row_limit = 25000
    
    print(f"  - Fetching page data from {start_date} to {end_date}...")
    
    while True:
        try:
            request = {
                'startDate': start_date,
                'endDate': end_date,
                'dimensions': ['page'],
                'rowLimit': row_limit,
                'startRow': start_row
            }
            response = service.searchanalytics().query(siteUrl=site_url, body=request).execute()
            
            if 'rows' in response:
                all_pages.extend(response['rows'])
                if len(response['rows']) < row_limit:
                    break
                start_row += row_limit
            else:
                break
        except HttpError as e:
            print(f"    - Error fetching data: {e}")
            break
            
    if not all_pages:
        return None
        
    df = pd.DataFrame([
        {
            'page': row['keys'][0],
            'clicks': row['clicks'],
            'impressions': row['impressions'],
            'ctr': row['ctr'],
            'position': row['position']
        } for row in all_pages
    ])
    return df

def get_month_range(month_str):
    """Returns the start and end date for a given YYYY-MM string."""
    dt = datetime.strptime(month_str, '%Y-%m')
    start_date = dt.strftime('%Y-%m-01')
    last_day = (dt + relativedelta(months=1) - timedelta(days=1)).strftime('%Y-%m-%d')
    return start_date, last_day

def create_seasonal_report_html(df, report_title, years_list):
    """Generates the HTML report for seasonal comparison."""
    table_html = df.to_html(classes="table table-striped table-hover", index=False, border=0)
    
    return f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{report_title}</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body {{ padding: 2rem; }}
        h1 {{ border-bottom: 2px solid #dee2e6; padding-bottom: .5rem; margin-top: 2rem; }}
        .table thead th {{ background-color: #434343; color: #ffffff; text-align: left; }}
        footer {{ margin-top: 3rem; text-align: center; color: #6c757d; }}
    </style>
</head>
<body>
    <div class="container-fluid">
        <h1>{report_title}</h1>
        <p>Comparing performance for the same month across years: {', '.join(map(str, years_list))}</p>
        <div class="table-responsive">
            {table_html}
        </div>
    </div>
    <footer><p><a href="https://github.com/liamdelahunty/gsc-exporter" target="_blank">gsc-exporter</a></p></footer>
</body>
</html>
"""

def main():
    parser = argparse.ArgumentParser(description='Generate a seasonal performance report.')
    parser.add_argument('site_url', help='The GSC site URL (e.g., https://www.example.com or sc-domain:example.com)')
    parser.add_argument('--month', help='The month to analyze in YYYY-MM format (defaults to last complete month).')
    parser.add_argument('--years', type=int, default=3, help='Number of years to look back (default 3).')
    parser.add_argument('--use-cache', action='store_true', help='Use cached data if available.')
    
    args = parser.parse_args()
    service = get_gsc_service()
    if not service: return

    # Determine target month
    if not args.month:
        latest_date = get_latest_available_gsc_date(service, args.site_url)
        target_month_date = latest_date.replace(day=1) - timedelta(days=1)
        args.month = target_month_date.strftime('%Y-%m')

    target_dt = datetime.strptime(args.month, '%Y-%m')
    
    # Prepare output directory
    site_output_name = args.site_url
    if site_output_name.startswith('sc-domain:'):
        host_plain = site_output_name.replace('sc-domain:', '')
    else:
        host_plain = urlparse(site_output_name).netloc
    host_dir = host_plain.replace('www.', '').replace('.', '-')
    output_dir = os.path.join('output', host_dir, 'seasonal')
    os.makedirs(output_dir, exist_ok=True)

    all_years_data = []
    years_list = []

    for i in range(args.years):
        year_dt = target_dt - relativedelta(years=i)
        year_str = year_dt.strftime('%Y-%m')
        start_date, end_date = get_month_range(year_str)
        
        # 1. Check for seasonal-specific cache
        csv_cache_path = os.path.join(output_dir, f'page-data-{year_str}.csv')
        df_year = None
        
        if os.path.exists(csv_cache_path):
            print(f"Using seasonal cache for {year_str}")
            df_year = pd.read_csv(csv_cache_path)
        else:
            # 2. Check for general monthly report cache in the host directory
            # We look for files matching the pattern monthly-summary-report-*-{start_date}-to-{end_date}.csv
            host_root_dir = os.path.join('output', host_dir)
            search_pattern = os.path.join(host_root_dir, f"*-{start_date}-to-{end_date}.csv")
            potential_caches = glob.glob(search_pattern)
            
            if potential_caches:
                print(f"Found existing monthly report for {year_str}: {potential_caches[0]}")
                # Note: Monthly summary reports are at site-level, not page-level.
                # If we need page-level data, we specifically need page-level caches.
                # Let's check for page-level reports instead.
                page_report_pattern = os.path.join(host_root_dir, f"page-level-report-*-{start_date}-to-{end_date}.csv")
                potential_page_caches = glob.glob(page_report_pattern)
                if potential_page_caches:
                    print(f"Found existing page-level report for {year_str}: {potential_page_caches[0]}")
                    df_year = pd.read_csv(potential_page_caches[0])
            
            # 3. Fetch from GSC if within 16 months and not found in cache
            if df_year is None:
                sixteen_months_ago = date.today() - relativedelta(months=16)
                if year_dt.date() >= sixteen_months_ago:
                    df_year = fetch_page_data(service, args.site_url, start_date, end_date)
                    if df_year is not None:
                        df_year.to_csv(csv_cache_path, index=False)
                else:
                    print(f"Data for {year_str} is older than 16 months and no cache was found. Skipping.")
        
        if df_year is not None:
            years_list.append(year_dt.year)
            # Ensure we only have relevant columns and they are named correctly
            if 'page' not in df_year.columns and 'Page' in df_year.columns:
                df_year = df_year.rename(columns={'Page': 'page'})
            
            # Keep only the columns we need for the merge
            cols_to_keep = ['page', 'clicks', 'impressions', 'ctr', 'position']
            df_year = df_year[[c for c in cols_to_keep if c in df_year.columns]]
            
            df_year = df_year.rename(columns={
                'clicks': f'clicks_{year_dt.year}',
                'impressions': f'impressions_{year_dt.year}',
                'ctr': f'ctr_{year_dt.year}',
                'position': f'position_{year_dt.year}'
            })
            all_years_data.append(df_year)

    if not all_years_data:
        print("No data found for any of the years.")
        return

    # Merge all years
    merged_df = all_years_data[0]
    for df_next in all_years_data[1:]:
        merged_df = pd.merge(merged_df, df_next, on='page', how='outer')

    # Fill NaNs with 0 for clicks/impressions
    for year in years_list:
        merged_df[f'clicks_{year}'] = merged_df[f'clicks_{year}'].fillna(0).astype(int)
        merged_df[f'impressions_{year}'] = merged_df[f'impressions_{year}'].fillna(0).astype(int)

    # Calculate growth (current vs last year)
    if len(years_list) >= 2:
        curr_year = years_list[0]
        prev_year = years_list[1]
        merged_df['clicks_diff'] = merged_df[f'clicks_{curr_year}'] - merged_df[f'clicks_{prev_year}']
        merged_df = merged_df.sort_values(by='clicks_diff', ascending=False)

    # Format for report
    report_title = f"Seasonal Performance Report: {target_dt.strftime('%B')} ({args.site_url})"
    csv_report_path = os.path.join(output_dir, f'seasonal-report-{args.month}.csv')
    html_report_path = os.path.join(output_dir, f'seasonal-report-{args.month}.html')
    
    merged_df.to_csv(csv_report_path, index=False)
    print(f"Exported CSV to {csv_report_path}")
    
    html_content = create_seasonal_report_html(merged_df, report_title, years_list)
    with open(html_report_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    print(f"Exported HTML to {html_report_path}")

if __name__ == '__main__':
    main()
