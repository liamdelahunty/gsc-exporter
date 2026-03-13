"""
Generates a report that highlights keyword cannibalisation issues.

This script identifies keywords that multiple pages are ranking for, which
can cause SEO issues. It calculates the total potential clicks and impressions
a consolidated page could achieve.

The report is generated in HTML format, showing the top 100 cannibalised
keywords by impressions.

Usage:
    python keyword-cannibalisation-report.py <site_url> [--start-date <start_date>] [--end-date <end_date>]
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
import sys
import html
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
            
            print("A browser window will open for you to authorise access.")
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
                'dimensions': ['date'],
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

def is_data_available(service, site_url, date_to_check):
    """Checks if data is available for a specific date."""
    date_str = date_to_check.strftime('%Y-%m-%d')
    try:
        request = {
            'startDate': date_str,
            'endDate': date_str,
            'dimensions': ['date'],
            'rowLimit': 1
        }
        response = service.searchanalytics().query(siteUrl=site_url, body=request).execute()
        return 'rows' in response and response['rows']
    except HttpError:
        return False

def get_performance_data(service, site_url, start_date, end_date):
    """Fetches pages and queries data from GSC for a given date range."""
    all_data = []
    start_row = 0
    row_limit = 25000
    print(f"Fetching data for {site_url} from {start_date} to {end_date}...")
    while True:
        try:
            request = {
                'startDate': start_date,
                'endDate': end_date,
                'dimensions': ['query', 'page'],
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
    return all_data

def generate_accordion_html(report_df, top_100_cannibalised):
    """Generates the Bootstrap accordion HTML for the cannibalisation report."""
    accordion_id = "cannibalisationAccordion"
    
    header = """
    <div class="row fw-bold border-bottom pb-2 mb-2">
        <div class="col-md-6">Keyword</div>
        <div class="col-md-2 text-end">Clicks</div>
        <div class="col-md-2 text-end">Impressions</div>
        <div class="col-md-2 text-end">Pages</div>
    </div>
    """
    
    html_parts = [header, f'<div class="accordion" id="{accordion_id}">']

    # Use the ordered list of queries from the top_100_cannibalised dataframe
    # to ensure the report is sorted by impression opportunity.
    for index, summary_row in top_100_cannibalised.iterrows():
        query = summary_row['query']
        total_clicks = summary_row['total_clicks']
        total_impressions = summary_row['total_impressions']
        page_count = summary_row['page_count']

        # Create a unique ID for each accordion item
        collapse_id = f"collapse-{index}"
        header_id = f"header-{index}"
        
        # Filter the main dataframe to get all pages for the current query
        pages_for_query_df = report_df[report_df['query'] == query].copy()
        pages_for_query_df.sort_values(by=['clicks', 'impressions'], ascending=[False, False], inplace=True)

        # Format the numbers in the sub-table for better readability
        sub_group_html_df = pages_for_query_df.copy()
        sub_group_html_df['page'] = sub_group_html_df['page'].apply(lambda x: f'<a href="{x}" target="_blank">{x}</a>')
        sub_group_html_df['ctr'] = sub_group_html_df['ctr'].apply(lambda x: f"{x:.2%}")
        sub_group_html_df['position'] = sub_group_html_df['position'].apply(lambda x: f"{x:.2f}")
        sub_group_html_df['clicks'] = sub_group_html_df['clicks'].apply(lambda x: f"{x:,.0f}")
        sub_group_html_df['impressions'] = sub_group_html_df['impressions'].apply(lambda x: f"{x:,.0f}")

        sub_table_html = sub_group_html_df[['page', 'clicks', 'impressions', 'ctr', 'position']].to_html(
            classes="table table-sm table-striped",
            index=False,
            border=0,
            escape=False
        )

        accordion_item = f"""
        <div class="accordion-item">
            <h2 class="accordion-header" id="{header_id}">
                <button class="accordion-button collapsed" type="button" data-bs-toggle="collapse" data-bs-target="#{collapse_id}">
                    <div class="row w-100 align-items-center">
                        <div class="col-md-6 text-start"><strong>{html.escape(query)}</strong></div>
                        <div class="col-md-2 text-end">{total_clicks:,.0f}</div>
                        <div class="col-md-2 text-end">{total_impressions:,.0f}</div>
                        <div class="col-md-2 text-end">{page_count}</div>
                    </div>
                </button>
            </h2>
            <div id="{collapse_id}" class="accordion-collapse collapse" data-bs-parent="#{accordion_id}">
                <div class="accordion-body">
                    <div class="table-responsive">
                        {sub_table_html}
                    </div>
                </div>
            </div>
        </div>
        """
        html_parts.append(accordion_item)

    html_parts.append('</div>')
    return "".join(html_parts)

def create_html_report(site_url, start_date, end_date, report_df, top_100_cannibalised):
    """Generates the full HTML report for keyword cannibalisation."""

    report_title = "Keyword Cannibalisation Report"
    accordion_html = generate_accordion_html(report_df, top_100_cannibalised)

    return f"""
<!DOCTYPE html>
<html lang="en-GB">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{report_title}: {site_url}</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body {{ padding-top: 5rem; }}
        .table-responsive {{ max-height: 500px; }}
        .accordion-button:not(.collapsed) {{ background-color: #e7f1ff; }}
        .table th:not(:first-child), .table td:not(:first-child) {{ text-align: right; }}
        .table th:first-child, .table td:first-child {{ text-align: left; }}
    </style>
</head>
<body>
    <header class="navbar navbar-expand-lg navbar-light bg-light border-bottom mb-4 fixed-top">
        <div class="container-fluid">
            <div class="d-flex align-items-baseline">
                <h1 class="h3 mb-0 me-4">{report_title}</h1>
                <span class="text-muted me-4">{site_url}</span>
                <span class="text-muted">{start_date} to {end_date}</span>
            </div>
            <ul class="navbar-nav ms-auto">
                <li class="nav-item">
                    <a class="nav-link" href="https://github.com/liamdelahunty/gsc-exporter" target="_blank">GitHub</a>
                </li>
            </ul>
        </div>
    </header>

    <main class="container-fluid py-4">
        {accordion_html}
    </main>

    <footer class="footer mt-auto py-3 bg-light">
        <div class="container text-center">
            <p>This report highlights the top 100 keywords (by total impressions) that have multiple pages ranking for them.</p>
            <span class="text-muted">Report generated on {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</span>
        </div>
    </footer>
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
"""

def main():
    """Main function to run the script."""
    parser = argparse.ArgumentParser(
        description='Generates a report highlighting keyword cannibalisation issues.',
        epilog="""Example Usage:
  python keyword-cannibalisation-report.py https://www.example.com --last-month
""",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument('site_url', help='The URL of the site to analyse.')
    
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

    service = get_gsc_service()
    if not service:
        return

    latest_available_date = get_latest_available_gsc_date(service, args.site_url)

    if not any([
        args.start_date, args.last_24_hours, args.last_7_days, args.last_28_days,
        args.last_month, args.last_quarter, args.last_3_months,
        args.last_6_months, args.last_12_months, args.last_16_months
    ]):
        args.last_month = True

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
        today = date.today()
        first_day_of_this_month = today.replace(day=1)
        last_day_of_previous_month = first_day_of_this_month - timedelta(days=1)
        
        if is_data_available(service, args.site_url, last_day_of_previous_month):
            start_date = last_day_of_previous_month.replace(day=1).strftime('%Y-%m-%d')
            end_date = last_day_of_previous_month.strftime('%Y-%m-%d')
        else:
            first_day_of_previous_month = last_day_of_previous_month.replace(day=1)
            last_day_of_two_months_ago = first_day_of_previous_month - timedelta(days=1)
            start_date = last_day_of_two_months_ago.replace(day=1).strftime('%Y-%m-%d')
            end_date = last_day_of_two_months_ago.strftime('%Y-%m-%d')
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
    else: 
        start_date = args.start_date
        end_date = args.end_date

    site_url = args.site_url

    print(f"Analysing {site_url} from {start_date} to {end_date}")

    raw_data = get_performance_data(service, site_url, start_date, end_date)
    if not raw_data:
        print("No data found for the given site and date range.")
        return

    df = pd.DataFrame(raw_data)
    df[['query', 'page']] = pd.DataFrame(df['keys'].tolist(), index=df.index)
    df.drop(columns=['keys'], inplace=True)
    
    print(f"\nSuccessfully downloaded {len(df)} rows of data.")
    print("Processing for cannibalisation issues...")

    # --- Cannibalisation Logic ---
    query_summary = df.groupby('query').agg(
        page_count=('page', 'nunique'),
        total_clicks=('clicks', 'sum'),
        total_impressions=('impressions', 'sum')
    ).reset_index()

    cannibalised_queries = query_summary[query_summary['page_count'] > 1].copy()

    if cannibalised_queries.empty:
        print("No keyword cannibalisation issues found in the provided date range.")
        return

    print(f"Found {len(cannibalised_queries)} keywords with potential cannibalisation issues.")

    top_100_cannibalised = cannibalised_queries.sort_values(
        by='total_impressions', ascending=False
    ).head(100)

    print(f"Reporting on the top {len(top_100_cannibalised)} cannibalised keywords (by impressions).")

    top_queries_list = top_100_cannibalised['query'].tolist()
    report_df = df[df['query'].isin(top_queries_list)].copy()

    report_df['query'] = pd.Categorical(report_df['query'], categories=top_queries_list, ordered=True)
    report_df.sort_values(by=['query', 'clicks'], ascending=[True, False], inplace=True)

    # --- Report Generation and File Output ---
    if site_url.startswith('sc-domain:'):
        host_plain = site_url.replace('sc-domain:', '')
    else:
        host_plain = urlparse(site_url).netloc
    
    host_dir = host_plain.replace('www.', '')
    output_dir = os.path.join('output', host_dir)
    os.makedirs(output_dir, exist_ok=True)
    host_for_filename = host_dir.replace('.', '-')
    
    base_filename = f"keyword-cannibalisation-report-{host_for_filename}-{start_date}-to-{end_date}"
    html_output_path = os.path.join(output_dir, f"{base_filename}.html")

    print("Generating HTML report...")
    html_report = create_html_report(site_url, start_date, end_date, report_df, top_100_cannibalised)

    try:
        with open(html_output_path, 'w', encoding='utf-8') as f:
            f.write(html_report)
        print(f"\nSuccessfully created HTML report at: {html_output_path}")
    except IOError as e:
        print(f"Error writing HTML to file: {e}")

if __name__ == '__main__':
    main()
