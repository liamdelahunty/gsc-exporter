"""
Generates a report showing the performance of top pages over the last 16 months.

This script identifies the top 250 pages from the last complete calendar month
and then fetches their performance data for each of the last 16 complete months
to show trends over time.

Usage:
    python page-performance-over-time.py <site_url>
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
            
            print("A browser window will open for you to authorize access.")
            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        
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
            if e.resp.status == 400:
                print(f"No data for {check_date_str}, checking previous day (HTTP 400).")
            else:
                print(f"An HTTP error occurred while checking date {check_date_str}: {e}")
        except Exception as e:
            print(f"An unexpected error occurred while checking date {check_date_str}: {e}")
            
    print(f"Could not determine latest available GSC date within {max_retries} days. Using today's date as a fallback.")
    return current_date

def get_gsc_data(service, site_url, start_date, end_date, dimensions, filters=None):
    """Fetches performance data from GSC for a given date range and dimensions."""
    all_data = []
    start_row = 0
    row_limit = 25000 
    
    print(f"Fetching data for dimensions: {', '.join(dimensions)} from {start_date} to {end_date}...")

    request_body = {
        'startDate': start_date,
        'endDate': end_date,
        'dimensions': dimensions,
        'rowLimit': row_limit,
        'startRow': start_row
    }

    if filters:
        request_body['dimensionFilterGroups'] = [{'filters': filters}]

    while True:
        try:
            request_body['startRow'] = start_row
            response = service.searchanalytics().query(siteUrl=site_url, body=request_body).execute()

            if 'rows' in response:
                rows = response['rows']
                all_data.extend(rows)
                print(f"Retrieved {len(rows)} rows... (Total: {len(all_data)})")
                if len(rows) < row_limit:
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
            
    if not all_data:
        return pd.DataFrame()

    df = pd.DataFrame(all_data)
    # Ensure keys are always returned as a list, even for a single dimension
    if isinstance(df['keys'].iloc[0], list):
        df[dimensions] = pd.DataFrame(df['keys'].tolist(), index=df.index)
    else:
        df[dimensions[0]] = df['keys']
        
    df = df.drop(columns=['keys'])
    
    for col in ['clicks', 'impressions', 'ctr', 'position']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        
    return df

def create_html_report(report_title, df_clicks, df_impressions):
    """Generates an HTML report from the pivoted dataframes."""

    def format_df(df):
        """Formats a dataframe for HTML output."""
        df_html = df.copy()
        for col in df_html.columns:
            df_html[col] = df_html[col].apply(lambda x: f"{int(x):,}" if pd.notna(x) else "0")
        return df_html

    df_clicks_html = format_df(df_clicks)
    df_impressions_html = format_df(df_impressions)
    
    clicks_table = df_clicks_html.to_html(classes="table table-striped table-hover", border=0)
    impressions_table = df_impressions_html.to_html(classes="table table-striped table-hover", border=0)

    return f"""
<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{report_title}</title><link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
<style>
body {{ padding: 2rem; }}
h1, h2 {{ border-bottom: 2px solid #dee2e6; padding-bottom: .5rem; margin-top: 2rem; }}
footer {{ margin-top: 3rem; text-align: center; color: #6c757d; }}
.table-responsive {{ max-height: 600px; }}
</style></head>
<body><div class="container-fluid"><h1>{report_title}</h1>
<h2>Clicks Over Time</h2>
<div class="table-responsive">{clicks_table}</div>
<h2>Impressions Over Time</h2>
<div class="table-responsive">{impressions_table}</div>
</div>
<footer><p><a href="https://github.com/liamdelahunty/gsc-exporter" target="_blank">gsc-exporter</a></p></footer></body></html>
"""

def main():
    """Main function to run the page performance over time report."""
    parser = argparse.ArgumentParser(
        description='Generate a report on page performance over time.',
        epilog='Example usage:\n'
               '  python page-performance-over-time.py https://www.example.com\n'
    )
    parser.add_argument('site_url', help='The URL of the site to analyse. Use sc-domain: for a domain property.')
    
    args = parser.parse_args()
    site_url = args.site_url

    service = get_gsc_service()
    if not service:
        return

    latest_available_date = get_latest_available_gsc_date(service, site_url)
    
    # 1. Determine the date range for the last full calendar month
    end_of_last_month = latest_available_date.replace(day=1) - timedelta(days=1)
    start_of_last_month = end_of_last_month.replace(day=1)
    
    last_month_start_str = start_of_last_month.strftime('%Y-%m-%d')
    last_month_end_str = end_of_last_month.strftime('%Y-%m-%d')
    
    print(f"Identifying top pages from {last_month_start_str} to {last_month_end_str}...")

    # 2. Fetch data for the last full month to identify top 250 pages
    df_last_month = get_gsc_data(service, site_url, last_month_start_str, last_month_end_str, ['page'])
    
    if df_last_month.empty:
        print("No data found for the last full month. Cannot proceed.")
        return

    top_250_pages = df_last_month.sort_values(by='clicks', ascending=False).head(250)['page'].tolist()
    print(f"Identified {len(top_250_pages)} top pages.")

    # 3. Fetch data for the last 16 full months for these top pages
    all_monthly_data = []
    
    for i in range(16):
        # Calculate start and end of each of the past 16 full months
        month_to_fetch_end = (latest_available_date.replace(day=1) - relativedelta(months=i)) - timedelta(days=1)
        month_to_fetch_start = month_to_fetch_end.replace(day=1)

        month_start_str = month_to_fetch_start.strftime('%Y-%m-%d')
        month_end_str = month_to_fetch_end.strftime('%Y-%m-%d')
        
        page_filter = {
            'dimension': 'page',
            'operator': 'in',
            'expression': top_250_pages
        }
        
        df_month = get_gsc_data(service, site_url, month_start_str, month_end_str, ['page'], filters=[page_filter])
        
        if not df_month.empty:
            df_month['month'] = month_to_fetch_start.strftime('%Y-%m')
            all_monthly_data.append(df_month)

    if not all_monthly_data:
        print("No historical data found for the top pages.")
        return

    df_historical = pd.concat(all_monthly_data, ignore_index=True)

    # 4. Pivot the data to have pages as rows and monthly metrics as columns
    df_pivot_clicks = df_historical.pivot_table(index='page', columns='month', values='clicks', aggfunc='sum').fillna(0)
    df_pivot_impressions = df_historical.pivot_table(index='page', columns='month', values='impressions', aggfunc='sum').fillna(0)

    # Sort columns by month
    df_pivot_clicks = df_pivot_clicks.reindex(sorted(df_pivot_clicks.columns, reverse=True), axis=1)
    df_pivot_impressions = df_pivot_impressions.reindex(sorted(df_pivot_impressions.columns, reverse=True), axis=1)

    # Combine into a single dataframe for export
    df_combined = pd.concat([df_pivot_clicks, df_pivot_impressions], keys=['clicks', 'impressions'], axis=1)

    # 5. Save the data to CSV
    if site_url.startswith('sc-domain:'):
        host_plain = site_url.replace('sc-domain:', '')
    else:
        host_plain = urlparse(site_url).netloc
    
    host_dir = host_plain.replace('www.', '')
    output_dir = os.path.join('output', host_dir)
    os.makedirs(output_dir, exist_ok=True)
    host_for_filename = host_dir.replace('.', '-')

    file_prefix = f"page-performance-over-time-{host_for_filename}"
    csv_output_path = os.path.join(output_dir, f"{file_prefix}.csv")
    html_output_path = os.path.join(output_dir, f"{file_prefix}.html")
    
    df_combined.to_csv(csv_output_path)
    print(f"Successfully saved data to {csv_output_path}")

    # 6. Generate and save HTML report
    html_output = create_html_report(
        report_title=f"Page Performance Over Time for {host_dir}",
        df_clicks=df_pivot_clicks,
        df_impressions=df_pivot_impressions
    )
    with open(html_output_path, 'w', encoding='utf-8') as f:
        f.write(html_output)
    print(f"Successfully created HTML report at {html_output_path}")

if __name__ == '__main__':
    main()