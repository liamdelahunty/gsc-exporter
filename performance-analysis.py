"""
A script for performance analysis of Google Search Console data.

This script fetches performance data (clicks, impressions, CTR, position) for two 
different time periods, compares them, and generates a report highlighting best/worst 
performing pages and pages with low CTR.

Usage:
    python performance-analysis.py <site_url> [comparison_flag]

Example:
    python performance-analysis.py https://www.example.com --compare-last-28-days
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

def get_performance_data(service, site_url, start_date, end_date):
    """Fetches performance data from GSC for a given date range."""
    all_data = []
    start_row = 0
    row_limit = 25000 
    print(f"Fetching data for {site_url} from {start_date} to {end_date}...")

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

    # Convert list of dictionaries to a DataFrame
    df = pd.DataFrame(all_data)
    df['page'] = df['keys'].apply(lambda x: x[0])
    df = df.drop(columns=['keys'])
    
    # Ensure all columns are numeric, setting non-numeric to NaN
    for col in ['clicks', 'impressions', 'ctr', 'position']:
        df[col] = pd.to_numeric(df[col], errors='coerce')
        
    return df

def main():
    """Main function to run the performance analysis."""
    parser = argparse.ArgumentParser(description='Analyze Google Search Console performance data.')
    parser.add_argument('site_url', help='The URL of the site to analyze. Use sc-domain: for a domain property.')

    date_group = parser.add_mutually_exclusive_group()
    date_group.add_argument('--start-date', help='Start date in YYYY-MM-DD format for the current period.')
    date_group.add_argument('--last-24-hours', action='store_true', help='Compare the last 24 hours to the previous 24 hours.')
    date_group.add_argument('--last-7-days', action='store_true', help='Compare the last 7 days to the previous 7 days.')
    date_group.add_argument('--last-28-days', action='store_true', help='Compare last 28 days to the previous 28 days. (Default)')
    date_group.add_argument('--last-month', action='store_true', help='Compare last full month to the previous month.')
    date_group.add_argument('--last-quarter', action='store_true', help='Compare last full quarter to the previous quarter.')
    date_group.add_argument('--last-3-months', action='store_true', help='Compare last 3 months to the previous 3 months.')
    date_group.add_argument('--last-6-months', action='store_true', help='Compare last 6 months to the previous 6 months.')
    date_group.add_argument('--last-12-months', action='store_true', help='Compare last 12 months to the previous 12 months.')
    date_group.add_argument('--last-16-months', action='store_true', help='Compare last 16 months to the previous 16 months.')

    parser.add_argument('--end-date', help='End date in YYYY-MM-DD format for the current period.')
    
    args = parser.parse_args()
    site_url = args.site_url

    # Set default comparison if none is chosen
    if not any([
        args.start_date, args.last_24_hours, args.last_7_days, args.last_28_days, 
        args.last_month, args.last_quarter, args.last_3_months, 
        args.last_6_months, args.last_12_months, args.last_16_months
    ]):
        args.last_month = True

    print("Starting performance analysis...")
    
    today = date.today()
    
    if args.start_date and args.end_date:
        current_start_date = args.start_date
        current_end_date = args.end_date
        
        start_date_dt = datetime.strptime(current_start_date, '%Y-%m-%d').date()
        end_date_dt = datetime.strptime(current_end_date, '%Y-%m-%d').date()
        duration = (end_date_dt - start_date_dt).days
        
        previous_end_date_dt = start_date_dt - timedelta(days=1)
        previous_start_date_dt = previous_end_date_dt - timedelta(days=duration)
        
        previous_start_date = previous_start_date_dt.strftime('%Y-%m-%d')
        previous_end_date = previous_end_date_dt.strftime('%Y-%m-%d')
        
        period_label = f"custom-period"

    elif args.last_24_hours:
        current_start_date = (today - timedelta(days=2)).strftime('%Y-%m-%d')
        current_end_date = (today - timedelta(days=2)).strftime('%Y-%m-%d')
        previous_start_date = (today - timedelta(days=3)).strftime('%Y-%m-%d')
        previous_end_date = (today - timedelta(days=3)).strftime('%Y-%m-%d')
        period_label = "last-24-hours"
        
    elif args.last_7_days:
        current_start_date = (today - timedelta(days=7)).strftime('%Y-%m-%d')
        current_end_date = today.strftime('%Y-%m-%d')
        previous_start_date = (today - timedelta(days=14)).strftime('%Y-%m-%d')
        previous_end_date = (today - timedelta(days=8)).strftime('%Y-%m-%d')
        period_label = "last-7-days"

    elif args.last_28_days:
        current_start_date = (today - timedelta(days=28)).strftime('%Y-%m-%d')
        current_end_date = today.strftime('%Y-%m-%d')
        previous_start_date = (today - timedelta(days=56)).strftime('%Y-%m-%d')
        previous_end_date = (today - timedelta(days=29)).strftime('%Y-%m-%d')
        period_label = "last-28-days"

    elif args.last_month:
        first_day_of_current_month = today.replace(day=1)
        current_end_date_dt = first_day_of_current_month - timedelta(days=1)
        current_start_date_dt = current_end_date_dt.replace(day=1)
        current_start_date = current_start_date_dt.strftime('%Y-%m-%d')
        current_end_date = current_end_date_dt.strftime('%Y-%m-%d')
        
        previous_end_date_dt = current_start_date_dt - timedelta(days=1)
        previous_start_date_dt = previous_end_date_dt.replace(day=1)
        previous_start_date = previous_start_date_dt.strftime('%Y-%m-%d')
        previous_end_date = previous_end_date_dt.strftime('%Y-%m-%d')
        period_label = "last-month"
        
    elif args.last_quarter:
        current_quarter = (today.month - 1) // 3
        current_end_date_dt = datetime(today.year, 3 * current_quarter + 1, 1).date() - timedelta(days=1)
        current_start_date_dt = current_end_date_dt.replace(day=1) - relativedelta(months=2)
        current_start_date = current_start_date_dt.strftime('%Y-%m-%d')
        current_end_date = current_end_date_dt.strftime('%Y-%m-%d')

        previous_end_date_dt = current_start_date_dt - timedelta(days=1)
        previous_start_date_dt = previous_end_date_dt.replace(day=1) - relativedelta(months=2)
        previous_start_date = previous_start_date_dt.strftime('%Y-%m-%d')
        previous_end_date = previous_end_date_dt.strftime('%Y-%m-%d')
        period_label = "last-quarter"
        
    elif args.last_3_months:
        current_start_date = (today - relativedelta(months=3)).strftime('%Y-%m-%d')
        current_end_date = today.strftime('%Y-%m-%d')
        previous_start_date = (today - relativedelta(months=6)).strftime('%Y-%m-%d')
        previous_end_date = (today - relativedelta(months=3) - timedelta(days=1)).strftime('%Y-%m-%d')
        period_label = "last-3-months"

    elif args.last_6_months:
        current_start_date = (today - relativedelta(months=6)).strftime('%Y-%m-%d')
        current_end_date = today.strftime('%Y-%m-%d')
        previous_start_date = (today - relativedelta(months=12)).strftime('%Y-%m-%d')
        previous_end_date = (today - relativedelta(months=6) - timedelta(days=1)).strftime('%Y-%m-%d')
        period_label = "last-6-months"

    elif args.last_12_months:
        current_start_date = (today - relativedelta(months=12)).strftime('%Y-%m-%d')
        current_end_date = today.strftime('%Y-%m-%d')
        previous_start_date = (today - relativedelta(months=24)).strftime('%Y-%m-%d')
        previous_end_date = (today - relativedelta(months=12) - timedelta(days=1)).strftime('%Y-%m-%d')
        period_label = "last-12-months"

    elif args.last_16_months:
        current_start_date = (today - relativedelta(months=16)).strftime('%Y-%m-%d')
        current_end_date = today.strftime('%Y-%m-%d')
        previous_start_date = (today - relativedelta(months=32)).strftime('%Y-%m-%d')
        previous_end_date = (today - relativedelta(months=16) - timedelta(days=1)).strftime('%Y-%m-%d')
        period_label = "last-16-months"

    print(f"Current period: {current_start_date} to {current_end_date}")
    print(f"Previous period: {previous_start_date} to {previous_end_date}")

    service = get_gsc_service()
    if not service:
        return

    # Fetch data for both periods
    df_current = get_performance_data(service, args.site_url, current_start_date, current_end_date)
    df_previous = get_performance_data(service, args.site_url, previous_start_date, previous_end_date)

    if df_current.empty and df_previous.empty:
        print("No data found for either period. Exiting.")
        return

    # --- Data Processing and Comparison ---
    df_current.rename(columns={
        'clicks': 'clicks_current', 'impressions': 'impressions_current',
        'ctr': 'ctr_current', 'position': 'position_current'
    }, inplace=True)

    df_previous.rename(columns={
        'clicks': 'clicks_previous', 'impressions': 'impressions_previous',
        'ctr': 'ctr_previous', 'position': 'position_previous'
    }, inplace=True)

    # Merge the two dataframes
    if not df_previous.empty:
        df_merged = pd.merge(df_current, df_previous, on='page', how='outer')
    else:
        df_merged = df_current
        for col in ['clicks_previous', 'impressions_previous', 'ctr_previous', 'position_previous']:
            df_merged[col] = 0


    df_merged.fillna(0, inplace=True)

    # Calculate deltas
    df_merged['clicks_delta'] = df_merged['clicks_current'] - df_merged['clicks_previous']
    df_merged['impressions_delta'] = df_merged['impressions_current'] - df_merged['impressions_previous']
    df_merged['ctr_delta'] = df_merged['ctr_current'] - df_merged['ctr_previous']
    # For position, a smaller number is better, so a negative delta is an improvement
    df_merged['position_delta'] = df_merged['position_previous'] - df_merged['position_current']
    
    # Sort for analysis
    df_best = df_merged.sort_values(by='clicks_delta', ascending=False).head(20)
    df_worst = df_merged.sort_values(by='clicks_delta', ascending=True).head(20)

    # Identify low CTR opportunities (high impressions, low CTR)
    # Thresholds: at least 1000 impressions and CTR < 1%
    low_ctr_threshold_impressions = 1000
    low_ctr_threshold_ctr = 0.01
    df_low_ctr = df_current[
        (df_current['impressions_current'] >= low_ctr_threshold_impressions) &
        (df_current['ctr_current'] < low_ctr_threshold_ctr)
    ].sort_values(by='impressions_current', ascending=False).head(20)

    # Identify Rising Stars
    rising_stars_prev_impressions_max = 50
    rising_stars_curr_impressions_min = 500
    df_rising_stars = df_merged[
        (df_merged['impressions_previous'] < rising_stars_prev_impressions_max) &
        (df_merged['impressions_current'] >= rising_stars_curr_impressions_min)
    ].sort_values(by='impressions_current', ascending=False).head(20)

    # Identify Falling Stars
    falling_stars_prev_clicks_min = 500
    falling_stars_curr_clicks_max = 50
    df_falling_stars = df_merged[
        (df_merged['clicks_previous'] >= falling_stars_prev_clicks_min) &
        (df_merged['clicks_current'] < falling_stars_curr_clicks_max)
    ].sort_values(by='clicks_delta', ascending=True).head(20)

    # --- Output Generation ---
    if site_url.startswith('sc-domain:'):
        host_plain = site_url.replace('sc-domain:', '')
    else:
        host_plain = urlparse(site_url).netloc
    
    host_dir = host_plain.replace('www.', '')
    output_dir = os.path.join('output', host_dir)
    os.makedirs(output_dir, exist_ok=True)
    host_for_filename = host_dir.replace('.', '-')

    csv_file_name = f"performance-comparison-{host_for_filename}-{period_label}-{current_start_date}-to-{current_end_date}.csv"
    csv_output_path = os.path.join(output_dir, csv_file_name)

    html_file_name = f"performance-report-{host_for_filename}-{period_label}-{current_start_date}-to-{current_end_date}.html"
    html_output_path = os.path.join(output_dir, html_file_name)
    try:
        # Save detailed comparison to CSV
        df_merged.to_csv(csv_output_path, index=False, encoding='utf-8')
        print(f"\nSuccessfully exported comparison data to {csv_output_path}")

        # Generate and save HTML report
        html_output = create_html_report(
            page_title=f"Performance Analysis for {host_dir}",
            current_period_str=f"{current_start_date} to {current_end_date}",
            previous_period_str=f"{previous_start_date} to {previous_end_date}",
            df_best=df_best,
            df_worst=df_worst,
            df_low_ctr=df_low_ctr,
            df_rising_stars=df_rising_stars,
            df_falling_stars=df_falling_stars
        )
        with open(html_output_path, 'w', encoding='utf-8') as f:
            f.write(html_output)
        print(f"Successfully created HTML report at {html_output_path}")
    except PermissionError:
        print(f"\nError: Permission denied when trying to write to the output directory.")
        print(f"Please make sure you have write permissions for the directory: {output_dir}")
        print(f"Also, check if the file is already open in another program: {csv_file_name} or {html_file_name}")


def create_html_report(page_title, current_period_str, previous_period_str, df_best, df_worst, df_low_ctr, df_rising_stars, df_falling_stars):
    """Generates an HTML report from the analysis dataframes."""
    
    # Helper to convert dataframe to HTML table with Bootstrap classes
    def df_to_html(df, table_id):
        if df.empty:
            return "<p>No data available for this section.</p>"
        return df.to_html(classes="table table-striped table-hover", index=False, table_id=table_id, border=0)

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
        <p class="text-muted">Current Period: {current_period_str} | Previous Period: {previous_period_str}</p>

        <h2>Best Performing Content (by Clicks Change)</h2>
        <p class="text-muted">These pages have seen the largest increase in clicks. Analyse them to understand what is working well.</p>
        <div class="table-responsive">
            {df_to_html(df_best, 'table-best')}
        </div>

        <h2>Worst Performing Content (by Clicks Change)</h2>
        <p class="text-muted">These pages have lost the most clicks. Investigate whether this is due to content decay, seasonality, or new competition.</p>
        <div class="table-responsive">
            {df_to_html(df_worst, 'table-worst')}
        </div>
        
        <h2>Rising Stars</h2>
        <p class="text-muted">Pages with minimal previous visibility that are now gaining significant impressions. These may be new content pieces or topics gaining traction.</p>
        <div class="table-responsive">
            {df_to_html(df_rising_stars, 'table-rising')}
        </div>

        <h2>Falling Stars</h2>
        <p class="text-muted">Previously strong pages that have experienced a dramatic drop in clicks. These require urgent attention to diagnose the cause of the decline.</p>
        <div class="table-responsive">
            {df_to_html(df_falling_stars, 'table-falling')}
        </div>

        <h2>High Impressions, Low CTR Opportunities</h2>
        <p class="text-muted">These pages are good candidates for title and meta description optimisation to improve their Click-Through Rate (CTR).</p>
        <div class="table-responsive">
            {df_to_html(df_low_ctr, 'table-low-ctr')}
        </div>
        
    </div>

    <footer>
        <p><a href="../../resources/how-to-read-the-performance-analysis-report.html">How to Read This Report</a></p>
        <p><a href="https://github.com/liamdelahunty/gsc-exporter" target="_blank">gsc-exporter</a></p>
    </footer>
</body>
</html>
"""
    return html_template




if __name__ == '__main__':
    main()
