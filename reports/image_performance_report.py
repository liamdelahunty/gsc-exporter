"""
Generates a specialized success report for Google Image Search performance.
Refactored for modular GSC Exporter.
"""
import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import pandas as pd
import json
from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta
from core.naming import get_output_dir, get_filename_slug
from core.cache import fetch_with_cache
from core.date_utils import parse_standard_date_args, get_month_range_lookback

def create_html_report(site_url, start_date, end_date, data_payload):
    """Generates the Image Success Report HTML."""
    report_title = "Image Search Success Report"
    gen_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    df_queries = data_payload['queries']
    df_pages = data_payload['pages']
    df_matrix = data_payload['matrix']
    df_history = data_payload['history']
    df_device = data_payload['device']
    df_country = data_payload['country']

    def to_html_table(df, title, limit=50):
        if df.empty: return "<p class='text-muted'>No data available.</p>"
        display_df = df.head(limit).copy()
        if 'clicks' in display_df.columns: display_df['clicks'] = display_df['clicks'].apply(lambda x: f"{int(x):,}")
        if 'impressions' in display_df.columns: display_df['impressions'] = display_df['impressions'].apply(lambda x: f"{int(x):,}")
        if 'ctr' in display_df.columns: display_df['ctr'] = display_df['ctr'].apply(lambda x: f"{x:.2%}")
        if 'position' in display_df.columns: display_df['position'] = display_df['position'].apply(lambda x: f"{x:.2f}")
        if 'page' in display_df.columns:
            display_df['page'] = display_df['page'].apply(lambda x: f'<a href="{x}" target="_blank" class="text-break">{x}</a>')
        return f"<h5>{title}</h5>" + display_df.to_html(classes="table table-striped table-hover table-sm", index=False, escape=False, border=0)

    history_json = {
        'labels': df_history['month'].tolist(),
        'clicks': df_history['clicks'].tolist(),
        'impressions': df_history['impressions'].tolist()
    }
    device_json = {'labels': df_device['device'].tolist(), 'data': df_device['clicks'].tolist()} if not df_device.empty else {'labels': [], 'data': []}
    country_json = {'labels': df_country.head(10)['country'].tolist(), 'data': df_country.head(10)['clicks'].tolist()} if not df_country.empty else {'labels': [], 'data': []}

    return f"""
<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{report_title}</title><link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<style>
    body {{ padding-top: 56px; background-color: #f4f7f6; }}
    .card {{ border: none; box-shadow: 0 0.125rem 0.25rem rgba(0, 0, 0, 0.075); margin-bottom: 2rem; }}
    .table-container {{ max-height: 500px; overflow-y: auto; background: white; border-radius: 0.5rem; }}
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
                <div class="card"><div class="card-body">
                    <h5 class="card-title">Image Search Performance Trend</h5>
                    <div style="height: 350px;"><canvas id="historyChart"></canvas></div>
                </div></div>
            </div>
            <div class="col-lg-4">
                <div class="guide-box mb-4"><h6>What is an "Image Click"?</h6><p><small>A "click" occurs when a user selects an image OR clicks a link to your site.</small></p></div>
                <div class="card"><div class="card-body">
                    <h5 class="card-title">Clicks by Device</h5>
                    <div style="height: 200px;"><canvas id="deviceChart"></canvas></div>
                </div></div>
            </div>
        </div>
        <div class="row"><div class="col-md-12"><div class="card"><div class="card-body">
            <h5 class="card-title text-primary">Query & Page Relationship Matrix</h5>
            <div class="table-container">{to_html_table(df_matrix, "", 100)}</div>
        </div></div></div></div>
        <div class="row">
            <div class="col-md-6"><div class="card"><div class="card-body">
                <h5 class="card-title text-primary">Top 50 Image Queries</h5>
                <div class="table-container">{to_html_table(df_queries, "", 50)}</div>
            </div></div></div>
            <div class="col-md-6"><div class="card"><div class="card-body">
                <h5 class="card-title text-primary">Top Landing Pages for Image Traffic</h5>
                <div class="table-container">{to_html_table(df_pages, "", 50)}</div>
            </div></div></div>
        </div>
        <div class="row">
            <div class="col-md-6"><div class="card"><div class="card-body">
                <h5 class="card-title text-primary">Top 10 Countries</h5>
                <div style="height: 300px;"><canvas id="countryChart"></canvas></div>
            </div></div></div>
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
        new Chart(document.getElementById('deviceChart'), {{
            type: 'doughnut',
            data: {{
                labels: {json.dumps(device_json['labels'])},
                datasets: [{{ data: {json.dumps(device_json['data'])}, backgroundColor: ['#0d6efd', '#198754', '#ffc107'] }}]
            }},
            options: {{ responsive: true, maintainAspectRatio: false }}
        }});
        new Chart(document.getElementById('countryChart'), {{
            type: 'bar',
            data: {{
                labels: {json.dumps(country_json['labels'])},
                datasets: [{{ label: 'Clicks', data: {json.dumps(country_json['data'])}, backgroundColor: '#0d6efd' }}]
            }},
            options: {{ indexAxis: 'y', responsive: true, maintainAspectRatio: false }}
        }});
    </script>
    <footer class="py-4 bg-light border-top text-center"><p class="text-muted mb-0">Report generated on {gen_time} &bull; gsc-exporter</p></footer>
</body></html>
"""

def run_report(service, site_url, start_date, end_date):
    """Executes the Image Search success report."""
    print(f"Running Image Performance Report for {site_url} ({start_date} to {end_date})...")
    
    # 1. Fetch Data for tables
    df_queries = fetch_with_cache(service, site_url, start_date, end_date, ['query'], 'image')
    df_pages = fetch_with_cache(service, site_url, start_date, end_date, ['page'], 'image')
    df_matrix = fetch_with_cache(service, site_url, start_date, end_date, ['query', 'page'], 'image')
    df_device = fetch_with_cache(service, site_url, start_date, end_date, ['device'], 'image')
    df_country = fetch_with_cache(service, site_url, start_date, end_date, ['country'], 'image')
    
    # 2. History (16 months lookback from end_date)
    history_start, _ = get_month_range_lookback(end_date, months=16)
    df_history_raw = fetch_with_cache(service, site_url, history_start, end_date, ['date'], 'image')
    
    if not df_history_raw.empty:
        df_history_raw['date'] = pd.to_datetime(df_history_raw['date'])
        df_history = df_history_raw.groupby(df_history_raw['date'].dt.to_period('M')).agg({
            'clicks': 'sum',
            'impressions': 'sum'
        }).reset_index()
        df_history['month'] = df_history['date'].astype(str)
    else:
        df_history = pd.DataFrame(columns=['month', 'clicks', 'impressions'])

    data_payload = {
        'queries': df_queries, 'pages': df_pages, 'matrix': df_matrix,
        'history': df_history, 'device': df_device, 'country': df_country
    }

    # 3. Output Paths
    output_dir = get_output_dir(site_url)
    os.makedirs(output_dir, exist_ok=True)
    slug = get_filename_slug(site_url)
    file_prefix = f"image-performance-{slug}-{start_date}-to-{end_date}"
    
    # 4. Save and Generate
    html_content = create_html_report(site_url, start_date, end_date, data_payload)
    html_path = os.path.join(output_dir, f"{file_prefix}.html")
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    csv_queries_path = os.path.join(output_dir, f"{file_prefix}-queries.csv")
    csv_pages_path = os.path.join(output_dir, f"{file_prefix}-pages.csv")
    csv_matrix_path = os.path.join(output_dir, f"{file_prefix}-matrix.csv")
    
    df_queries.to_csv(csv_queries_path, index=False, encoding='utf-8')
    df_pages.to_csv(csv_pages_path, index=False, encoding='utf-8')
    df_matrix.to_csv(csv_matrix_path, index=False, encoding='utf-8')
        
    print(f"CSV saved to: {csv_queries_path}")
    print(f"CSV saved to: {csv_pages_path}")
    print(f"CSV saved to: {csv_matrix_path}")
    print(f"HTML saved to: {html_path}")
    return html_path

if __name__ == '__main__':
    import argparse
    from core.client import get_gsc_service
    parser = argparse.ArgumentParser(description='Image performance report.')
    parser.add_argument('site_url', help='The URL of the site to analyse.')
    parser.add_argument('--start-date', help='Start date (YYYY-MM-DD).')
    parser.add_argument('--end-date', help='End date (YYYY-MM-DD).')
    parser.add_argument('--last-month', action='store_true', help='Run for the last calendar month.')

    args = parser.parse_args()
    start_date, end_date = parse_standard_date_args(args)

    service = get_gsc_service()
    if service:
        run_report(service, args.site_url, start_date, end_date)
