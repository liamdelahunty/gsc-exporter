"""
Generates a summary report of Google Search Console performance data for various
date ranges, including an option to process all complete months over the last 16 months.

This script authenticates with the GSC API and can run for a single site or all
sites in an account. It retrieves clicks, impressions, CTR, average position, and
unique query/page counts. It uses pagination to get a more accurate count of
queries and pages.

The data is compiled into a CSV and a themed HTML report for each date range processed.
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
from functools import cmp_to_key

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


def get_all_sites(service):
    """Fetches a list of all sites in the user's GSC account."""
    sites = []
    try:
        site_list = service.sites().list().execute()
        if 'siteEntry' in site_list:
            sites = [s['siteUrl'] for s in site_list['siteEntry']]
    except HttpError as e:
        print(f"An HTTP error occurred while fetching sites: {e}")
    return sites

def _get_paginated_row_count(service, site_url, start_date, end_date, dimension):
    """
    Helper function to get a paginated row count for a single dimension.
    Returns the count and a boolean indicating if the count was truncated by a limit.
    """
    count = 0
    start_row = 0
    row_limit = 25000
    is_truncated = False
    
    print(f"      - Counting unique {dimension}s...")
    
    while True:
        try:
            request = {
                'startDate': start_date,
                'endDate': end_date,
                'dimensions': [dimension],
                'rowLimit': row_limit,
                'startRow': start_row
            }
            response = service.searchanalytics().query(siteUrl=site_url, body=request).execute()
            
            if 'rows' in response:
                num_rows = len(response['rows'])
                count += num_rows
                if num_rows < row_limit:
                    break
                start_row += row_limit
            else:
                break
        except HttpError as e:
            print(f"        - Warning: Could not continue fetching unique {dimension} count for {site_url}: {e}")
            is_truncated = True
            break
            
    if is_truncated:
        print(f"      - Found {count} unique {dimension}s (incomplete, hit API limit).")
    else:
        print(f"      - Found {count} unique {dimension}s.")
        
    return count, is_truncated

def get_monthly_performance_data(service, site_url, start_date, end_date):
    """
    Fetches performance data and unique query/page counts from GSC using pagination
    to get a more accurate count.
    """
    try:
        request_totals = {'startDate': start_date, 'endDate': end_date}
        response_totals = service.searchanalytics().query(siteUrl=site_url, body=request_totals).execute()
        if 'rows' not in response_totals:
            return None
        totals_data = response_totals['rows'][0]

        unique_queries, queries_truncated = _get_paginated_row_count(service, site_url, start_date, end_date, 'query')
        unique_pages, pages_truncated = _get_paginated_row_count(service, site_url, start_date, end_date, 'page')

        return {
            **totals_data, 
            'queries': unique_queries, 
            'pages': unique_pages,
            'queries_truncated': queries_truncated,
            'pages_truncated': pages_truncated
        }

    except HttpError as e:
        if e.resp.status == 403:
            print(f"Warning: Insufficient permission for {site_url}.")
            return "PERMISSION_DENIED"
        if e.resp.status in [400, 404]:
             print(f"    - No data available for {site_url} from {start_date} to {end_date}.")
        else:
            print(f"An HTTP error occurred for {site_url}: {e}")
    return None

def create_summary_report(df, report_title, month, template_path='resources/report-blank.html'):
    """Generates a summary HTML report from a DataFrame using a template."""
    if not os.path.exists(template_path):
        print(f"Error: Template file not found at {template_path}")
        return None

    with open(template_path, 'r', encoding='utf-8') as f:
        template_html = f.read()

    # --- Data Preparation ---
    report_df = df.copy()
    
    # Sort by property name, then by clicks
    report_df['sort_key'] = report_df['site_url'].apply(get_sort_key)
    report_df = report_df.sort_values(by=['sort_key', 'clicks'], ascending=[True, False]).drop(columns=['sort_key'])

    # Check for truncated data before formatting
    was_queries_truncated = report_df['queries_truncated'].any()
    was_pages_truncated = report_df['pages_truncated'].any()

    # Format numbers, adding a '*' if data was truncated
    report_df['# queries'] = report_df.apply(
        lambda row: f"{row['queries']:,.0f}{'*' if row['queries_truncated'] else ''}", axis=1
    )
    report_df['# pages'] = report_df.apply(
        lambda row: f"{row['pages']:,.0f}{'*' if row['pages_truncated'] else ''}", axis=1
    )
    
    # Standard formatting for other columns
    report_df['clicks'] = report_df['clicks'].apply(lambda x: f"{x:,.0f}")
    report_df['impressions'] = report_df['impressions'].apply(lambda x: f"{x:,.0f}")
    report_df['ctr'] = report_df['ctr'].apply(lambda x: f"{x:.2%}")
    report_df['position'] = report_df['position'].apply(lambda x: f"{x:,.2f}")

    # Rename and select final columns for the report table
    report_df = report_df.rename(columns={'site_url': 'property'})
    final_columns = ['property', 'clicks', 'impressions', 'ctr', 'position', '# queries', '# pages']
    report_df = report_df[final_columns]
    
    # --- HTML Generation ---

    # Convert DataFrame to HTML table
    table_html = report_df.to_html(classes="table table-striped table-hover", index=False, border=0)

    # Inject report title and month into the template
    html_output = template_html.replace('This Report Name', report_title)
    html_output = html_output.replace(
        '<span class="text-muted me-4">Domain name</span>',
        f'<span class="text-muted me-4">All Sites</span>'
    )
    html_output = html_output.replace(
        '<span class="text-muted me-4">Date-range</span>',
        f'<span class="text-muted me-4">{month}</span>'
    )
    
    # Update the "Resources" link in the footer
    html_output = html_output.replace(
        '<a href="index.html">Resources</a>',
        '<a href="../../resources/index.html">Resources</a>'
    )

    # Add custom CSS for table alignment
    custom_css = """<style>
        html {
            height: 100%;
        }
        body {
            display: flex;
            flex-direction: column;
            min-height: 100vh;
        }
        /* Custom CSS for table alignment */
        .table th, .table td {
            text-align: right;
            vertical-align: middle;
        }
        .table th:first-child, .table td:first-child { /* Align 'property' column to left */
            text-align: left;
        }
    </style>"""
    html_output = html_output.replace(
        """<style>
        html {
            height: 100%;
        }
        body {
            display: flex;
            flex-direction: column;
            min-height: 100vh;
        }
    </style>""",
        custom_css
    )

    # --- Content Injection ---

    # Construct truncation warning if necessary
    truncation_warning_html = ''
    if was_queries_truncated or was_pages_truncated:
        notes = []
        if was_queries_truncated:
            notes.append("query counts")
        if was_pages_truncated:
            notes.append("page counts")
        
        truncation_warning_html = f'''
        <div class="alert alert-warning" role="alert">
            <strong>*Note:</strong> The {' and '.join(notes)} for some properties may be incomplete as they exceeded the API's export limit.
        </div>
        '''

    # A robust way to replace the main content
    main_content_placeholder = """    <main class="container py-4 flex-grow-1">
        <h1>Hello</h1>
        <p>Lorem ipsum dolor sit amet, consectetur adipisicing elit, sed do eiusmod
            tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam,
            quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo
            consequat. Duis aute irure dolor in reprehenderit in voluptate velit esse
            cillum dolore eu fugiat nulla pariatur. Excepteur sint occaecat cupidatat non
        proident, sunt in culpa qui officia deserunt mollit anim id est laborum.</p>
        <div class="row">
            <div class="col">
                <p>Lorem ipsum dolor sit amet, consectetur adipisicing elit, sed do eiusmod
                    tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam,
                    quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo
                    consequat. Duis aute irure dolor in reprehenderit in voluptate velit esse
                    cillum dolore eu fugiat nulla pariatur. Excepteur sint occaecat cupidatat non
                proident, sunt in culpa qui officia deserunt mollit anim id est laborum.</p>
            </div>
            <div class="col">
                <p>Lorem ipsum dolor sit amet, consectetur adipisicing elit, sed do eiusmod
                    tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam,
                    quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo
                    consequat. Duis aute irure dolor in reprehenderit in voluptate velit esse
                    cillum dolore eu fugiat nulla pariatur. Excepteur sint occaecat cupidatat non
                proident, sunt in culpa qui officia deserunt mollit anim id est laborum.</p>
            </div>
        </div>
    </main>"""

    final_main_content = f"""    <main class="container py-4 flex-grow-1">
        {truncation_warning_html}
        <div class="table-responsive">
            {table_html}
        </div>
    </main>"""
    
    html_output = html_output.replace(main_content_placeholder, final_main_content)

    return html_output

def get_sort_key(site_url):
    """Creates a sort key for a site URL."""
    if site_url.startswith('sc-domain:'):
        root_domain = site_url.replace('sc-domain:', '')
        order = 0
        subdomain = ''
    else:
        netloc = urlparse(site_url).netloc
        parts = netloc.split('.')
        if len(parts) > 2 and parts[-2] in ['co', 'com', 'org', 'net', 'gov', 'edu'] and len(parts[-3]) > 2:
            root_domain = '.'.join(parts[-3:])
        elif len(parts) > 2:
            root_domain = '.'.join(parts[-2:])
        else:
            root_domain = netloc
        if netloc.startswith('www.'):
            order = 1
            subdomain = ''
        else:
            order = 2
            subdomain = netloc.split('.')[0]
    return (root_domain, order, subdomain)

def main():
    """Main function to run the analysis."""
    parser = argparse.ArgumentParser(
        description='Run a monthly summary report for GSC properties.',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument('site_url', nargs='?', default=None, help='Optional: The URL of the site to analyse. If not provided, runs for all sites.')
    parser.add_argument('--use-cache', action='store_true', help='Use a cached CSV file from a previous run if it exists.')
    
    date_group = parser.add_mutually_exclusive_group()
    date_group.add_argument('--all-months', action='store_true', help='Generate a separate report for each of the last 16 complete months.')
    date_group.add_argument('--start-date', help='Start date in YYYY-MM-DD format.')
    date_group.add_argument('--last-7-days', action='store_true', help='Set date range to the last 7 days.')
    date_group.add_argument('--last-28-days', action='store_true', help='Set date range to the last 28 days.')
    date_group.add_argument('--last-month', action='store_true', help='Set date range to the last calendar month (this is the default).')
    
    parser.add_argument('--end-date', help='End date in YYYY-MM-DD format. Used only with --start-date.')
    
    args = parser.parse_args()

    service = get_gsc_service()
    if not service:
        return

    # Determine the sites to process
    sites_to_process = []
    if args.site_url:
        sites_to_process = [args.site_url]
        latest_available_date = get_latest_available_gsc_date(service, args.site_url)
    else:
        sites_to_process = get_all_sites(service)
        if not sites_to_process:
            print("No sites found in your account.")
            return
        sites_to_process.sort(key=get_sort_key)
        # For all-months/all-sites report, we use today's date as a general reference
        # as querying for each site's latest available date would be inefficient here.
        latest_available_date = date.today() 
    
    date_ranges_to_process = []

    if args.all_months:
        # Loop through the last 16 complete months relative to the latest available date
        for i in range(1, 17):
            end_of_month = latest_available_date.replace(day=1) - relativedelta(months=i - 1) - timedelta(days=1)
            start_of_month = end_of_month.replace(day=1)
            date_ranges_to_process.append((start_of_month.strftime('%Y-%m-%d'), end_of_month.strftime('%Y-%m-%d')))
    elif args.start_date and args.end_date:
        date_ranges_to_process.append((args.start_date, args.end_date))
    elif args.last_7_days:
        start_date = (latest_available_date - timedelta(days=6)).strftime('%Y-%m-%d')
        end_date = latest_available_date.strftime('%Y-%m-%d')
        date_ranges_to_process.append((start_date, end_date))
    elif args.last_28_days:
        start_date = (latest_available_date - timedelta(days=27)).strftime('%Y-%m-%d')
        end_date = latest_available_date.strftime('%Y-%m-%d')
        date_ranges_to_process.append((start_date, end_date))
    else:  # Default to last complete month
        end_of_month = latest_available_date.replace(day=1) - timedelta(days=1)
        start_of_month = end_of_month.replace(day=1)
        date_ranges_to_process.append((start_of_month.strftime('%Y-%m-%d'), end_of_month.strftime('%Y-%m-%d')))

    for start_date, end_date in date_ranges_to_process:
        print(f"\n----- Processing date range: {start_date} to {end_date} -----")
        
        # --- Define output paths for the current date range ---
        if args.site_url:
            site_output_name = sites_to_process[0] # Use the single site's name for output dir
            if site_output_name.startswith('sc-domain:'):
                host_plain = site_output_name.replace('sc-domain:', '')
            else:
                host_plain = urlparse(site_output_name).netloc
            
            host_dir = host_plain.replace('www.', '')
            output_dir = os.path.join('output', host_dir)
            file_prefix = f"monthly-summary-report-{host_dir.replace('.', '-')}-{start_date}-to-{end_date}"
            report_title = f"Google Organic Monthly Summary for {site_output_name}"
        else:
            output_dir = os.path.join('output', 'account')
            file_prefix = f"monthly-summary-report-account-wide-{start_date}-to-{end_date}"
            report_title = "Google Organic Monthly Summary Report"

        os.makedirs(output_dir, exist_ok=True)
        csv_output_path = os.path.join(output_dir, f'{file_prefix}.csv')
        html_output_path = os.path.join(output_dir, f'{file_prefix}.html')

        df = None

        if args.use_cache and os.path.exists(csv_output_path):
            print(f"Found cached data at {csv_output_path}. Using it to generate report.")
            df = pd.read_csv(csv_output_path)
            # Ensure 'queries_truncated' and 'pages_truncated' are boolean if loading from cache
            if 'queries_truncated' in df.columns:
                df['queries_truncated'] = df['queries_truncated'].astype(bool)
            if 'pages_truncated' in df.columns:
                df['pages_truncated'] = df['pages_truncated'].astype(bool)
        else:
            all_data = []
            for site_url in sites_to_process:
                print(f"\nFetching data for site: {site_url}")
                data = get_monthly_performance_data(service, site_url, start_date, end_date)
                if data == "PERMISSION_DENIED":
                    continue # Skip to the next site
                elif data:
                    all_data.append({'site_url': site_url, 'month': start_date[:7], **data})
            
            if not all_data:
                print(f"No performance data found for the period {start_date} to {end_date}.")
                continue

            df = pd.DataFrame(all_data)
            column_order = ['site_url', 'month', 'clicks', 'impressions', 'ctr', 'position', 'queries', 'pages', 'queries_truncated', 'pages_truncated']
            df = df[column_order]

            try:
                df.to_csv(csv_output_path, index=False)
                print(f"\nSuccessfully exported CSV to {csv_output_path}")
                print(f"Hint: To recreate this report from the saved data, use the --use-cache flag.")
            except PermissionError:
                print(f"\nError: Permission denied when writing to the output directory.")
                continue

        # Generate HTML report
        try:
            report_date_str = f"{start_date} to {end_date}"
            html_output = create_summary_report(df, report_title, report_date_str)
            
            if html_output:
                with open(html_output_path, 'w', encoding='utf-8') as f:
                    f.write(html_output)
                print(f"Successfully created HTML report at {html_output_path}")
        except PermissionError:
            print(f"\nError: Permission denied when writing to the output directory.")

if __name__ == '__main__':
    main()
