"""
Performs an account-wide analysis of Google Search Console data, gathering key
performance metrics for each complete calendar month for every property in the account.

This script authenticates with the Google Search Console API, fetches a list of all
sites associated with the account, and then, for each site, retrieves the clicks,
impressions, CTR, and average position for each full calendar month over the last
16 months.

The aggregated data is then compiled into a single CSV file and a single HTML report,
providing a comprehensive overview of the account's performance over time.
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
import argparse

# --- Configuration ---
SCOPES = ['https://www.googleapis.com/auth/webmasters.readonly']
CLIENT_SECRET_FILE = 'client_secret.json'
TOKEN_FILE = 'token.json'

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
                print("Please download your client secret from the Google API Console and place it in the root directory.")
                return None
            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_FILE, 'w') as token:
            token.write(creds.to_json())
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
    except Exception as e:
        print(f"An unexpected error occurred while fetching sites: {e}")
    return sites

def get_monthly_performance_data(service, site_url, start_date, end_date):
    """Fetches performance data from GSC for a given date range."""
    try:
        request = {
            'startDate': start_date,
            'endDate': end_date
        }
        response = service.searchanalytics().query(siteUrl=site_url, body=request).execute()
        if 'rows' in response:
            return response['rows'][0]
    except HttpError as e:
        print(f"An HTTP error occurred for site {site_url} from {start_date} to {end_date}: {e}")
    except Exception as e:
        print(f"An unexpected error occurred for site {site_url} from {start_date} to {end_date}: {e}")
    return None

def create_html_report(df):
    """Generates an HTML report from the analysis dataframe."""
    html_template = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Account-Wide GSC Performance Report</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body {{ padding: 2rem; }}
        .table-responsive {{ max-height: 800px; overflow-y: auto; }}
        h1 {{ border-bottom: 2px solid #dee2e6; padding-bottom: 0.5rem; margin-top: 2rem; }}
        footer {{ margin-top: 3rem; text-align: center; color: #6c757d; }}
        .table thead th {{ text-align: center; }}
    </style>
</head>
<body>
    <div class="container-fluid">
        <h1 class="mb-3">Account-Wide GSC Performance Report</h1>
        <div class="table-responsive">
            {df.to_html(classes="table table-striped table-hover", index=False, border=0)}
        </div>
    </div>
    <footer>
        <p><a href="https://github.com/liamdelahunty/gsc-exporter" target="_blank">gsc-exporter</a></p>
    </footer>
</body>
</html>
"""
    return html_template

def main():
    """Main function to run the account-wide analysis."""
    service = get_gsc_service()
    if not service:
        return

    sites = get_all_sites(service)
    if not sites:
        print("No sites found in your account.")
        return

    all_data = []
    today = date.today()
    
    for site_url in sites:
        print(f"\nFetching data for site: {site_url}")
        for i in range(1, 17):
            end_of_month = today.replace(day=1) - relativedelta(months=i-1) - timedelta(days=1)
            start_of_month = end_of_month.replace(day=1)
            
            start_date = start_of_month.strftime('%Y-%m-%d')
            end_date = end_of_month.strftime('%Y-%m-%d')

            data = get_monthly_performance_data(service, site_url, start_date, end_date)
            
            if data:
                all_data.append({
                    'site_url': site_url,
                    'month': start_of_month.strftime('%Y-%m'),
                    'clicks': data['clicks'],
                    'impressions': data['impressions'],
                    'ctr': data['ctr'],
                    'position': data['position']
                })
    
    if not all_data:
        print("No performance data found for any site.")
        return
        
    df = pd.DataFrame(all_data)
    
    # Format the dataframe for better readability
    df['ctr'] = df['ctr'].apply(lambda x: f"{x:.2%}")
    df['position'] = df['position'].apply(lambda x: f"{x:.2f}")

    output_dir = 'output'
    os.makedirs(output_dir, exist_ok=True)
    
    # Get the most recent month for the filename
    most_recent_month = (today.replace(day=1) - timedelta(days=1)).strftime('%Y-%m')

    # Save to CSV
    csv_file_name = f'account-wide-performance-{most_recent_month}.csv'
    csv_output_path = os.path.join(output_dir, csv_file_name)
    df.to_csv(csv_output_path, index=False)
    print(f"\nSuccessfully exported CSV to {csv_output_path}")

    # Generate and save HTML report
    html_file_name = f'account-wide-performance-{most_recent_month}.html'
    html_output_path = os.path.join(output_dir, html_file_name)
    html_output = create_html_report(df)
    with open(html_output_path, 'w', encoding='utf-8') as f:
        f.write(html_output)
    print(f"Successfully created HTML report at {html_output_path}")

if __name__ == '__main__':
    main()
