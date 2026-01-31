"""
Generates a page-level report with key performance metrics and unique query counts.

This script fetches performance data for a specified date range and creates a CSV
and HTML report listing all pages along with their clicks, impressions, CTR, and
the number of unique queries driving traffic to each page.

Usage:
    python page-level-report.py <site_url> [date_range_flag]

Example:
    python page-level-report.py https://www.example.com --last-28-days
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


def get_gsc_data(service, site_url, start_date, end_date, dimensions, search_type='web'):
    """Fetches performance data from GSC for a given date range and dimensions."""
    all_data = []
    start_row = 0
    row_limit = 25000 
    
    print(f"Fetching {search_type} data for dimensions: {', '.join(dimensions)}...")

    while True:
        try:
            request = {
                'startDate': start_date,
                'endDate': end_date,
                'dimensions': dimensions,
                'searchType': search_type,
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

    df = pd.DataFrame(all_data)
    df[dimensions] = pd.DataFrame(df['keys'].tolist(), index=df.index)
    df = df.drop(columns=['keys'])
    
    for col in ['clicks', 'impressions', 'ctr', 'position']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        
    return df

def create_html_report(df, report_title, period_str, summary_data, limit=None, total_rows=None):
    """Generates an HTML report from the DataFrame."""

    df_html = df.copy()

    # Format numbers for readability
    df_html['clicks'] = df_html['clicks'].apply(lambda x: f"{int(x):,}")
    df_html['impressions'] = df_html['impressions'].apply(lambda x: f"{int(x):,}")
    if 'Query #' in df_html.columns:
        df_html['Query #'] = df_html['Query #'].apply(lambda x: f"{int(x):,}")
    df_html['ctr'] = df_html['ctr'].apply(lambda x: f"{x:.2%}")
    df_html['position'] = df_html['position'].apply(lambda x: f"{x:.2f}")

    # --- Truncation Alert ---
    truncation_alert_html = ""
    if limit is not None and total_rows is not None and total_rows > limit:
        truncation_alert_html = f"""
        <div class="alert alert-info">
            <strong>Report Truncated:</strong> This HTML report is showing the top <strong>{limit:,}</strong> pages out of a total of <strong>{total_rows:,}</strong>.
            The full, unfiltered data is available in the accompanying CSV file.
        </div>
        """

    # Manual HTML table generation using divs and bootstrap grid
    table_header = '''
<div class="container">
  <div class="row fw-bold py-2 bg-dark text-white">
    <div class="col-6">Page</div>
    <div class="col-1 text-end">Clicks</div>
    <div class="col-1 text-end">Impressions</div>
    <div class="col-1 text-end">CTR</div>
    <div class="col-1 text-end">Position</div>
    <div class="col-2 text-end">Query #</div>
  </div>
'''

    table_body = ""
    for i, row in df_html.iterrows():
        bg_class = "bg-light" if i % 2 == 0 else ""
        table_body += f'''
  <div class="row py-2 border-bottom {bg_class}">
    <div class="col-6" style="word-wrap: break-word; overflow-wrap: break-word;">{row['page']}</div>
    <div class="col-1 text-end">{row['clicks']}</div>
    <div class="col-1 text-end">{row['impressions']}</div>
    <div class="col-1 text-end">{row['ctr']}</div>
    <div class="col-1 text-end">{row['position']}</div>
    <div class="col-2 text-end">{row['Query #']}</div>
  </div>
'''

    report_body = table_header + table_body + '</div>'

    summary_html = "<h2 class='mt-5'>Overall Summary</h2><table class='table table-bordered' style='max-width: 500px;'>"
    for key, value in summary_data.items():
        summary_html += f"<tr><th style='width: 50%;'>{key}</th><td>{value}</td></tr>"
    summary_html += "</table>"

    return f"""
<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{report_title}</title><link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
<style>
body {{ padding: 2rem; }}
h1, h2 {{ border-bottom: 2px solid #dee2e6; padding-bottom: .5rem; margin-top: 2rem; }}
footer {{ margin-top: 3rem; text-align: center; color: #6c757d; }}
</style></head>
<body><div class="container-fluid"><h1>{report_title}</h1><p class="text-muted">Analysis for the period: {period_str}</p>
{truncation_alert_html}
{report_body}
{summary_html}
</div>
<footer><p><a href="https://github.com/liamdelahunty/gsc-exporter" target="_blank">gsc-exporter</a></p></footer></body></html>"""


def main():
    """Main function to run the page-level report."""
    parser = argparse.ArgumentParser(
        description='Generate a page-level report with clicks, impressions, CTR, and unique query counts.',
        epilog='Example usage:\n'
               '  python page-level-report.py https://www.example.com --last-28-days\n'
               '  To use cached data: python page-level-report.py https://www.example.com --last-28-days --use-cache\n'
    )
    parser.add_argument('site_url', help='The URL of the site to analyse. Use sc-domain: for a domain property.')
    parser.add_argument('--search-type', default='web', choices=['web', 'image', 'video', 'news', 'discover', 'googleNews'], help='The search type to query. Defaults to "web".')
    parser.add_argument('--strip-query-strings', action='store_true', help='Remove query strings from page URLs before aggregating data.')
    parser.add_argument('--use-cache', action='store_true', help='Use a cached CSV file from a previous run if it exists.')
    parser.add_argument('--limit', type=int, default=250, help='Limit the number of pages in the HTML report. Default is 250.')

    date_group = parser.add_mutually_exclusive_group()
    date_group.add_argument('--start-date', help='Start date in YYYY-MM-DD format.')
    date_group.add_argument('--last-24-hours', action='store_true', help='Use the last 24 hours for the report.')
    date_group.add_argument('--last-7-days', action='store_true', help='Use the last 7 days for the report.')
    date_group.add_argument('--last-28-days', action='store_true', help='Use the last 28 days for the report.')
    date_group.add_argument('--last-month', action='store_true', help='Use the last calendar month for the report. (Default)')
    date_group.add_argument('--last-quarter', action='store_true', help='Use the last quarter for the report.')
    date_group.add_argument('--last-3-months', action='store_true', help='Use the last 3 months for the report.')
    date_group.add_argument('--last-6-months', action='store_true', help='Use the last 6 months for the report.')
    date_group.add_argument('--last-12-months', action='store_true', help='Use the last 12 months for the report.')
    date_group.add_argument('--last-16-months', action='store_true', help='Use the last 16 months for the report.')

    parser.add_argument('--end-date', help='End date in YYYY-MM-DD format. Used only with --start-date.')
    
    args = parser.parse_args()
    site_url = args.site_url

    # Set default date range if none is chosen
    if not any([
        args.start_date, args.last_24_hours, args.last_7_days, args.last_28_days,
        args.last_month, args.last_quarter, args.last_3_months,
        args.last_6_months, args.last_12_months, args.last_16_months
    ]):
        args.last_month = True

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
    elif args.last_3_months:
        start_date = (latest_available_date - relativedelta(months=3) + timedelta(days=1)).strftime('%Y-%m-%d')
        end_date = latest_available_date.strftime('%Y-%m-%d')
        period_label = "last-3-months"
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
    
    # Define output paths
    if site_url.startswith('sc-domain:'):
        host_plain = site_url.replace('sc-domain:', '')
    else:
        host_plain = urlparse(site_url).netloc
    
    host_dir = host_plain.replace('www.', '')
    output_dir = os.path.join('output', host_dir)
    os.makedirs(output_dir, exist_ok=True)
    host_for_filename = host_dir.replace('.', '-')

    filename_suffix = "-no-query" if args.strip_query_strings else ""
    file_prefix = f"page-level-report-{host_for_filename}-{period_label}-{start_date}-to-{end_date}{filename_suffix}"
    csv_output_path = os.path.join(output_dir, f"{file_prefix}.csv")
    html_output_path = os.path.join(output_dir, f"{file_prefix}.html")

    page_level_data = None
    summary_data = None
    df_page_query = pd.DataFrame() # Initialize df_page_query here

    if args.use_cache and os.path.exists(csv_output_path):
        print(f"Found cached data at {csv_output_path}. Using it to generate report.")
        page_level_data = pd.read_csv(csv_output_path)
        # Manually convert 'Query #' column back to integer if it exists
        if 'Query #' in page_level_data.columns:
             page_level_data.rename(columns={'Query #': 'query_count'}, inplace=True)

    if page_level_data is None:
        print(f"Using date range: {start_date} to {end_date}")
        # service is already authenticated above
        # if not service:
        #     return

        # Fetch page-level data (unsampled)
        df_pages = get_gsc_data(service, site_url, start_date, end_date, ['page'], args.search_type)
        if df_pages.empty:
            print("No page data found for the specified period. Exiting.")
            return
            
        # Fetch page-query data (potentially sampled) to get query counts
        df_page_query = get_gsc_data(service, site_url, start_date, end_date, ['page', 'query'], args.search_type)
        
        # Strip query strings if the flag is set
        if args.strip_query_strings:
            print("Stripping query strings from page URLs...")
            df_pages['page'] = df_pages['page'].str.split('?').str[0]
            if not df_page_query.empty:
                df_page_query['page'] = df_page_query['page'].str.split('?').str[0]
            
            df_pages = df_pages.groupby('page').agg(
                clicks=('clicks', 'sum'),
                impressions=('impressions', 'sum'),
                impression_weighted_position=('impressions', lambda x: (x * df_pages.loc[x.index, 'position']).sum())
            ).reset_index()
            df_pages['ctr'] = df_pages.apply(lambda row: row['clicks'] / row['impressions'] if row['impressions'] > 0 else 0, axis=1)
            df_pages['position'] = df_pages.apply(lambda row: row['impression_weighted_position'] / row['impressions'] if row['impressions'] > 0 else 0, axis=1)
            df_pages.drop(columns=['impression_weighted_position'], inplace=True)

        # Calculate query counts from the page-query data
        if not df_page_query.empty:
            query_counts = df_page_query.groupby('page')['query'].nunique().reset_index()
            query_counts.rename(columns={'query': 'query_count'}, inplace=True)
            df_pages = pd.merge(df_pages, query_counts, on='page', how='left')
            df_pages['query_count'] = df_pages['query_count'].fillna(0)
        else:
            df_pages['query_count'] = 0

        # Finalize the report dataframe
        page_level_data = df_pages[['page', 'clicks', 'impressions', 'ctr', 'position', 'query_count']].copy()
        page_level_data = page_level_data.sort_values(by='clicks', ascending=False)
        
        # Save CSV
        page_level_data.to_csv(csv_output_path, index=False, encoding='utf-8')
        print(f"\nSuccessfully exported page-level data to {csv_output_path}")
        print(f"Hint: To recreate this report from the saved data, use the --use-cache flag.")

    # Always calculate summary data from the page_level_data dataframe
    total_pages = len(page_level_data)
    total_clicks = page_level_data['clicks'].sum()
    total_impressions = page_level_data['impressions'].sum()
    avg_ctr = total_clicks / total_impressions if total_impressions > 0 else 0
    total_impression_weighted_position = (page_level_data['impressions'] * page_level_data['position']).sum()
    avg_position = total_impression_weighted_position / total_impressions if total_impressions > 0 else 0
    
    # Total unique queries cannot be determined from the cached file, so handle this case
    if args.use_cache and os.path.exists(csv_output_path):
        if 'query_count' in page_level_data.columns:
            total_unique_queries_str = f"{page_level_data['query_count'].sum():,.0f}"
        else:
            total_unique_queries_str = "N/A (from cache)"
    else:
        total_unique_queries = df_page_query['query'].nunique() if not df_page_query.empty else 0
        total_unique_queries_str = f"{total_unique_queries:,}"

    summary_data = {
        "Number of Pages": f"{total_pages:,}",
        "Total Clicks": f"{total_clicks:,.0f}",
        "Total Impressions": f"{total_impressions:,.0f}",
        "Average CTR": f"{avg_ctr:.2%}",
        "Average Position": f"{avg_position:.2f}",
        "Total Unique Queries": total_unique_queries_str
    }
    
    # Rename column for HTML report
    page_level_data.rename(columns={'query_count': 'Query #'}, inplace=True)
    
    # Apply limit for HTML report
    html_df = page_level_data.head(args.limit)

    try:
        # Generate and save HTML report
        html_output = create_html_report(
            df=html_df,
            report_title=f"Page-Level Report for {host_dir}",
            period_str=f"{start_date} to {end_date}",
            summary_data=summary_data,
            limit=args.limit,
            total_rows=len(page_level_data)
        )
        with open(html_output_path, 'w', encoding='utf-8') as f:
            f.write(html_output)
        print(f"Successfully created HTML report at {html_output_path}")

    except Exception as e:
        print(f"An error occurred during file generation: {e}")

if __name__ == '__main__':
    main()
