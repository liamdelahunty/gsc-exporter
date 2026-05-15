"""
Exports a report of queries and their corresponding pages from a Google 
Search Console property.

This script authenticates with the GSC API, fetches performance data, and then
generates both a CSV and an interactive HTML report.

By default, to improve performance and readability, the script processes a
limited subset of the data for both the CSV and HTML outputs, focusing on
the top 250 pages/queries. These limits can be adjusted using the
--report-limit and --sub-table-limit flags.

Usage:
    python gsc-pages-queries.py <site_url> [--start-date <start_date>] [--end-date <end_date>]
"""
import os
import pandas as pd
import time
import socket
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

# Set global timeout for API requests
socket.setdefaulttimeout(300)

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
            print(f"Could not load credentials: {e}")
            creds = None

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except exceptions.RefreshError:
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
                print(f"An HTTP error occurred: {e}")
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
            
    return current_date 



def get_pages_queries_data(service, site_url, start_date, end_date):
    """Fetches pages and queries data from GSC with pagination and retries."""
    all_data = []
    start_row = 0
    row_limit = 10000 # Reduced for stability
    
    print(f"Fetching data for {site_url} from {start_date} to {end_date}...")
    
    while True:
        success = False
        for attempt in range(3):
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
                    print(f"  - Retrieved {len(rows)} rows... (Total: {len(all_data)})")
                    if len(rows) < row_limit:
                        break
                    start_row += row_limit
                else:
                    break
                success = True
                break
            except (socket.timeout, TimeoutError):
                print(f"  - Timeout on attempt {attempt + 1}, retrying...")
                time.sleep(5 * (attempt + 1))
            except HttpError as e:
                print(f"  - An HTTP error occurred: {e}")
                break
        
        if not success and attempt == 2:
            print(f"  - Failed to fetch data after 3 attempts.")
            break
            
        if 'rows' not in response or len(response['rows']) < row_limit:
            break
            
    return all_data

def create_html_report(data_df, site_url, start_date, end_date, report_limit, sub_table_limit, command, brand_terms):
    """Generates an HTML report for pages and queries."""
    
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

    has_brand_classification = 'brand_type' in data_df.columns

    if has_brand_classification:
        non_brand_df = data_df[data_df['brand_type'] == 'Non-Brand'].sort_values(by=['query', 'clicks'], ascending=[True, False]).reset_index(drop=True)
        brand_df = data_df[data_df['brand_type'] == 'Brand'].sort_values(by=['query', 'clicks'], ascending=[True, False]).reset_index(drop=True)
        all_queries_df = data_df.sort_values(by=['query', 'clicks'], ascending=[True, False]).reset_index(drop=True)
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

    primary_totals = grouped_df.groupby(primary_dim).agg(
        total_clicks=('clicks', 'sum'),
        total_impressions=('impressions', 'sum')
    ).sort_values(by='total_clicks', ascending=False).reset_index()

    if len(primary_totals) > report_limit:
        print(f"Report will be truncated to the top {report_limit} {primary_dim}s based on clicks.")
    
    limited_primary_totals = primary_totals.head(report_limit)

    item_count = 0
    for index, row in limited_primary_totals.iterrows():
        primary_val = row[primary_dim]
        total_clicks = row['total_clicks']
        total_impressions = row['total_impressions']
        
        collapse_id = f"collapse-{primary_dim}-{item_count}"
        header_id = f"header-{primary_dim}-{item_count}"
        
        sub_group_full = grouped_df[grouped_df[primary_dim] == primary_val]
        sub_group = sub_group_full.head(sub_table_limit)
        
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
    
    match = re.search(r'([\w-]+\.(?:co\.uk|com\.au|co\.nz|co\.za|co\.il|co\.jp|com|org|net|biz|info))\s*$', hostname.lower())
    if match:
        return match.group(1)
    
    parts = hostname.split('.')
    if len(parts) > 1:
        return '.'.join(parts[-2:])
    return hostname

def get_brand_terms(site_url):
    """Automatically extracts a set of likely brand terms from a site URL."""
    if not site_url or site_url == "Loaded from CSV":
        return set()
        
    hostname = urlparse(site_url).hostname
    if not hostname:
        return set()

    suffixes_to_remove = ['.com', '.co.uk', '.org', '.net', '.gov', '.edu', '.io', '.co']
    
    if hostname.startswith('www.'):
        hostname = hostname[4:]
        
    for suffix in sorted(suffixes_to_remove, key=len, reverse=True):
        if hostname.endswith(suffix):
            hostname = hostname[:-len(suffix)]
            break
            
    if not hostname:
        return set()

    terms = {hostname}
    if '-' in hostname:
        terms.add(hostname.replace('-', ' '))
        terms.add(hostname.replace('-', ''))
        
    print(f"Auto-detected brand terms: {terms}")
    return terms

def main():
    """Main function to run the script."""
    parser = argparse.ArgumentParser(
        description='Export Google Search Console pages and queries.',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument('site_url', nargs='?', help='The URL of the site to export data for.')
    parser.add_argument('--csv', help='Path to a CSV file to generate the report from.')
    
    date_group = parser.add_mutually_exclusive_group()
    date_group.add_argument('--start-date', help='Start date in YYYY-MM-DD format.')
    date_group.add_argument('--last-7-days', action='store_true', help='Set date range to the last 7 days.')
    date_group.add_argument('--last-28-days', action='store_true', help='Set date range to the last 28 days.')
    date_group.add_argument('--last-month', action='store_true', help='Set date range to the last calendar month.')
    date_group.add_argument('--last-12-months', action='store_true', help='Set date range to the last 12 months.')
    date_group.add_argument('--last-16-months', action='store_true', help='Set date range to the last 16 months.')
    
    parser.add_argument('--end-date', help='End date in YYYY-MM-DD format.')
    parser.add_argument('--use-cache', action='store_true', help='Use a cached CSV file from a previous run if it exists.')
    parser.add_argument('--report-limit', type=int, default=250, help='Maximum primary items in HTML report.')
    parser.add_argument('--sub-table-limit', type=int, default=100, help='Maximum sub-items in HTML report.')
    parser.add_argument('--no-brand-detection', action='store_true', help='Disable brand detection.')
    parser.add_argument('--brand-terms', nargs='+', help='Additional brand terms.')
    
    args = parser.parse_args()

    if not args.site_url and not args.csv:
        parser.error('site_url is required unless --csv is provided.')
    
    df = None
    
    if args.csv:
        if not os.path.exists(args.csv):
            print(f"Error: CSV file not found at '{args.csv}'")
            return
        df = pd.read_csv(args.csv)
        processing_site_url = args.site_url or "Loaded from CSV"
        start_date = "N/A"
        end_date = "N/A"
        site_url = processing_site_url
        html_output_path = args.csv.replace('.csv', '.html')
    else:
        service = get_gsc_service()
        if not service: return

        latest_available_date = get_latest_available_gsc_date(service, args.site_url)

        if not any([args.start_date, args.last_7_days, args.last_28_days, args.last_month, args.last_12_months, args.last_16_months]):
            args.last_month = True

        if args.start_date and args.end_date:
            start_date, end_date = args.start_date, args.end_date
        elif args.last_7_days:
            start_date = (latest_available_date - timedelta(days=6)).strftime('%Y-%m-%d')
            end_date = latest_available_date.strftime('%Y-%m-%d')
        elif args.last_28_days:
            start_date = (latest_available_date - timedelta(days=27)).strftime('%Y-%m-%d')
            end_date = latest_available_date.strftime('%Y-%m-%d')
        elif args.last_month:
            end_month = latest_available_date.replace(day=1) - timedelta(days=1)
            start_date, end_date = end_month.replace(day=1).strftime('%Y-%m-%d'), end_month.strftime('%Y-%m-%d')
        elif args.last_16_months:
            start_date = (latest_available_date - relativedelta(months=16) + timedelta(days=1)).strftime('%Y-%m-%d')
            end_date = latest_available_date.strftime('%Y-%m-%d')
        else:
            start_date, end_date = args.start_date, args.end_date

        site_url = args.site_url
        host_plain = site_url.replace('sc-domain:', '') if site_url.startswith('sc-domain:') else urlparse(site_url).netloc
        host_dir = host_plain.replace('www.', '')
        output_dir = os.path.join('output', host_dir)
        os.makedirs(output_dir, exist_ok=True)
        host_for_filename = host_dir.replace('.', '-')
        
        base_filename = f"gsc-pages-queries-{host_for_filename}-{start_date}-to-{end_date}"
        csv_output_path = os.path.join(output_dir, f"{base_filename}.csv")
        html_output_path = os.path.join(output_dir, f"{base_filename}.html")

        if args.use_cache and os.path.exists(csv_output_path):
            print(f"Found cached data at {csv_output_path}. Using it.")
            df = pd.read_csv(csv_output_path)
        else:
            raw_data = get_pages_queries_data(service, site_url, start_date, end_date)
            if not raw_data:
                print("No data found.")
                return

            df = pd.DataFrame(raw_data)
            df[['query', 'page']] = pd.DataFrame(df['keys'].tolist(), index=df.index)
            df.drop(columns=['keys'], inplace=True)

            print(f"\nOriginal dataframe has {len(df)} rows. Filtering for report...")
            df.sort_values(by='clicks', ascending=False, inplace=True)
            top_pages = df.groupby('page')['clicks'].sum().nlargest(args.report_limit).index
            top_queries = df.groupby('query')['clicks'].sum().nlargest(args.report_limit).index
            df_from_pages = df[df['page'].isin(top_pages)].groupby('page').head(args.sub_table_limit)
            df_from_queries = df[df['query'].isin(top_queries)].groupby('query').head(args.sub_table_limit)
            df = pd.concat([df_from_pages, df_from_queries]).drop_duplicates().reset_index(drop=True)
            
            try:
                df[['page', 'query', 'clicks', 'impressions', 'ctr', 'position']].to_csv(csv_output_path, index=False)
                print(f"\nSuccessfully created CSV report at {csv_output_path}")
            except IOError as e:
                print(f"Error writing CSV: {e}")

    if df is not None:
        brand_terms = set()
        if not args.no_brand_detection:
            brand_terms.update(get_brand_terms(args.site_url or processing_site_url))
        if args.brand_terms:
            brand_terms.update(term.lower() for term in args.brand_terms)
        
        if brand_terms:
            pattern = r'\b(?:' + '|'.join(re.escape(term) for term in brand_terms) + r')\b'
            df['brand_type'] = df['query'].str.contains(pattern, case=False, regex=True).map({True: 'Brand', False: 'Non-Brand'})

        html_df = df.copy()
        html_df['ctr'] = html_df['ctr'].apply(lambda x: f"{x:.2%}")
        html_df['position'] = html_df['position'].apply(lambda x: f"{x:.2f}")

        html_report = create_html_report(html_df, site_url, start_date, end_date, args.report_limit, args.sub_table_limit, ' '.join(sys.argv), brand_terms)
        try:
            with open(html_output_path, 'w', encoding='utf-8') as f:
                f.write(html_report)
            print(f"Successfully created HTML report at {html_output_path}")
        except IOError as e:
            print(f"Error writing HTML: {e}")

if __name__ == '__main__':
    main()
