"""
Generates a specialized success report for Google Image Search performance.

This report analyses which images are driving traffic, the queries leading to them,
and which landing pages are benefiting from image search. It includes historical
trends, device breakdowns, and geographical distribution.

Usage:
    python image-performance-report.py <site_url> [--last-month | --last-3-months | --all-time]
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
import json
import time

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
    for i in range(2, 7): # Check from 2 to 7 days ago
        check_date = current_date - timedelta(days=i)
        check_date_str = check_date.strftime('%Y-%m-%d')
        try:
            request = {'startDate': check_date_str, 'endDate': check_date_str, 'dimensions': ['date'], 'rowLimit': 1}
            response = service.searchanalytics().query(siteUrl=site_url, body=request).execute()
            if 'rows' in response and response['rows']:
                return check_date
        except HttpError:
            continue
    return current_date - timedelta(days=3)

def fetch_gsc_data(service, site_url, start_date, end_date, dimensions, row_limit=5000):
    """Fetches performance data for Image Search with pagination."""
    all_data = []
    start_row = 0
    
    print(f"Fetching image data for dimensions: {', '.join(dimensions)}...")
    
    while True:
        try:
            request = {
                'startDate': start_date,
                'endDate': end_date,
                'dimensions': dimensions,
                'searchType': 'image',
                'rowLimit': row_limit,
                'startRow': start_row
            }
            response = service.searchanalytics().query(siteUrl=site_url, body=request).execute()
            
            if 'rows' in response:
                rows = response['rows']
                all_data.extend(rows)
                if len(rows) < row_limit:
                    break
                start_row += row_limit
                print(f"  - Retrieved {len(all_data)} rows...")
            else:
                break
        except HttpError as e:
            print(f"An HTTP error occurred: {e}")
            break
            
    if not all_data:
        return pd.DataFrame()

    df = pd.DataFrame(all_data)
    df[dimensions] = pd.DataFrame(df['keys'].tolist(), index=df.index)
    df = df.drop(columns=['keys'])
    return df

def create_html_report(site_url, start_date, end_date, data_payload):
    """Generates the Image Success Report HTML."""
    
    report_title = "Image Search Success Report"
    gen_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Data unpacking
    df_queries = data_payload['queries']
    df_pages = data_payload['pages']
    df_history = data_payload['history']
    df_device = data_payload['device']
    df_country = data_payload['country']

    # Table formatting helper
    def to_html_table(df, title, limit=50):
        if df.empty: return "<p class='text-muted'>No data available.</p>"
        
        display_df = df.head(limit).copy()
        
        # Format metrics
        if 'clicks' in display_df.columns: display_df['clicks'] = display_df['clicks'].apply(lambda x: f"{int(x):,}")
        if 'impressions' in display_df.columns: display_df['impressions'] = display_df['impressions'].apply(lambda x: f"{int(x):,}")
        if 'ctr' in display_df.columns: display_df['ctr'] = display_df['ctr'].apply(lambda x: f"{x:.2%}")
        if 'position' in display_df.columns: display_df['position'] = display_df['position'].apply(lambda x: f"{x:.2f}")

        # Make URLs clickable
        if 'page' in display_df.columns:
            display_df['page'] = display_df['page'].apply(lambda x: f'<a href="{x}" target="_blank" class="text-break">{x}</a>')

        return f"<h5>{title}</h5>" + display_df.to_html(
            classes="table table-striped table-hover table-sm", 
            index=False, 
            escape=False,
            border=0
        )

    # Chart data preparation
    import json
    history_json = {
        'labels': df_history['month'].tolist(),
        'clicks': df_history['clicks'].tolist(),
        'impressions': df_history['impressions'].tolist()
    }
    
    device_json = {
        'labels': df_device['device'].tolist(),
        'data': df_device['clicks'].tolist()
    }

    country_json = {
        'labels': df_country.head(10)['country'].tolist(),
        'data': df_country.head(10)['clicks'].tolist()
    }

    return f"""
<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{report_title}</title><link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<style>
    body {{ padding-top: 56px; background-color: #f4f7f6; }}
    .navbar {{ box-shadow: 0 2px 4px rgba(0,0,0,.1); }}
    .card {{ border: none; box-shadow: 0 0.125rem 0.25rem rgba(0, 0, 0, 0.075); margin-bottom: 2rem; }}
    .card-title {{ color: #2c3e50; font-weight: 600; }}
    .table-container {{ max-height: 500px; overflow-y: auto; background: white; border-radius: 0.5rem; }}
    .metric-value {{ font-size: 1.5rem; font-weight: bold; color: #0d6efd; }}
    .guide-box {{ background-color: #e9ecef; border-left: 5px solid #0d6efd; padding: 1rem; border-radius: 0.25rem; }}
</style></head>
<body>
    <header class="navbar navbar-expand-lg navbar-dark bg-dark fixed-top">
        <div class="container-fluid">
            <span class="navbar-brand mb-0 h1">{report_title}</span>
            <div class="navbar-text d-none d-md-block">
                <span class="me-3">{site_url}</span>
                <span>{start_date} to {end_date}</span>
            </div>
        </div>
    </header>

    <main class="container-fluid py-4">
        <div class="row">
            <div class="col-lg-8">
                <div class="card">
                    <div class="card-body">
                        <h5 class="card-title">Image Search Performance Trend (16 Months)</h5>
                        <div style="height: 350px;"><canvas id="historyChart"></canvas></div>
                    </div>
                </div>
            </div>
            <div class="col-lg-4">
                <div class="guide-box mb-4">
                    <h6><strong>What is an "Image Click"?</strong></h6>
                    <p><small>In Image Search, a "click" occurs when a user selects an image to see it larger, OR clicks a link that takes them to your website. Impressions are counted when an image is shown in results, even if it wasn't scrolled into view.</small></p>
                </div>
                <div class="card">
                    <div class="card-body">
                        <h5 class="card-title">Clicks by Device</h5>
                        <div style="height: 200px;"><canvas id="deviceChart"></canvas></div>
                    </div>
                </div>
            </div>
        </div>

        <div class="row">
            <div class="col-md-12">
                <div class="card">
                    <div class="card-body">
                        <h5 class="card-title text-primary">Top 50 Image Queries ({start_date} to {end_date})</h5>
                        <p class="text-muted small">The search terms users typed in before clicking your images during the <strong>last complete calendar month</strong>.</p>
                        <div class="table-container">
                            {to_html_table(df_queries, "", 50)}
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <div class="row">
            <div class="col-md-12">
                <div class="card">
                    <div class="card-body">
                        <h5 class="card-title text-primary">Top Landing Pages for Image Traffic ({start_date} to {end_date})</h5>
                        <p class="text-muted small">Which pages on your site were discovered through visual search during the <strong>last complete calendar month</strong>.</p>
                        <div class="table-container">
                            {to_html_table(df_pages, "", 50)}
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <div class="row">
            <div class="col-md-6">
                <div class="card">
                    <div class="card-body">
                        <h5 class="card-title text-primary">Top 10 Countries</h5>
                        <div style="height: 300px;"><canvas id="countryChart"></canvas></div>
                    </div>
                </div>
            </div>
            <div class="col-md-6">
                 <div class="guide-box">
                    <h6><strong>Optimisation Tip</strong></h6>
                    <p><small>Check the landing pages with high image impressions but low clicks. Ensure the images on those pages are high-quality, relevant, and have descriptive alt text. If a page gets lots of image clicks, consider adding a clear Call to Action (CTA) near those images to convert that visual traffic.</small></p>
                </div>
            </div>
        </div>
    </main>

    <script>
        const historyData = {json.dumps(history_json)};
        new Chart(document.getElementById('historyChart'), {{
            type: 'line',
            data: {{
                labels: historyData.labels,
                datasets: [
                    {{ label: 'Clicks', data: historyData.clicks, borderColor: '#0d6efd', tension: 0.2, yAxisID: 'y' }},
                    {{ label: 'Impressions', data: historyData.impressions, borderColor: '#ffc107', tension: 0.2, yAxisID: 'y1' }}
                ]
            }},
            options: {{ 
                responsive: true, maintainAspectRatio: false,
                scales: {{ 
                    y: {{ position: 'left', title: {{ display: true, text: 'Clicks' }} }},
                    y1: {{ position: 'right', grid: {{ drawOnChartArea: false }}, title: {{ display: true, text: 'Impressions' }} }}
                }}
            }}
        }});

        const deviceData = {json.dumps(device_json)};
        new Chart(document.getElementById('deviceChart'), {{
            type: 'doughnut',
            data: {{
                labels: deviceData.labels,
                datasets: [{{ data: deviceData.data, backgroundColor: ['#0d6efd', '#198754', '#ffc107'] }}]
            }},
            options: {{ responsive: true, maintainAspectRatio: false }}
        }});

        const countryData = {json.dumps(country_json)};
        new Chart(document.getElementById('countryChart'), {{
            type: 'bar',
            data: {{
                labels: countryData.labels,
                datasets: [{{ label: 'Clicks', data: countryData.data, backgroundColor: '#0d6efd' }}]
            }},
            options: {{ indexAxis: 'y', responsive: true, maintainAspectRatio: false }}
        }});
    </script>

    <footer class="py-4 bg-light border-top">
        <div class="container text-center">
            <p class="text-muted mb-0">Report generated on {gen_time} &bull; <a href="https://github.com/liamdelahunty/gsc-exporter" target="_blank">gsc-exporter</a></p>
        </div>
    </footer>
</body></html>
"""

def main():
    parser = argparse.ArgumentParser(description='Generate a Google Image Search Success Report.')
    parser.add_argument('site_url', help='The URL of the site to analyse.')
    args = parser.parse_args()
    
    site_url = args.site_url
    service = get_gsc_service()
    if not service: return

    latest_date = get_latest_available_gsc_date(service, site_url)
    
    # Range for tables (Last complete month)
    end_date_dt = latest_date.replace(day=1) - timedelta(days=1)
    start_date_dt = end_date_dt.replace(day=1)
    
    start_str = start_date_dt.strftime('%Y-%m-%d')
    end_str = end_date_dt.strftime('%Y-%m-%d')

    print(f"\n--- Analysing Image Search for {site_url} ({start_str} to {end_str}) ---")

    # 1. Fetch Top Queries
    df_queries = fetch_gsc_data(service, site_url, start_str, end_str, ['query'])
    
    # 2. Fetch Top Pages
    df_pages = fetch_gsc_data(service, site_url, start_str, end_str, ['page'])
    
    # 3. Fetch Device/Country Breakdown
    df_device = fetch_gsc_data(service, site_url, start_str, end_str, ['device'])
    df_country = fetch_gsc_data(service, site_url, start_str, end_str, ['country'])
    
    # 4. Fetch 16-month History
    history_start = (latest_date - relativedelta(months=15)).replace(day=1).strftime('%Y-%m-%d')
    print(f"Fetching 16-month history from {history_start}...")
    df_history_raw = fetch_gsc_data(service, site_url, history_start, latest_date.strftime('%Y-%m-%d'), ['date'])
    
    if not df_history_raw.empty:
        df_history_raw['date'] = pd.to_datetime(df_history_raw['date'])
        df_history = df_history_raw.groupby(df_history_raw['date'].dt.to_period('M')).agg({
            'clicks': 'sum',
            'impressions': 'sum'
        }).reset_index()
        df_history['month'] = df_history['date'].astype(str)
    else:
        df_history = pd.DataFrame(columns=['month', 'clicks', 'impressions'])

    # Data package
    data_payload = {
        'queries': df_queries,
        'pages': df_pages,
        'history': df_history,
        'device': df_device,
        'country': df_country
    }

    # Output paths
    if site_url.startswith('sc-domain:'):
        host_plain = site_url.replace('sc-domain:', '')
    else:
        host_plain = urlparse(site_url).netloc
    
    host_dir = host_plain.replace('www.', '')
    output_dir = os.path.join('output', host_dir)
    os.makedirs(output_dir, exist_ok=True)
    
    host_for_filename = host_dir.replace('.', '-')
    file_prefix = f"image-success-report-{host_for_filename}-{start_str}-to-{end_str}"
    
    # Save CSVs (we'll save queries and pages)
    df_queries.to_csv(os.path.join(output_dir, f"{file_prefix}-queries.csv"), index=False)
    df_pages.to_csv(os.path.join(output_dir, f"{file_prefix}-pages.csv"), index=False)
    
    # Generate HTML
    html_content = create_html_report(site_url, start_str, end_str, data_payload)
    html_path = os.path.join(output_dir, f"{file_prefix}.html")
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"\nSuccessfully generated reports in: {output_dir}")
    print(f"HTML: {os.path.basename(html_path)}")

if __name__ == '__main__':
    main()
