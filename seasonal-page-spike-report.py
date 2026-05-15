"""
Generates a report identifying pages with "out of the ordinary" traffic spikes.

This script fetches monthly performance data for pages, caches it locally, 
and identifies pages where clicks or impressions in a given month are 
significantly higher than their historical average (using Z-scores).

Usage:
    python seasonal-page-spike-report.py <site_url> [--months <number_of_months>] [--threshold <z_score_threshold>]

Example:
    python seasonal-page-spike-report.py https://www.example.com --months 24 --threshold 2.0
"""
import os
import pandas as pd
import numpy as np
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
    
    print(f"    - Fetching data for {start_date} to {end_date}...")
    
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
            print(f"      - Error: {e}")
            break
            
    if not all_pages:
        return None
        
    df = pd.DataFrame([
        {
            'page': row['keys'][0],
            'clicks': row['clicks'],
            'impressions': row['impressions']
        } for row in all_pages
    ])
    return df

def get_month_range(month_str):
    """Returns the start and end date for a given YYYY-MM string."""
    dt = datetime.strptime(month_str, '%Y-%m')
    start_date = dt.strftime('%Y-%m-01')
    last_day = (dt + relativedelta(months=1) - timedelta(days=1)).strftime('%Y-%m-%d')
    return start_date, last_day

def create_report_html(spikes_df, report_title, site_url, months_count):
    """Generates the HTML report for spikes."""
    if spikes_df.empty:
        return f"<html><head><title>{report_title}</title></head><body><h1>{report_title}</h1><p>No spikes detected.</p></body></html>"

    # Format numbers
    display_df = spikes_df.copy()
    display_df['clicks'] = display_df['clicks'].apply(lambda x: f"{x:,}")
    display_df['impressions'] = display_df['impressions'].apply(lambda x: f"{x:,}")
    display_df['avg_clicks'] = display_df['avg_clicks'].apply(lambda x: f"{x:,.2f}")
    display_df['avg_impressions'] = display_df['avg_impressions'].apply(lambda x: f"{x:,.2f}")
    display_df['clicks_z_score'] = display_df['clicks_z_score'].apply(lambda x: f"{x:.2f}" if not pd.isna(x) else "N/A")
    display_df['impressions_z_score'] = display_df['impressions_z_score'].apply(lambda x: f"{x:.2f}" if not pd.isna(x) else "N/A")

    table_html = display_df.to_html(classes="table table-striped table-hover", index=False, border=0)
    
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
        h1 {{ border-bottom: 2px solid #dee2e6; padding-bottom: .5rem; margin-bottom: 1rem; }}
        .table thead th {{ background-color: #434343; color: #ffffff; text-align: left; }}
        footer {{ margin-top: 3rem; text-align: center; color: #6c757d; }}
        .z-score {{ font-weight: bold; color: #d63384; }}
    </style>
</head>
<body>
    <div class="container-fluid">
        <h1>{report_title}</h1>
        <p class="lead">Seasonal analysis identifying pages with traffic significantly higher than their historical average (analyzing last {months_count} months).</p>
        <p class="text-muted">Domain: {site_url}</p>
        <div class="table-responsive">
            {table_html}
        </div>
    </div>
    <footer><p><a href="https://github.com/liamdelahunty/gsc-exporter" target="_blank">gsc-exporter</a></p></footer>
</body>
</html>
"""

def main():
    parser = argparse.ArgumentParser(description='Identify seasonal pages with traffic spikes.')
    parser.add_argument('site_url', help='The GSC site URL')
    parser.add_argument('--months', type=int, default=16, help='Number of months to analyze (default 16).')
    parser.add_argument('--threshold', type=float, default=2.0, help='Z-score threshold for spike detection (default 2.0).')
    parser.add_argument('--min-clicks', type=int, default=10, help='Minimum clicks in a month to consider as a spike.')
    
    args = parser.parse_args()
    service = get_gsc_service()
    if not service: return

    latest_date = get_latest_available_gsc_date(service, args.site_url)
    target_month_date = latest_date.replace(day=1) - timedelta(days=1)
    
    # Prepare output directory
    if args.site_url.startswith('sc-domain:'):
        host_plain = args.site_url.replace('sc-domain:', '')
    else:
        host_plain = urlparse(args.site_url).netloc
    host_dir = host_plain.replace('www.', '').replace('.', '-')
    
    # Use a common cache directory for page-level data
    cache_dir = os.path.join('cache', 'page-data', host_dir)
    os.makedirs(cache_dir, exist_ok=True)
    
    output_dir = os.path.join('output', host_dir, 'seasonal')
    os.makedirs(output_dir, exist_ok=True)

    all_data_frames = []
    
    sixteen_months_ago = date.today() - relativedelta(months=16)

    for i in range(args.months):
        month_dt = target_month_date - relativedelta(months=i)
        month_str = month_dt.strftime('%Y-%m')
        cache_file = os.path.join(cache_dir, f'{month_str}.csv')
        
        df_month = None
        if os.path.exists(cache_file):
            df_month = pd.read_csv(cache_file)
        elif month_dt.date() >= sixteen_months_ago:
            print(f"Fetching data for {month_str}...")
            start_date, end_date = get_month_range(month_str)
            df_month = fetch_page_data(service, args.site_url, start_date, end_date)
            if df_month is not None:
                df_month.to_csv(cache_file, index=False)
        else:
            print(f"Skipping {month_str} (no cache and > 16 months ago).")
            
        if df_month is not None:
            df_month['month'] = month_str
            all_data_frames.append(df_month)

    if not all_data_frames:
        print("No data found.")
        return

    df = pd.concat(all_data_frames, ignore_index=True)
    
    # Calculate stats per page
    stats = df.groupby('page').agg({
        'clicks': ['mean', 'std', 'count'],
        'impressions': ['mean', 'std']
    })
    stats.columns = ['_'.join(col).strip() for col in stats.columns.values]
    stats = stats.reset_index()

    # Join stats back to main df
    df = df.merge(stats, on='page')

    # Calculate Z-scores
    df['clicks_z_score'] = (df['clicks'] - df['clicks_mean']) / df['clicks_std'].replace(0, np.nan)
    df['impressions_z_score'] = (df['impressions'] - df['impressions_mean']) / df['impressions_std'].replace(0, np.nan)

    is_spike = (
        ((df['clicks_z_score'] > args.threshold) | (df['impressions_z_score'] > args.threshold)) &
        (df['clicks'] >= args.min_clicks)
    )
    
    spikes = df[is_spike].copy()
    
    # Sort by Z-score descending
    spikes['max_z'] = spikes[['clicks_z_score', 'impressions_z_score']].max(axis=1)
    spikes = spikes.sort_values(by=['month', 'max_z'], ascending=[False, False])

    # Select columns for report
    report_df = spikes[[
        'month', 'page', 'clicks', 'clicks_mean', 'clicks_z_score', 
        'impressions', 'impressions_mean', 'impressions_z_score'
    ]]
    report_df = report_df.rename(columns={
        'clicks_mean': 'avg_clicks',
        'impressions_mean': 'avg_impressions'
    })

    # Save results
    report_title = f"Seasonal Page Spikes Report: {args.site_url}"
    date_suffix = datetime.now().strftime("%Y-%m-%d")
    csv_path = os.path.join(output_dir, f'seasonal-page-spikes-{date_suffix}.csv')
    html_path = os.path.join(output_dir, f'seasonal-page-spikes-{date_suffix}.html')
    
    report_df.to_csv(csv_path, index=False)
    print(f"Exported CSV to {csv_path}")
    
    html_content = create_report_html(report_df, report_title, args.site_url, args.months)
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    print(f"Exported HTML to {html_path}")

if __name__ == '__main__':
    main()
