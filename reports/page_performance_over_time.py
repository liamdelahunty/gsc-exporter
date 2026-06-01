"""
Tracks the performance of top pages over the last 16 months.
Adapted for the modular GSC Exporter.
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

def create_html_report(site_url, df, top_pages_list):
    """Generates the HTML report with Chart.js line charts."""
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
                    y: {{ beginAtZero: true, title: {{ display: true, text: 'Clicks' }} }}
                }}
            }}
        }});
    </script>
    <footer class="footer mt-auto py-3 bg-light">
        <div class="container text-center">
            <span class="text-muted">Report generated on {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}. <a href="https://github.com/liamdelahunty/gsc-exporter" target="_blank">gsc-exporter</a></span>
        </div>
    </footer>
</body>
</html>
"""
    return html_template

def run_report(service, site_url, start_date, end_date, limit=25, months=16):
    """Executes the page performance over time report."""
    print(f"Running Page Performance Over Time Report for {site_url} ({months} months ending {end_date})...")
    
    # 1. Fetch Top Pages for the provided period
    df_top = fetch_with_cache(service, site_url, start_date, end_date, ['page'])
    if df_top.empty:
        print(f"No page data found for {start_date} to {end_date}.")
        return None
        
    top_pages = df_top.sort_values(by='clicks', ascending=False).head(limit)['page'].tolist()
    
    # 2. Fetch Historical Data (lookback from end_date)
    all_month_data = []
    base_end_dt = datetime.strptime(end_date, '%Y-%m-%d')
    for i in range(months):
        month_dt = base_end_dt - relativedelta(months=i)
        m_start = month_dt.strftime('%Y-%m-01')
        m_end = (month_dt + relativedelta(months=1) - timedelta(days=1)).strftime('%Y-%m-%d')
        if i == 0:
            m_end = end_date # Ensure we don't go past the requested end_date
        
        df_m = fetch_with_cache(service, site_url, m_start, m_end, ['page'])
        if not df_m.empty:
            df_m = df_m[df_m['page'].isin(top_pages)].copy()
            df_m['month'] = month_dt.strftime('%Y-%m')
            all_month_data.append(df_m)
            
    if not all_month_data:
        print("No historical data found.")
        return None
        
    df_combined = pd.concat(all_month_data, ignore_index=True)
    
    # 4. Define Output Paths
    output_dir = get_output_dir(site_url)
    os.makedirs(output_dir, exist_ok=True)
    slug = get_filename_slug(site_url)
    
    file_prefix = f"page-performance-over-time-{slug}-{end_date}"
    csv_path = os.path.join(output_dir, f"{file_prefix}.csv")
    html_path = os.path.join(output_dir, f"{file_prefix}.html")
    
    # 5. Save CSV
    df_combined.to_csv(csv_path, index=False, encoding='utf-8')
    
    # 6. Generate HTML
    top_pages_list = df_combined.groupby('page')['clicks'].sum().sort_values(ascending=False).head(limit).index.tolist()
    html_content = create_html_report(site_url, df_combined, top_pages_list)
    
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
        
    print(f"CSV saved to: {csv_path}")
    print(f"HTML saved to: {html_path}")
    return html_path

if __name__ == '__main__':
    import argparse
    from core.client import get_gsc_service
    
    parser = argparse.ArgumentParser(description='Track performance of top pages over time.')
    parser.add_argument('site_url', help='The URL of the site to analyse.')
    parser.add_argument('--start-date', help='Start date (YYYY-MM-DD).')
    parser.add_argument('--end-date', help='End date (YYYY-MM-DD).')
    parser.add_argument('--last-7-days', action='store_true', help='Run for the last 7 available days.')
    parser.add_argument('--last-month', action='store_true', help='Run for the last calendar month.')
    parser.add_argument('--limit', type=int, default=25, help='Number of top pages to track.')
    parser.add_argument('--months', type=int, default=16, help='Number of months for historical lookback.')
    
    args = parser.parse_args()
    
    service = get_gsc_service()
    if service:
        start_date, end_date = parse_standard_date_args(args, service, args.site_url)
        
        run_report(service, args.site_url, start_date, end_date, args.limit, args.months)

