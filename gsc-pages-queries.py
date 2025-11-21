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
                return None
            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_FILE, 'w') as token:
            token.write(creds.to_json())
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

def create_html_report(data_df, site_url, start_date, end_date):
    """Generates an HTML report for pages and queries."""
    # Group by query
    query_grouped = data_df.groupby('query', group_keys=False).apply(lambda x: x.sort_values(by='clicks', ascending=False)).reset_index(drop=True)
    
    # Group by page
    page_grouped = data_df.groupby('page', group_keys=False).apply(lambda x: x.sort_values(by='clicks', ascending=False)).reset_index(drop=True)

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
    </style>
</head>
<body>
    <div class="container-fluid">
        <h1 class="mb-3">Pages & Queries Report</h1>
        <h2>{site_url}</h2>
        <p class="text-muted">{start_date} to {end_date}</p>

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
                {generate_accordion_html(query_grouped, 'query', 'page')}
            </div>
            <div class="tab-pane fade" id="pages" role="tabpanel">
                {generate_accordion_html(page_grouped, 'page', 'query')}
            </div>
        </div>
    </div>
</body>
</html>
    """
    return html

def generate_accordion_html(grouped_df, primary_dim, secondary_dim):
    """Generates Bootstrap accordion HTML for the grouped data."""
    accordion_id = f"accordion-{primary_dim}"
    html = f'<div class="accordion mt-3" id="{accordion_id}">'

    # Get total metrics for the primary dimension
    primary_totals = grouped_df.groupby(primary_dim).agg(
        total_clicks=('clicks', 'sum'),
        total_impressions=('impressions', 'sum')
    ).sort_values(by='total_clicks', ascending=False).reset_index()

    item_count = 0
    for index, row in primary_totals.iterrows():
        primary_val = row[primary_dim]
        total_clicks = row['total_clicks']
        total_impressions = row['total_impressions']
        
        # Unique ID for accordion items
        collapse_id = f"collapse-{primary_dim}-{item_count}"
        header_id = f"header-{primary_dim}-{item_count}"
        
        # Get the subgroup for the current primary dimension value
        sub_group = grouped_df[grouped_df[primary_dim] == primary_val]
        
        # Format the sub-table
        sub_group_html = sub_group[[secondary_dim, 'clicks', 'impressions', 'ctr', 'position']].to_html(classes="table table-sm table-striped", index=False, border=0)

        html += f"""
        <div class="accordion-item">
            <h2 class="accordion-header" id="{header_id}">
                <button class="accordion-button collapsed" type="button" data-bs-toggle="collapse" data-bs-target="#{collapse_id}">
                    <strong>{primary_val}</strong>&nbsp;<span class="badge bg-primary rounded-pill ms-auto me-2">Clicks: {total_clicks:,d}</span><span class="badge bg-secondary rounded-pill me-2">Impressions: {total_impressions:,d}</span>
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
        if item_count >= 1000: # Limit to 1000 items for performance
            html += '<div>...and more...</div>'
            break

    html += '</div>'
    return html

def main():
    """Main function to run the script."""
    parser = argparse.ArgumentParser(description='Export Google Search Console pages and queries.')
    parser.add_argument('site_url', help='The URL of the site to export data for.')
    
    date_group = parser.add_mutually_exclusive_group()
    date_group.add_argument('--start-date', help='Start date in YYYY-MM-DD format.')
    date_group.add_argument('--last-7-days', action='store_true', help='Set date range to the last 7 days.')
    date_group.add_argument('--last-28-days', action='store_true', help='Set date range to the last 28 days.')
    date_group.add_argument('--last-month', action='store_true', help='Set date range to the last calendar month.')
    
    parser.add_argument('--end-date', help='End date in YYYY-MM-DD format. Used only with --start-date.')
    
    args = parser.parse_args()
    
    today = date.today()

    if not any([args.start_date, args.last_7_days, args.last_28_days, args.last_month]):
        args.last_28_days = True

    if args.last_7_days:
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
    else: # Custom date range
        start_date = args.start_date
        end_date = args.end_date

    service = get_gsc_service()
    if not service:
        return

    raw_data = get_pages_queries_data(service, args.site_url, start_date, end_date)
    
    if raw_data:
        df = pd.DataFrame(raw_data)
        # The 'keys' column contains a list of [query, page]
        df[['query', 'page']] = pd.DataFrame(df['keys'].tolist(), index=df.index)
        df.drop(columns=['keys'], inplace=True)
        
        # Format for HTML report
        html_df = df.copy()
        html_df['ctr'] = html_df['ctr'].apply(lambda x: f"{x:.2%}")
        html_df['position'] = html_df['position'].apply(lambda x: f"{x:.2f}")

        # --- Output File Naming ---
        if args.site_url.startswith('sc-domain:'):
            host_plain = args.site_url.replace('sc-domain:', '')
        else:
            host_plain = urlparse(args.site_url).netloc
        
        host_dir = host_plain.replace('www.', '')
        output_dir = os.path.join('output', host_dir)
        os.makedirs(output_dir, exist_ok=True)
        host_for_filename = host_dir.replace('.', '-')
        
        file_name = f"gsc-pages-queries-{host_for_filename}-{start_date}-to-{end_date}.html"
        output_path = os.path.join(output_dir, file_name)

        # --- Generate and Save Report ---
        html_report = create_html_report(html_df, args.site_url, start_date, end_date)
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(html_report)
            print(f"\nSuccessfully created HTML report at {output_path}")
        except IOError as e:
            print(f"Error writing to file: {e}")

    else:
        print("No data found for the given site and date range.")

if __name__ == '__main__':
    main()
