"""
Tracks the performance of top pages over the last 16 months.

This script identifies the top pages for the last complete calendar month and then 
fetches the performance metrics for those pages for each month over the 
available historical period (up to 16 months). It generates a CSV and an HTML 
report with interactive line charts using Chart.js.

Usage:
    python page-performance-over-time.py <site_url> [--limit <number_of_pages>]

Example:
    python page-performance-over-time.py https://www.example.com --limit 50
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
import argparse
import json

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

def get_latest_available_gsc_date(service, site_url):
    """Determines the latest date for which GSC data is available."""
    current_date = date.today()
    for i in range(5):
        check_date = current_date - timedelta(days=i)
        check_date_str = check_date.strftime('%Y-%m-%d')
        try:
            request = {'startDate': check_date_str, 'endDate': check_date_str, 'dimensions': ['date'], 'rowLimit': 1}
            response = service.searchanalytics().query(siteUrl=site_url, body=request).execute()
            if 'rows' in response and response['rows']:
                return check_date
        except HttpError:
            pass
    return current_date

def fetch_gsc_data(service, site_url, start_date, end_date, dimensions, filters=None):
    """Fetches performance data from GSC with retries and pagination."""
    all_data = []
    start_row = 0
    row_limit = 10000 
    
    request_body = {
        'startDate': start_date,
        'endDate': end_date,
        'dimensions': dimensions,
        'rowLimit': row_limit
    }
    if filters:
        request_body['dimensionFilterGroups'] = [{'filters': filters}]

    while True:
        success = False
        for attempt in range(3):
            try:
                request_body['startRow'] = start_row
                response = service.searchanalytics().query(siteUrl=site_url, body=request_body).execute()
                
                if 'rows' in response:
                    rows = response['rows']
                    all_data.extend(rows)
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
            
    if not all_data:
        return pd.DataFrame()

    df = pd.DataFrame(all_data)
    df[dimensions] = pd.DataFrame(df['keys'].tolist(), index=df.index)
    df = df.drop(columns=['keys'])
    return df

def create_html_report(site_url, df, top_pages_list):
    """Generates the HTML report with interactive charts."""
    
    # Sort months for the chart labels
    months = sorted(df['month'].unique())
    
    # Prepare data for Chart.js
    datasets = []
    colors = [
        '#4285F4', '#DB4437', '#F4B400', '#0F9D58', '#AB47BC', 
        '#00ACC1', '#FF7043', '#9E9D24', '#5C6BC0', '#F06292'
    ]
    
    for i, page in enumerate(top_pages_list):
        page_df = df[df['page'] == page].set_index('month')
        clicks_data = [int(page_df.loc[m, 'clicks']) if m in page_df.index else 0 for m in months]
        
        datasets.append({
            'label': page.replace(site_url, ''), # Shorten label
            'data': clicks_data,
            'borderColor': colors[i % len(colors)],
            'backgroundColor': colors[i % len(colors)],
            'fill': False,
            'tension': 0.1,
            'hidden': i >= 10 # Hide all but top 10 by default
        })

    # Prepare table data
    table_df = df.pivot(index='page', columns='month', values='clicks').fillna(0).astype(int)
    table_df['Total Clicks'] = table_df.sum(axis=1)
    table_df = table_df.sort_values(by='Total Clicks', ascending=False)
    table_html = table_df.to_html(classes="table table-striped table-hover table-sm", border=0)

    html_template = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Page Performance Over Time: {site_url}</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body {{ padding: 2rem; background-color: #f8f9fa; }}
        .card {{ border: none; box-shadow: 0 0.125rem 0.25rem rgba(0, 0, 0, 0.075); margin-bottom: 2rem; }}
        .table-container {{ max-height: 600px; overflow-y: auto; background: white; }}
        footer {{ margin-top: 3rem; text-align: center; color: #6c757d; }}
    </style>
</head>
<body>
    <div class="container-fluid">
        <h1 class="mb-4">Page Performance Over Time</h1>
        <h2 class="h4 text-muted mb-4">{site_url}</h2>

        <div class="card">
            <div class="card-body">
                <h5 class="card-title">Monthly Clicks for Top Pages</h5>
                <p class="text-muted small">Top 10 pages shown by default. Click items in the legend to toggle visibility.</p>
                <div style="height: 500px;"><canvas id="performanceChart"></canvas></div>
            </div>
        </div>

        <div class="card">
            <div class="card-body">
                <h5 class="card-title">Detailed Performance Table</h5>
                <div class="table-container">
                    {table_html}
                </div>
            </div>
        </div>
    </div>

    <script>
        const ctx = document.getElementById('performanceChart').getContext('2d');
        new Chart(ctx, {{
            type: 'line',
            data: {{
                labels: {json.dumps(months)},
                datasets: {json.dumps(datasets)}
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {{
                    legend: {{ position: 'bottom', labels: {{ boxWidth: 12, padding: 15, font: {{ size: 11 }} }} }}
                }},
                scales: {{
                    y: {{ beginAtZero: True, title: {{ display: true, text: 'Clicks' }} }},
                    x: {{ title: {{ display: true, text: 'Month' }} }}
                }}
            }}
        }});
    </script>

    <footer>
        <p><a href="../../resources/how-to-read-the-performance-analysis-report.html">User Guide</a> &bull; 
        <a href="https://github.com/liamdelahunty/gsc-exporter" target="_blank">gsc-exporter</a></p>
    </footer>
</body>
</html>
"""
    return html_template

def main():
    parser = argparse.ArgumentParser(description='Track performance of top pages over time.')
    parser.add_argument('site_url', help='The URL of the site to analyse.')
    parser.add_argument('--limit', type=int, default=25, help='Number of top pages to track (default 25).')
    parser.add_argument('--use-cache', action='store_true', help='Use cached CSV if available.')
    args = parser.parse_args()

    site_url = args.site_url
    service = get_gsc_service()
    if not service: return

    latest_date = get_latest_available_gsc_date(service, site_url)
    
    if site_url.startswith('sc-domain:'):
        host_plain = site_url.replace('sc-domain:', '')
    else:
        host_plain = urlparse(site_url).netloc
    host_dir = host_plain.replace('www.', '')
    output_dir = os.path.join('output', host_dir)
    os.makedirs(output_dir, exist_ok=True)
    host_for_filename = host_dir.replace('.', '-')
    
    csv_path = os.path.join(output_dir, f"page-performance-over-time-{host_for_filename}.csv")
    html_path = csv_path.replace('.csv', '.html')

    df_combined = None
    if args.use_cache and os.path.exists(csv_path):
        print(f"Loading cached data from {csv_path}...")
        df_combined = pd.read_csv(csv_path)

    if df_combined is None:
        # 1. Identify top pages from last complete month
        last_month_end = latest_date.replace(day=1) - timedelta(days=1)
        last_month_start = last_month_end.replace(day=1)
        
        print(f"Identifying top pages for {last_month_start.strftime('%B %Y')}...")
        df_top = fetch_gsc_data(service, site_url, last_month_start.strftime('%Y-%m-%d'), last_month_end.strftime('%Y-%m-%d'), ['page'])
        
        if df_top.empty:
            print("No data found for the last complete month.")
            return

        top_pages = df_top.sort_values(by='clicks', ascending=False).head(args.limit)['page'].tolist()
        
        # 2. Fetch history for these pages
        history_start = (latest_date - relativedelta(months=16)).strftime('%Y-%m-%d')
        print(f"Fetching history for {len(top_pages)} pages from {history_start}...")
        
        all_month_data = []
        for i in range(17):
            month_dt = latest_date.replace(day=1) - relativedelta(months=i)
            m_start = month_dt.strftime('%Y-%m-01')
            m_end = (month_dt + relativedelta(months=1) - timedelta(days=1)).strftime('%Y-%m-%d')
            
            # Fetch for all top pages in one call using filter
            filters = [{'dimension': 'page', 'operator': 'contains', 'expression': p} for p in top_pages]
            # Actually, multi-contains filter isn't supported, we need to loop or fetch all and filter
            df_m = fetch_gsc_data(service, site_url, m_start, m_end, ['page'])
            if not df_m.empty:
                df_m = df_m[df_m['page'].isin(top_pages)]
                df_m['month'] = month_dt.strftime('%Y-%m')
                all_month_data.append(df_m)

        if not all_month_data:
            print("No historical data found.")
            return

        df_combined = pd.concat(all_month_data, ignore_index=True)
        df_combined.to_csv(csv_path, index=False)
        print(f"Exported CSV to {csv_path}")

    # Generate HTML
    top_pages_list = df_combined.groupby('page')['clicks'].sum().sort_values(ascending=False).head(args.limit).index.tolist()
    html_content = create_html_report(site_url, df_combined, top_pages_list)
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    print(f"Exported HTML to {html_path}")

if __name__ == '__main__':
    main()
