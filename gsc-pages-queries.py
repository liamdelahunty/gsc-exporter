"""
Exports a report of queries and their corresponding pages, and pages and their
corresponding queries from a Google Search Console property.

This script authenticates with the Google Search Console API, fetches data for a
specified site with 'query' and 'page' dimensions, and then generates an HTML
report showing the relationships between them.

Usage:
    python gsc-pages-queries.py <site_url> [--start-date <start_date>] [--end-date <end_date>] 
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
import re
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



def get_pages_queries_data(service, site_url, start_date, end_date):
    """Fetches pages and queries data from GSC for a given date range."""
    all_data = []
    start_row = 0
    row_limit = 5000  # A safe limit, can be up to 25000
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

def create_html_report(data_df, site_url, start_date, end_date, report_limit, sub_table_limit, command, brand_terms):
    """Generates an HTML report for pages and queries."""
    
    # --- Report Details Alert ---
    brand_terms_str = ", ".join(sorted(list(brand_terms))) if brand_terms else "None"
    info_alert_html = f"""
        <div class="alert alert-secondary">
            <strong>Report Details:</strong>
            <ul>
                <li><strong>Command:</strong> <code>{html.escape(' '.join(command.split()))}</code></li>
                <li><strong>Brand Terms Used:</strong> {html.escape(brand_terms_str)}</li>
            </ul>
        </div>
    """

    # --- Truncation Alert ---
    query_count = data_df['query'].nunique()
    page_count = data_df['page'].nunique()
    is_truncated = query_count > report_limit or page_count > report_limit

    truncation_alert_html = ""
    if is_truncated:
        truncation_alert_html = f"""
        <div class="alert alert-info">
            <strong>Report Truncated:</strong> To improve performance, this HTML report has been shortened.
            <ul>
                <li>The report is limited to the top <strong>{report_limit}</strong> primary items (queries/pages) by clicks.</li>
                <li>Each table within an item is limited to its top <strong>{sub_table_limit}</strong> rows.</li>
            </ul>
            The full, unfiltered data is available in the accompanying CSV file. You can adjust these limits using the <code>--report-limit</code> and <code>--sub-table-limit</code> flags.
        </div>
        """

    # --- HTML Structure ---
    # Prepare data based on whether brand classification exists
    has_brand_classification = 'brand_type' in data_df.columns

    if has_brand_classification:
        non_brand_df = data_df[data_df['brand_type'] == 'Non-Brand'].sort_values(by=['query', 'clicks'], ascending=[True, False]).reset_index(drop=True)
        brand_df = data_df[data_df['brand_type'] == 'Brand'].sort_values(by=['query', 'clicks'], ascending=[True, False]).reset_index(drop=True)
        all_queries_df = data_df.sort_values(by=['query', 'clicks'], ascending=[True, False]).reset_index(drop=True)
        
        # The 'Pages to Queries' data does not get brand-classified in this version
        page_grouped = data_df.sort_values(by=['page', 'clicks'], ascending=[True, False]).reset_index(drop=True)

        query_tabs = """
            <li class="nav-item" role="presentation">
                <button class="nav-link active" id="non-brand-tab" data-bs-toggle="tab" data-bs-target="#non-brand-queries" type="button" role="tab">Non-Brand Queries</button>
            </li>
            <li class="nav-item" role="presentation">
                <button class="nav-link" id="brand-tab" data-bs-toggle="tab" data-bs-target="#brand-queries" type="button" role="tab">Brand Queries</button>
            </li>
            <li class="nav-item" role="presentation">
                <button class="nav-link" id="all-queries-tab" data-bs-toggle="tab" data-bs-target="#all-queries" type="button" role="tab">All Queries</button>
            </li>
        """
        query_tab_content = f"""
            <div class="tab-pane fade show active" id="non-brand-queries" role="tabpanel">
                {generate_accordion_html(non_brand_df, 'query', 'page', report_limit, sub_table_limit)}
            </div>
            <div class="tab-pane fade" id="brand-queries" role="tabpanel">
                {generate_accordion_html(brand_df, 'query', 'page', report_limit, sub_table_limit)}
            </div>
            <div class="tab-pane fade" id="all-queries" role="tabpanel">
                {generate_accordion_html(all_queries_df, 'query', 'page', report_limit, sub_table_limit)}
            </div>
        """
    else:
        query_grouped = data_df.sort_values(by=['query', 'clicks'], ascending=[True, False]).reset_index(drop=True)
        page_grouped = data_df.sort_values(by=['page', 'clicks'], ascending=[True, False]).reset_index(drop=True)
        query_tabs = """
            <li class="nav-item" role="presentation">
                <button class="nav-link active" id="queries-tab" data-bs-toggle="tab" data-bs-target="#queries" type="button" role="tab">Queries to Pages</button>
            </li>
        """
        query_tab_content = f"""
            <div class="tab-pane fade show active" id="queries" role="tabpanel">
                {generate_accordion_html(query_grouped, 'query', 'page', report_limit, sub_table_limit)}
            </div>
        """

    # --- Final HTML Assembly ---
    html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Google Organic Pages & Queries Report for {site_url}</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"></script>
    <style>
        body {{ padding: 2rem; }}
        .table-responsive {{ max-height: 500px; }}
        .accordion-button:not(.collapsed) {{ background-color: #e7f1ff; }}
        .table th:not(:first-child), .table td:not(:first-child) {{ text-align: right; }}
        .table th:first-child, .table td:first-child {{ text-align: left; }}
        .badge-bg-primary {{ background-color: #0076AF;  }}
        .badge-bg-secondary {{ background-color: #712784; }}
    </style>
</head>
<body>
    <div class="container-fluid">
        <h1 class="mb-3">Google Organic Pages & Queries Report</h1>
        <h2>{site_url}</h2>
        <p class="text-muted">{start_date} to {end_date}</p>

        {info_alert_html}
        {truncation_alert_html}

        <ul class="nav nav-tabs" id="myTab" role="tablist">
            {query_tabs}
            <li class="nav-item" role="presentation">
                <button class="nav-link" id="pages-tab" data-bs-toggle="tab" data-bs-target="#pages" type="button" role="tab">Pages to Queries</button>
            </li>
        </ul>

        <div class="tab-content" id="myTabContent">
            {query_tab_content}
            <div class="tab-pane fade" id="pages" role="tabpanel">
                {generate_accordion_html(page_grouped, 'page', 'query', report_limit, sub_table_limit)}
            </div>
        </div>
    </div>
</body>
</html>
    """
    return html_content

def generate_accordion_html(grouped_df, primary_dim, secondary_dim, report_limit, sub_table_limit):
    """Generates Bootstrap accordion HTML for the grouped data."""
    accordion_id = f"accordion-{primary_dim}"
    html = f'<div class="accordion mt-3" id="{accordion_id}">'

    # Get total metrics for the primary dimension
    primary_totals = grouped_df.groupby(primary_dim).agg(
        total_clicks=('clicks', 'sum'),
        total_impressions=('impressions', 'sum')
    ).sort_values(by='total_clicks', ascending=False).reset_index()

    # Limit the number of primary items based on the report_limit
    if len(primary_totals) > report_limit:
        print(f"Report will be truncated to the top {report_limit} {primary_dim}s based on clicks.")
    
    limited_primary_totals = primary_totals.head(report_limit)

    item_count = 0
    for index, row in limited_primary_totals.iterrows():
        primary_val = row[primary_dim]
        total_clicks = row['total_clicks']
        total_impressions = row['total_impressions']
        
        # Unique ID for accordion items
        collapse_id = f"collapse-{primary_dim}-{item_count}"
        header_id = f"header-{primary_dim}-{item_count}"
        
        # Get the subgroup for the current primary dimension value
        sub_group_full = grouped_df[grouped_df[primary_dim] == primary_val]
        sub_group = sub_group_full.head(sub_table_limit)
        
        # Format the sub-table
        formatters = {
            'clicks': lambda x: f'{x:,d}',
            'impressions': lambda x: f'{x:,d}'
        }
        sub_group_html = sub_group[[secondary_dim, 'clicks', 'impressions', 'ctr', 'position']].to_html(
            classes="table table-sm table-striped",
            index=False,
            border=0,
            formatters=formatters
        )

        # Add a note if the sub-table is truncated
        if len(sub_group_full) > len(sub_group):
            sub_group_html += f"<p class='text-muted mt-2'>Showing top {sub_table_limit} of {len(sub_group_full):,} {secondary_dim}s, sorted by clicks.</p>"


        html += f"""
        <div class="accordion-item">
            <h2 class="accordion-header" id="{header_id}">
                <button class="accordion-button collapsed" type="button" data-bs-toggle="collapse" data-bs-target="#{collapse_id}">
                    <div class="d-flex w-100 align-items-center">
                        <strong>{primary_val}</strong>&nbsp;
                        <div class="ms-auto">
                            <span class="badge badge-bg-primary p-3 me-3">Clicks: {total_clicks:,d}</span>
                            <span class="badge badge-bg-secondary p-3 me-3">Impressions: {total_impressions:,d}</span>
                        </div>
                    </div>
                </button>
            </h2>
            <div id="{collapse_id}" class="accordion-collapse collapse" data-bs-parent="#{accordion_id}">
                <div class="accordion-body">
                    <div class="table-responsive">
                        {sub_group_html}
                    </div>
                </div>
            </div>
        </div>
        """
        item_count += 1

    html += '</div>'
    return html

def get_root_domain(site_url):
    """Extracts a clean root domain from a GSC site URL."""
    if site_url.startswith('sc-domain:'):
        return site_url.replace('sc-domain:', '')
    
    hostname = urlparse(site_url).hostname
    if not hostname:
        return None
    
    # Use a regex to find the most likely root domain, handling .co.uk, .com, etc.
    match = re.search(r'([\w-]+\.(?:co\.uk|com\.au|co\.nz|co\.za|co\.il|co\.jp|com|org|net|biz|info))\s*$', hostname.lower())
    if match:
        return match.group(1)
    
    # Fallback for other TLDs
    parts = hostname.split('.')
    if len(parts) > 1:
        return '.'.join(parts[-2:])
    return hostname

def get_brand_terms(site_url):
    """
    Automatically extracts a set of likely brand terms from a site URL.

    Args:
        site_url (str): The URL of the site.

    Returns:
        set: A set of guessed brand terms.
    """
    if not site_url or site_url == "Loaded from CSV":
        return set()
        
    hostname = urlparse(site_url).hostname
    if not hostname:
        return set()

    # A list of common public suffixes to remove.
    # This is a simplified approach. A more robust solution might use a library
    # like tldextract, but this avoids adding a new dependency.
    suffixes_to_remove = ['.com', '.co.uk', '.org', '.net', '.gov', '.edu', '.io', '.co']
    
    # Remove 'www.' prefix
    if hostname.startswith('www.'):
        hostname = hostname[4:]
        
    # Iteratively remove suffixes
    for suffix in sorted(suffixes_to_remove, key=len, reverse=True):
        if hostname.endswith(suffix):
            hostname = hostname[:-len(suffix)]
            break # Stop after the first, longest match
            
    if not hostname:
        return set()

    # Generate variations
    terms = {hostname}
    if '-' in hostname:
        terms.add(hostname.replace('-', ' '))
        terms.add(hostname.replace('-', ''))
        
    print(f"Auto-detected brand terms: {terms}")
    return terms

def main():
    """Main function to run the script."""
    parser = argparse.ArgumentParser(
        description='Export Google Search Console pages and queries. Generates an HTML report from either live GSC data or a pre-existing CSV file.',
        epilog='Example Usage:\n'
               '  To download data: python gsc-pages-queries.py https://www.example.com --last-month\n'
               '  To use cached data: python gsc-pages-queries.py https://www.example.com --last-month --use-cache\n'
               '  To generate from a csv: python gsc-pages-queries.py --csv ./output/example-com/report.csv --report-limit 50',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    # --- Arguments ---
    # Positional site_url (optional, if --csv is provided)
    parser.add_argument('site_url', nargs='?', help='The URL of the site to export data for. Required unless --csv is used.')
    
    # Data source selection (mutually exclusive)
    source_group = parser.add_mutually_exclusive_group()
    source_group.add_argument('--csv', help='Path to a CSV file to generate the report from, skipping the GSC API download.')
    
    # Date range options
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
    
    # Other arguments
    parser.add_argument('--end-date', help='End date in YYYY-MM-DD format. Used only with --start-date.')
    parser.add_argument('--use-cache', action='store_true', help='Use a cached CSV file from a previous run if it exists.')
    parser.add_argument('--report-limit', type=int, default=250, help='Maximum number of primary items (queries/pages) to include in the HTML report. Default is 250.')
    parser.add_argument('--sub-table-limit', type=int, default=100, help='Maximum number of sub-items (pages/queries) to display in each section of the HTML report. Default is 100.')
    parser.add_argument('--no-brand-detection', action='store_true', help='Disable the automatic brand term detection.')
    parser.add_argument('--brand-terms', nargs='+', help='A list of additional brand terms to include in the analysis.')
    parser.add_argument('--brand-terms-file', help='Path to a text file containing brand terms, one per line.')
    parser.add_argument('--top-queries', type=int, help='Generate a CSV with only the top N queries by clicks.')
    parser.add_argument('--split-brand', action='store_true', help='When used with --top-queries, generates separate CSVs for brand and non-brand top queries.')
    
    args = parser.parse_args()

    # Custom validation logic
    if not args.site_url and not args.csv:
        parser.error('site_url is required unless --csv is provided.')
    
    if args.use_cache and not args.site_url:
        parser.error('site_url is required when using --use-cache to identify the site for caching.')

    # --- Main Logic ---
    df = None
    
    # --- Case 1: Generate report from a local CSV file ---
    if args.csv:
        if not os.path.exists(args.csv):
            print(f"Error: CSV file not found at '{args.csv}'")
            return
        print(f"Generating report from CSV file: {args.csv}")
        df = pd.read_csv(args.csv)
        # Determine the site_url for brand detection and HTML title purposes
        processing_site_url = args.site_url # Prefer explicit site_url if provided
        
        # Use placeholders for metadata as it cannot be inferred from the CSV alone
        start_date = "N/A"
        end_date = "N/A"
        csv_inferred_site_url = "Loaded from CSV"

        # Try to parse info from filename for a better title and potential site_url
        try:
            filename = os.path.basename(args.csv)
            # This regex tries to capture the site from filenames like 'gsc-pages-queries-hr-inform-co-uk-DATE-to-DATE.csv'
            match = re.search(r'gsc-pages-queries-([\w-]+(?:-\w{2})?)(?:-full)?-\d{4}-\d{2}-\d{2}-to-\d{4}-\d{2}-\d{2}\.csv', filename)
            if match:
                # Add scheme for proper parsing by urlparse
                csv_inferred_site_url = 'https://' + match.group(1).replace('-', '.')
            else: # Fallback for simpler filenames
                parts = filename.replace('gsc-pages-queries-', '').replace('.csv', '').split('-to-')
                if len(parts) > 1:
                    remaining_parts = parts[0].split('-')
                    # Add scheme for proper parsing by urlparse
                    csv_inferred_site_url = 'https://' + '-'.join(remaining_parts[:-1]).replace('-', '.')
            
            # If a site_url wasn't explicitly provided, use the one inferred from CSV
            if not processing_site_url:
                processing_site_url = csv_inferred_site_url

            # Also try to get dates from filename for HTML report if not explicitly set
            date_parts = re.search(r'(\d{4}-\d{2}-\d{2})-to-(\d{4}-\d{2}-\d{2})\.csv', filename)
            if date_parts:
                start_date = date_parts.group(1)
                end_date = date_parts.group(2)

        except Exception:
            pass # Ignore parsing errors, placeholders will be used

        site_url = processing_site_url # This is what will be used in the HTML title
        html_output_path = args.csv.replace('.csv', '.html')
    # --- Case 2: Download data or use cache ---
    else:
        # Add a correction for common typos in the site URL
        if 'wwww.' in args.site_url:
            args.site_url = args.site_url.replace('wwww.', 'www.')
        
        # Authenticate GSC service once
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

        # Determine the date range based on the provided flags
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
            first_day_of_current_month = latest_available_date.replace(day=1)
            last_day_of_previous_month = first_day_of_current_month - timedelta(days=1)
            start_date = last_day_of_previous_month.replace(day=1).strftime('%Y-%m-%d')
            end_date = last_day_of_previous_month.strftime('%Y-%m-%d')
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
        else: # Custom date range
            start_date = args.start_date
            end_date = args.end_date

        site_url = args.site_url

        # --- Output File Naming ---
        if site_url.startswith('sc-domain:'):
            host_plain = site_url.replace('sc-domain:', '')
        else:
            host_plain = urlparse(site_url).netloc
        
        host_dir = host_plain.replace('www.', '')
        output_dir = os.path.join('output', host_dir)
        os.makedirs(output_dir, exist_ok=True)
        host_for_filename = host_dir.replace('.', '-')
        
        base_filename = f"gsc-pages-queries-{host_for_filename}-{start_date}-to-{end_date}"
        csv_output_path = os.path.join(output_dir, f"{base_filename}.csv")
        html_output_path = os.path.join(output_dir, f"{base_filename}.html")

        # Check for cached file if --use-cache is specified
        if args.use_cache and os.path.exists(csv_output_path):
            print(f"Found cached data at {csv_output_path}. Using it to generate report.")
            df = pd.read_csv(csv_output_path)
        else:
            # service is already authenticated above
            # if not service:
            #     return
            
            raw_data = get_pages_queries_data(service, site_url, start_date, end_date)
            if not raw_data:
                print("No data found for the given site and date range.")
                return

            df = pd.DataFrame(raw_data)
            df[['query', 'page']] = pd.DataFrame(df['keys'].tolist(), index=df.index)
            df.drop(columns=['keys'], inplace=True)
            
            # --- Save CSV Report ---
            try:
                # Reorder columns for CSV output
                csv_column_order = ['page', 'query', 'clicks', 'impressions', 'ctr', 'position']
                df_csv = df[csv_column_order]
                df_csv.to_csv(csv_output_path, index=False, encoding='utf-8')
                print(f"\nSuccessfully created CSV report at {csv_output_path}")
            except IOError as e:
                print(f"Error writing CSV to file: {e}")

    # --- Generate and Save HTML Report ---
    if df is not None:
        brand_terms = set()
        # Priority 1: --brand-terms-file flag
        if args.brand_terms_file:
            if os.path.exists(args.brand_terms_file):
                with open(args.brand_terms_file, 'r') as f:
                    file_terms = [line.strip().lower() for line in f if line.strip()]
                    brand_terms.update(file_terms)
                print(f"Loaded {len(file_terms)} brand terms from {args.brand_terms_file}")
            else:
                print(f"Warning: Brand terms file not found at '{args.brand_terms_file}'.")
        
        # Priority 2: Automatic file in /config (if no explicit file and brand detection is on)
        elif not args.no_brand_detection:
            hostname_for_brand_file = urlparse(args.site_url or processing_site_url).hostname
            if hostname_for_brand_file:
                # This logic determines the base name for the brand terms file e.g., 'hr.inform.co.uk' -> 'hr-inform'
                key = hostname_for_brand_file
                if key.startswith('www.'):
                    key = key[4:]
                
                suffixes_to_remove = ['.com', '.co.uk', '.org', '.net', '.gov', '.edu', '.io', '.co']
                for suffix in sorted(suffixes_to_remove, key=len, reverse=True):
                    if key.endswith(suffix):
                        key = key[:-len(suffix)]
                        break
                
                brand_file_name = key.replace('.', '-')
                config_file_path = os.path.join('config', f'brand-terms-{brand_file_name}.txt')

                if os.path.exists(config_file_path):
                    with open(config_file_path, 'r') as f:
                        config_terms = [line.strip().lower() for line in f if line.strip()]
                        brand_terms.update(config_terms)
                    print(f"Loaded {len(config_terms)} brand terms from {config_file_path} (auto-detected).")
        
        # Priority 3: Auto-detection from URL (if brand detection is on and no other terms loaded yet)
        if not args.no_brand_detection and not brand_terms:
            brand_terms.update(get_brand_terms(args.site_url or processing_site_url))

        # Priority 4: --brand-terms from command line (always adds to the set)
        if args.brand_terms:
            brand_terms.update(term.lower() for term in args.brand_terms)
        
        # Classify queries if we have brand terms
        if brand_terms:
            print(f"Classifying queries with brand terms: {brand_terms}")
            # Create a regex pattern to find any of the brand terms as whole words
            # Use (?:...) for non-capturing group and re.escape for safety
            pattern = r'\b(?:' + '|'.join(re.escape(term) for term in brand_terms) + r')\b'
            df['brand_type'] = df['query'].str.contains(pattern, case=False, regex=True).map({True: 'Brand', False: 'Non-Brand'})


        # --- Handle top_queries and split_brand CSV generation ---
        if args.top_queries:
            if not args.csv:
                print("Warning: --top-queries is best used with --csv to operate on existing data. This run will filter the freshly downloaded data.")

            # Calculate top queries based on total clicks
            query_clicks = df.groupby('query')['clicks'].sum().sort_values(ascending=False)
            
            if args.split_brand:
                if 'brand_type' not in df.columns:
                    print("Error: --split-brand requires brand classification, but it's disabled or no terms were found. Skipping CSV generation.")
                else:
                    # Top N Brand Queries
                    brand_queries = df[df['brand_type'] == 'Brand']['query'].unique()
                    top_brand_queries = query_clicks[query_clicks.index.isin(brand_queries)].head(args.top_queries).index
                    brand_df = df[df['query'].isin(top_brand_queries)]
                    
                    # Top N Non-Brand Queries
                    non_brand_queries = df[df['brand_type'] == 'Non-Brand']['query'].unique()
                    top_non_brand_queries = query_clicks[query_clicks.index.isin(non_brand_queries)].head(args.top_queries).index
                    non_brand_df = df[df['query'].isin(top_non_brand_queries)]

                    # Save the split files
                    base_path = html_output_path.replace('.html', '')
                    brand_csv_path = f"{base_path}-top-{args.top_queries}-brand-queries.csv"
                    non_brand_csv_path = f"{base_path}-top-{args.top_queries}-non-brand-queries.csv"
                    
                    brand_df.to_csv(brand_csv_path, index=False, encoding='utf-8')
                    print(f"Successfully created top brand queries CSV at {brand_csv_path}")
                    
                    non_brand_df.to_csv(non_brand_csv_path, index=False, encoding='utf-8')
                    print(f"Successfully created top non-brand queries CSV at {non_brand_csv_path}")
            else:
                # Top N queries overall
                top_queries_list = query_clicks.head(args.top_queries).index
                top_df = df[df['query'].isin(top_queries_list)]
                
                # Save the combined file
                base_path = html_output_path.replace('.html', '')
                top_csv_path = f"{base_path}-top-{args.top_queries}-queries.csv"
                top_df.to_csv(top_csv_path, index=False, encoding='utf-8')
                print(f"Successfully created top queries CSV at {top_csv_path}")


        # Format for HTML report
        html_df = df.copy()
        # Ensure required columns exist before formatting
        if 'ctr' in html_df.columns:
            html_df['ctr'] = html_df['ctr'].apply(lambda x: f"{x:.2%}")
        if 'position' in html_df.columns:
            html_df['position'] = html_df['position'].apply(lambda x: f"{x:.2f}")

        html_report = create_html_report(
            data_df=html_df, 
            site_url=site_url, 
            start_date=start_date, 
            end_date=end_date, 
            report_limit=args.report_limit, 
            sub_table_limit=args.sub_table_limit,
            command=' '.join(sys.argv),
            brand_terms=brand_terms
        )
        try:
            with open(html_output_path, 'w', encoding='utf-8') as f:
                f.write(html_report)
            print(f"Successfully created HTML report at {html_output_path}")
        except IOError as e:
            print(f"Error writing HTML to file: {e}")
    else:
        print("No data available to generate a report.")



if __name__ == '__main__':
    main()
