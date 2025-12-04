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

def create_html_report(data_df, site_url, start_date, end_date, report_limit, sub_table_limit):
    """Generates an HTML report for pages and queries."""
    # Group by query
    query_grouped = data_df.sort_values(by=['query', 'clicks'], ascending=[True, False]).reset_index(drop=True)
    
    # Group by page
    page_grouped = data_df.sort_values(by=['page', 'clicks'], ascending=[True, False]).reset_index(drop=True)

    # --- Truncation Alert ---
    query_count = data_df['query'].nunique()
    page_count = data_df['page'].nunique()
    is_truncated = query_count > report_limit or page_count > report_limit

    alert_html = ""
    if is_truncated:
        alert_html = f"""
        <div class="alert alert-info">
            <strong>Report Truncated:</strong> To improve performance, this HTML report has been shortened.
            <ul>
                <li>The report is limited to the top <strong>{report_limit}</strong> primary items (queries/pages) by clicks.</li>
                <li>Each table within an item is limited to its top <strong>{sub_table_limit}</strong> rows.</li>
            </ul>
            The full, unfiltered data is available in the accompanying CSV file. You can adjust these limits using the <code>--report-limit</code> and <code>--sub-table-limit</code> flags.
        </div>
        """

    # --- HTML Generation ---
    html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Pages & Queries Report for {site_url}</title>
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
        <h1 class="mb-3">Pages & Queries Report</h1>
        <h2>{site_url}</h2>
        <p class="text-muted">{start_date} to {end_date}</p>

        {alert_html}

        <ul class="nav nav-tabs" id="myTab" role="tablist">
            <li class="nav-item" role="presentation">
                <button class="nav-link active" id="queries-tab" data-bs-toggle="tab" data-bs-target="#queries" type="button" role="tab">Queries to Pages</button>
            </li>
            <li class="nav-item" role="presentation">
                <button class="nav-link" id="pages-tab" data-bs-toggle="tab" data-bs-target="#pages" type="button" role="tab">Pages to Queries</button>
            </li>
        </ul>

        <div class="tab-content" id="myTabContent">
            <div class="tab-pane fade show active" id="queries" role="tabpanel">
                {generate_accordion_html(query_grouped, 'query', 'page', report_limit, sub_table_limit)}
            </div>
            <div class="tab-pane fade" id="pages" role="tabpanel">
                {generate_accordion_html(page_grouped, 'page', 'query', report_limit, sub_table_limit)}
            </div>
        </div>
    </div>
</body>
</html>
    """
    return html

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

def main():
    """Main function to run the script."""
    parser = argparse.ArgumentParser(
        description='Export Google Search Console pages and queries. Generates an HTML report from either live GSC data or a pre-existing CSV file.',
        epilog='Example Usage:\n'
               '  To download data: python gsc-pages-queries.py --site-url https://www.example.com --last-month\n'
               '  To use cached data: python gsc-pages-queries.py --site-url https://www.example.com --last-month --use-cache\n'
               '  To generate from a csv: python gsc-pages-queries.py --csv ./output/example-com/report.csv --report-limit 50',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    # --- Argument Groups ---
    # Group for data source
    source_group = parser.add_mutually_exclusive_group(required=True)
    source_group.add_argument('--site-url', help='The URL of the site to export data for.')
    source_group.add_argument('--csv', help='Path to a CSV file to generate the report from, skipping the download.')

    # Group for date range
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
    
    args = parser.parse_args()

    # --- Main Logic ---
    df = None
    
    # --- Case 1: Generate report from a local CSV file ---
    if args.csv:
        if not os.path.exists(args.csv):
            print(f"Error: CSV file not found at '{args.csv}'")
            return
        print(f"Generating report from CSV file: {args.csv}")
        df = pd.read_csv(args.csv)
        # Use placeholders for metadata as it cannot be inferred from the CSV alone
        site_url = "Loaded from CSV"
        start_date = "N/A"
        end_date = "N/A"
        # Try to parse info from filename for a better title
        try:
            filename = os.path.basename(args.csv)
            parts = filename.replace('gsc-pages-queries-', '').replace('.csv', '').split('-to-')
            if len(parts) == 2:
                end_date = parts[1]
                remaining_parts = parts[0].split('-')
                start_date = remaining_parts[-1]
                # This is imperfect, but better than nothing
                site_url = '-'.join(remaining_parts[:-1]).replace('-', '.')
        except Exception:
            pass # Ignore parsing errors, placeholders will be used

        html_output_path = args.csv.replace('.csv', '.html')

    # --- Case 2: Download data or use cache ---
    else:
        # Add a correction for common typos in the site URL
        if 'wwww.' in args.site_url:
            args.site_url = args.site_url.replace('wwww.', 'www.')
        
        today = date.today()

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
            start_date = (today - timedelta(days=2)).strftime('%Y-%m-%d')
            end_date = (today - timedelta(days=2)).strftime('%Y-%m-%d')
        elif args.last_7_days:
            start_date = (today - timedelta(days=7)).strftime('%Y-%m-%d')
            end_date = today.strftime('%Y-%m-%d')
        elif args.last_28_days:
            start_date = (today - timedelta(days=28)).strftime('%Y-%m-%d')
            end_date = today.strftime('%Y-%m-%d')
        elif args.last_month:
            first_day_of_current_month = today.replace(day=1)
            last_day_of_previous_month = first_day_of_current_month - timedelta(days=1)
            start_date = last_day_of_previous_month.replace(day=1).strftime('%Y-%m-%d')
            end_date = last_day_of_previous_month.strftime('%Y-%m-%d')
        elif args.last_quarter:
            start_date = (today - relativedelta(months=3)).strftime('%Y-%m-%d')
            end_date = today.strftime('%Y-%m-%d')
        elif args.last_3_months:
            start_date = (today - relativedelta(months=3)).strftime('%Y-%m-%d')
            end_date = today.strftime('%Y-%m-%d')
        elif args.last_6_months:
            start_date = (today - relativedelta(months=6)).strftime('%Y-%m-%d')
            end_date = today.strftime('%Y-%m-%d')
        elif args.last_12_months:
            start_date = (today - relativedelta(months=12)).strftime('%Y-%m-%d')
            end_date = today.strftime('%Y-%m-%d')
        elif args.last_16_months:
            start_date = (today - relativedelta(months=16)).strftime('%Y-%m-%d')
            end_date = today.strftime('%Y-%m-%d')
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
            service = get_gsc_service()
            if not service:
                return
            
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
        # Format for HTML report
        html_df = df.copy()
        # Ensure required columns exist before formatting
        if 'ctr' in html_df.columns:
            html_df['ctr'] = html_df['ctr'].apply(lambda x: f"{x:.2%}")
        if 'position' in html_df.columns:
            html_df['position'] = html_df['position'].apply(lambda x: f"{x:.2f}")

        html_report = create_html_report(html_df, site_url, start_date, end_date, args.report_limit, args.sub_table_limit)
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
