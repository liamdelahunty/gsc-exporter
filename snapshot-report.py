"""
Generates a single-period performance snapshot for a Google Search Console property.

This script fetches performance data for a specified date range and creates a CSV 
export of all pages as well as an HTML report with observations on top-performing 
content, low CTR opportunities, and breakdowns by device and country.

Usage:
    python snapshot-report.py <site_url> [date_range_flag]

Example:
    python snapshot-report.py https://www.example.com --last-7-days
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
                print("Credentials have expired. Attempting to refresh...")
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


def get_gsc_data(service, site_url, start_date, end_date, dimensions):
    """
    Fetches performance data from GSC for a given date range and dimensions.
    Returns a pandas DataFrame.
    """
    all_data = []
    start_row = 0
    row_limit = 25000 
    
    dim_str = ', '.join(dimensions)
    print(f"Fetching data for dimensions: {dim_str} from {start_date} to {end_date}...")

    while True:
        try:
            request = {
                'startDate': start_date,
                'endDate': end_date,
                'dimensions': dimensions,
                'rowLimit': row_limit,
                'startRow': start_row
            }
            response = service.searchanalytics().query(siteUrl=site_url, body=request).execute()

            if 'rows' in response:
                rows = response['rows']
                all_data.extend(rows)
                
                # Check if all data has been fetched
                if len(rows) < row_limit:
                    print(f"Retrieved {len(rows)} rows. Total for this query: {len(all_data)}.")
                    break 
                
                print(f"Retrieved {len(rows)} rows, fetching more...")
                start_row += row_limit
            else:
                print("No more rows found.")
                break
        except HttpError as e:
            print(f"An HTTP error occurred: {e}")
            return None
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
            return None
            
    if not all_data:
        return pd.DataFrame()

    # Convert list of dictionaries to a DataFrame
    df = pd.DataFrame(all_data)

    # The 'keys' column contains a list of dimension values. Unpack it.
    for i, dimension_name in enumerate(dimensions):
        df[dimension_name] = df['keys'].apply(lambda x: x[i])
        
    df = df.drop(columns=['keys'])
    
    # Ensure metric columns are numeric
    for col in ['clicks', 'impressions', 'ctr', 'position']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        
    return df


def main():
    """Main function to run the snapshot report."""
    parser = argparse.ArgumentParser(description='Generate a single-period performance snapshot from Google Search Console.')
    parser.add_argument('site_url', help='The URL of the site to analyse. Use sc-domain: for a domain property.')
    parser.add_argument('--use-cache', action='store_true', help='Use cached CSV files from a previous run if they exist.')

    date_group = parser.add_mutually_exclusive_group()
    date_group.add_argument('--start-date', help='Start date in YYYY-MM-DD format.')
    date_group.add_argument('--end-date', help='End date in YYYY-MM-DD format. Used only with --start-date.')
    date_group.add_argument('--last-24-hours', action='store_true', help='Use the last 24 hours for the report.')
    date_group.add_argument('--last-7-days', action='store_true', help='Use the last 7 days for the report.')
    date_group.add_argument('--last-28-days', action='store_true', help='Use the last 28 days for the report.')
    date_group.add_argument('--last-month', action='store_true', help='Use the last calendar month for the report.')
    date_group.add_argument('--last-quarter', action='store_true', help='Use the last quarter for the report.')
    date_group.add_argument('--last-3-months', action='store_true', help='Use the last 3 months for the report. (Default)')
    date_group.add_argument('--last-6-months', action='store_true', help='Use the last 6 months for the report.')
    date_group.add_argument('--last-12-months', action='store_true', help='Use the last 12 months for the report.')
    date_group.add_argument('--last-16-months', action='store_true', help='Use the last 16 months for the report.')
    
    args = parser.parse_args()
    site_url = args.site_url

    # Set default date range if none is chosen
    if not any([
        args.start_date, args.last_24_hours, args.last_7_days, args.last_28_days,
        args.last_month, args.last_quarter, args.last_3_months,
        args.last_6_months, args.last_12_months, args.last_16_months
    ]):
        args.last_month = True

    print("Starting snapshot report...")
    
    # Authenticate GSC service once
    service = get_gsc_service()
    if not service:
        return

    latest_available_date = get_latest_available_gsc_date(service, site_url)
    
    if args.start_date and args.end_date:
        start_date = args.start_date
        end_date = args.end_date
        period_label = "custom-period"
    elif args.last_24_hours:
        # GSC data is often delayed by 2 days, so last 24 hours means the day before yesterday
        start_date = (latest_available_date - timedelta(days=1)).strftime('%Y-%m-%d')
        end_date = (latest_available_date - timedelta(days=1)).strftime('%Y-%m-%d')
        period_label = "last-24-hours"
    elif args.last_7_days:
        start_date = (latest_available_date - timedelta(days=6)).strftime('%Y-%m-%d')
        end_date = latest_available_date.strftime('%Y-%m-%d')
        period_label = "last-7-days"
    elif args.last_28_days:
        start_date = (latest_available_date - timedelta(days=27)).strftime('%Y-%m-%d')
        end_date = latest_available_date.strftime('%Y-%m-%d')
        period_label = "last-28-days"
    elif args.last_month:
        first_day_of_current_month = latest_available_date.replace(day=1)
        last_day_of_previous_month = first_day_of_current_month - timedelta(days=1)
        start_date = last_day_of_previous_month.replace(day=1).strftime('%Y-%m-%d')
        end_date = last_day_of_previous_month.strftime('%Y-%m-%d')
        period_label = "last-month"
    elif args.last_quarter:
        current_quarter = (latest_available_date.month - 1) // 3
        end_date_dt = datetime(latest_available_date.year, 3 * current_quarter + 1, 1).date() - timedelta(days=1)
        start_date_dt = end_date_dt.replace(day=1) - relativedelta(months=2)
        start_date = start_date_dt.strftime('%Y-%m-%d')
        end_date = end_date_dt.strftime('%Y-%m-%d')
        period_label = "last-quarter"
    elif args.last_6_months:
        start_date = (latest_available_date - relativedelta(months=6) + timedelta(days=1)).strftime('%Y-%m-%d')
        end_date = latest_available_date.strftime('%Y-%m-%d')
        period_label = "last-6-months"
    elif args.last_12_months:
        start_date = (latest_available_date - relativedelta(months=12) + timedelta(days=1)).strftime('%Y-%m-%d')
        end_date = latest_available_date.strftime('%Y-%m-%d')
        period_label = "last-12-months"
    elif args.last_16_months:
        start_date = (latest_available_date - relativedelta(months=16) + timedelta(days=1)).strftime('%Y-%m-%d')
        end_date = latest_available_date.strftime('%Y-%m-%d')
        period_label = "last-16-months"
    else: # Default to last 3 months
        start_date = (latest_available_date - relativedelta(months=3) + timedelta(days=1)).strftime('%Y-%m-%d')
        end_date = latest_available_date.strftime('%Y-%m-%d')
        period_label = "last-3-months"

    # Define output paths
    if site_url.startswith('sc-domain:'):
        host_plain = site_url.replace('sc-domain:', '')
    else:
        host_plain = urlparse(site_url).netloc
    
    host_dir = host_plain.replace('www.', '')
    output_dir = os.path.join('output', host_dir)
    os.makedirs(output_dir, exist_ok=True)
    host_for_filename = host_dir.replace('.', '-')

    base_file_prefix = f"snapshot-{host_for_filename}-{period_label}-{start_date}-to-{end_date}"
    
    pages_csv_path = os.path.join(output_dir, f"{base_file_prefix}-pages.csv")
    devices_csv_path = os.path.join(output_dir, f"{base_file_prefix}-devices.csv")
    countries_csv_path = os.path.join(output_dir, f"{base_file_prefix}-countries.csv")
    html_output_path = os.path.join(output_dir, f"{base_file_prefix}-report.html")

    use_cache = args.use_cache and os.path.exists(pages_csv_path) and os.path.exists(devices_csv_path) and os.path.exists(countries_csv_path)

    if use_cache:
        print("Found cached data for all dimensions. Using it to generate report.")
        df_pages = pd.read_csv(pages_csv_path)
        df_devices = pd.read_csv(devices_csv_path)
        df_countries = pd.read_csv(countries_csv_path)
    else:
        print(f"Using date range: {start_date} to {end_date}")


        # Fetch data for different dimensions
        df_pages = get_gsc_data(service, site_url, start_date, end_date, ['page'])
        df_devices = get_gsc_data(service, site_url, start_date, end_date, ['device'])
        df_countries = get_gsc_data(service, site_url, start_date, end_date, ['country'])

        if df_pages.empty:
            print("No page data found for the specified period. Exiting.")
            return
            
        # Save dataframes to CSV to be used as cache
        try:
            df_pages.to_csv(pages_csv_path, index=False, encoding='utf-8')
            df_devices.to_csv(devices_csv_path, index=False, encoding='utf-8')
            df_countries.to_csv(countries_csv_path, index=False, encoding='utf-8')
            print(f"\nSuccessfully exported data to CSV files in {output_dir}")
            print(f"Hint: To recreate this report from the saved data, use the --use-cache flag.")
        except PermissionError:
            print(f"\nError: Permission denied when trying to write to the output directory.")
            return

    # --- Analysis for HTML Observations ---
    # Top pages by clicks
    df_top_clicks = df_pages.sort_values(by='clicks', ascending=False).head(20)

    # Top pages by impressions
    df_top_impressions = df_pages.sort_values(by='impressions', ascending=False).head(20)

    # High impressions, low CTR opportunities
    low_ctr_threshold_impressions = 1000
    low_ctr_threshold_ctr = 0.01 
    df_low_ctr = df_pages[
        (df_pages['impressions'] >= low_ctr_threshold_impressions) &
        (df_pages['ctr'] < low_ctr_threshold_ctr)
    ].sort_values(by='impressions', ascending=False).head(20)

    try:
        # Generate and save HTML report
        html_output = create_snapshot_html_report(
            page_title=f"Performance Snapshot for {host_dir}",
            period_str=f"{start_date} to {end_date}",
            df_top_clicks=df_top_clicks,
            df_top_impressions=df_top_impressions,
            df_low_ctr=df_low_ctr,
            df_devices=df_devices,
            df_countries=df_countries
        )
        with open(html_output_path, 'w', encoding='utf-8') as f:
            f.write(html_output)
        print(f"Successfully created HTML report at {html_output_path}")
    except PermissionError:
        print(f"\nError: Permission denied when trying to write to the output directory.")
        print(f"Please make sure you have write permissions for the directory: {output_dir}")
        print(f"Also, check if the file is already open in another program: {html_output_path}")


def create_snapshot_html_report(page_title, period_str, df_top_clicks, df_top_impressions, df_low_ctr, df_devices, df_countries):
    """Generates an HTML report from the snapshot analysis dataframes."""
    
    # Helper to convert dataframe to HTML table with Bootstrap classes
    def df_to_html(df, table_id, float_format="%.2f"):
        if df.empty:
            return "<p>No data available for this section.</p>"
        # Custom styling for CTR and Position columns
        if 'ctr' in df.columns:
            df['ctr'] = df['ctr'].apply(lambda x: f"{x:.2%}")
        if 'position' in df.columns:
            df['position'] = df['position'].apply(lambda x: f"{x:.2f}")

        # Add formatting for clicks and impressions
        for col in df.columns:
            if 'clicks' in col or 'impressions' in col:
                # Ensure the column is numeric before formatting
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
                df[col] = df[col].apply(lambda x: f"{int(x):,}") # Format as integer with commas

        return df.to_html(classes="table table-striped table-hover", index=False, table_id=table_id, border=0, float_format=float_format)

    html_template = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{page_title}</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body {{ padding: 2rem; }}
        .table-responsive {{ max-height: 500px; overflow-y: auto; }}
        h2 {{ border-bottom: 2px solid #dee2e6; padding-bottom: 0.5rem; margin-top: 2rem; }}
        footer {{ margin-top: 3rem; text-align: center; color: #6c757d; }}
        .table thead th {{ text-align: center; }}
    </style>
</head>
<body>
    <div class="container-fluid">
        <h1 class="mb-3">{page_title}</h1>
        <p class="text-muted">Analysis for the period: {period_str}</p>

        <h2>Top Pages by Clicks</h2>
        <p class="text-muted">The pages driving the most organic clicks during this period.</p>
        <div class="table-responsive">
            {df_to_html(df_top_clicks, 'table-top-clicks')}
        </div>

        <h2>Top Pages by Impressions</h2>
        <p class="text-muted">The pages with the highest visibility in search results during this period.</p>
        <div class="table-responsive">
            {df_to_html(df_top_impressions, 'table-top-impressions')}
        </div>

        <h2>High Impressions, Low CTR Opportunities</h2>
        <p class="text-muted">These pages are displayed frequently in search results but receive relatively few clicks. Consider optimising their titles and meta descriptions to improve their Click-Through Rate (CTR).</p>
        <div class="table-responsive">
            {df_to_html(df_low_ctr, 'table-low-ctr')}
        </div>

        <h2>Performance by Device</h2>
        <p class="text-muted">Breakdown of organic search performance across different device types.</p>
        <div class="table-responsive">
            {df_to_html(df_devices, 'table-devices')}
        </div>

        <h2>Performance by Country</h2>
        <p class="text-muted">Breakdown of organic search performance by country, indicating where your audience is located.</p>
        <div class="table-responsive">
            {df_to_html(df_countries, 'table-countries')}
        </div>
        
    </div>

    <footer>
        <p><a href="../../resources/how-to-read-the-snapshot-report.html">How to Read Reports (General Guide)</a></p>
        <p><a href="https://github.com/liamdelahunty/gsc-exporter" target="_blank">gsc-exporter</a></p>
    </footer>
</body>
</html>
"""
    return html_template

if __name__ == '__main__':
    main()

