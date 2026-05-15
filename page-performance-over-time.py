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
    """Determines the latest available GSC date."""
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
    """Fetches performance data with retries."""
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
                    all_data.extend(response['rows'])
                    if len(response['rows']) < row_limit: break
                    start_row += row_limit
                else: break
                success = True
                break
            except (socket.timeout, TimeoutError):
                time.sleep(5 * (attempt + 1))
            except HttpError: break
        
        if not success or 'rows' not in response or len(response['rows']) < row_limit: break
            
    if not all_data:
        return pd.DataFrame()

    df = pd.DataFrame(all_data)
    df[dimensions] = pd.DataFrame(df['keys'].tolist(), index=df.index)
    df = df.drop(columns=['keys'])
    return df

def create_html_report(site_url, df, top_pages_list):
    """Generates the HTML report with link refinements."""
    
    months = sorted(df['month'].unique())
    datasets = []
    colors = ['#4285F4', '#DB4437', '#F4B400', '#0F9D58', '#AB47BC', '#00ACC1', '#FF7043', '#9E9D24', '#5C6BC0', '#F06292']
    
    for i, page in enumerate(top_pages_list):
        page_df = df[df['page'] == page].set_index('month')
        clicks_data = [int(page_df.loc[m, 'clicks']) if m in page_df.index else 0 for m in months]
        
        datasets.append({
            'label': page.replace(site_url, ''),
            'data': clicks_data,
            'borderColor': colors[i % len(colors)],
            'backgroundColor': colors[i % len(colors)],
            'fill': False,
            'tension': 0.1,
            'hidden': i >= 10 
        })

    table_df = df.pivot(index='page', columns='month', values='clicks').fillna(0).astype(int)
    table_df['Total Clicks'] = table_df.sum(axis=1)
    table_df = table_df.sort_values(by='Total Clicks', ascending=False).reset_index()
    
    # Make URLs clickable in the table
    table_df['page'] = table_df['page'].apply(lambda x: f'<a href="{x}" target="_blank" class="text-break">{x}</a>')
    table_html = table_df.to_html(classes="table table-striped table-hover table-sm", border=0, index=False, escape=False)

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
        .table td {{ word-wrap: break-word; min-width: 100px; max-width: 500px; }}
        .text-break {{ word-break: break-all !important; }}
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
                <div style="height: 500px;"><canvas id="performanceChart"></canvas></div>
            </div>
        </div>

        <div class="card">
            <div class="card-body">
                <h5 class="card-title">Detailed Performance Table</h5>
                <div class="table-responsive table-container">
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
                    legend: {{ position: 'bottom', labels: {{ boxWidth: 12, padding: 15 }} }}
                }},
                scales: {{
                    y: {{ beginAtZero: True, title: {{ display: true, text: 'Clicks' }} }}
                }}
            }}
        }});
    </script>
    <footer><p><a href="https://github.com/liamdelahunty/gsc-exporter" target="_blank">gsc-exporter</a></p></footer>
</body>
</html>
"""
    return html_template

def main():
    parser = argparse.ArgumentParser(description='Track performance of top pages over time.')
    parser.add_argument('site_url', help='The site URL.')
    parser.add_argument('--limit', type=int, default=25)
    parser.add_argument('--use-cache', action='store_true')
    args = parser.parse_args()

    service = get_gsc_service()
    if not service: return

    latest_date = get_latest_available_gsc_date(service, args.site_url)
    host_plain = args.site_url.replace('sc-domain:', '') if args.site_url.startswith('sc-domain:') else urlparse(args.site_url).netloc
    host_dir = host_plain.replace('www.', '')
    output_dir = os.path.join('output', host_dir)
    os.makedirs(output_dir, exist_ok=True)
    
    csv_path = os.path.join(output_dir, f"page-performance-over-time-{host_dir.replace('.', '-')}.csv")
    html_path = csv_path.replace('.csv', '.html')

    if args.use_cache and os.path.exists(csv_path):
        df_combined = pd.read_csv(csv_path)
    else:
        last_month_end = latest_date.replace(day=1) - timedelta(days=1)
        last_month_start = last_month_end.replace(day=1)
        df_top = fetch_gsc_data(service, args.site_url, last_month_start.strftime('%Y-%m-%d'), last_month_end.strftime('%Y-%m-%d'), ['page'])
        if df_top.empty: return
        top_pages = df_top.sort_values(by='clicks', ascending=False).head(args.limit)['page'].tolist()
        
        all_month_data = []
        for i in range(17):
            month_dt = latest_date.replace(day=1) - relativedelta(months=i)
            m_start, m_end = month_dt.strftime('%Y-%m-01'), (month_dt + relativedelta(months=1) - timedelta(days=1)).strftime('%Y-%m-%d')
            df_m = fetch_gsc_data(service, args.site_url, m_start, m_end, ['page'])
            if not df_m.empty:
                df_m = df_m[df_m['page'].isin(top_pages)]
                df_m['month'] = month_dt.strftime('%Y-%m')
                all_month_data.append(df_m)
        if not all_month_data: return
        df_combined = pd.concat(all_month_data, ignore_index=True)
        df_combined.to_csv(csv_path, index=False)

    top_pages_list = df_combined.groupby('page')['clicks'].sum().sort_values(ascending=False).head(args.limit).index.tolist()
    html_content = create_html_report(args.site_url, df_combined, top_pages_list)
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    print(f"Generated HTML report: {html_path}")

if __name__ == '__main__':
    main()
