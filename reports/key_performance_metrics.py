"""
Performs analysis of Google Search Console data, gathering key performance metrics.
Refactored for modular GSC Exporter.
"""
import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import pandas as pd
from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta
from core.naming import get_output_dir, get_filename_slug
from core.cache import fetch_with_cache
from core.date_utils import parse_standard_date_args

def create_single_site_html_report(df, report_title, full_period_str):
    """Generates a simplified HTML report for a single site, including a chart."""
    df_table = df.copy()
    if 'month_date' in df_table.columns:
        df_table = df_table.drop(columns=['month_date'])
    
    df_table['clicks'] = df_table['clicks'].apply(lambda x: f"{x:,.0f}")
    df_table['impressions'] = df_table['impressions'].apply(lambda x: f"{x:,.0f}")
    df_table['ctr'] = df_table['ctr'].apply(lambda x: f"{x:.2%}")
    df_table['position'] = df_table['position'].apply(lambda x: f"{x:.2f}")
    
    report_body = df_table.to_html(classes="table table-striped table-hover", index=False, border=0)
    chart_data = df.sort_values(by='month').to_json(orient='records')

    return f"""
<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Google Organic Performance Report for {report_title}</title><link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<style>body{{padding:2rem;}}h1,h2{{border-bottom:2px solid #dee2e6;padding-bottom:.5rem;margin-top:2rem;}}.table thead th {{background-color: #434343;color: #ffffff;text-align: left;}}footer{{margin-top:3rem;text-align:center;color:#6c757d;}}</style></head>
<body><div class="container-fluid"><h1>Google Organic Performance Report for {report_title}</h1>
<p class="text-muted">{full_period_str}</p>
<div class="card my-4">
  <div class="card-header"><h3>Clicks vs. Impressions</h3></div>
  <div class="card-body"><canvas id="performanceChart"></canvas></div>
</div>
<h2>Data Table</h2>
<div class="table-responsive">{report_body}</div></div>
<footer><p><a href="https://github.com/liamdelahunty/gsc-exporter" target="_blank">gsc-exporter</a></p></footer>
<script>
    const data = {chart_data};
    const labels = data.map(row => row.month);

    new Chart(document.getElementById('performanceChart'), {{
        type: 'line',
        data: {{
            labels: labels,
            datasets: [
                {{
                    label: 'Clicks',
                    data: data.map(row => row.clicks),
                    borderColor: 'rgba(54, 162, 235, 1)',
                    backgroundColor: 'rgba(54, 162, 235, 0.2)',
                    yAxisID: 'yClicks',
                    fill: false,
                    tension: 0.1
                }},
                {{
                    label: 'Impressions',
                    data: data.map(row => row.impressions),
                    borderColor: 'rgba(255, 99, 132, 1)',
                    backgroundColor: 'rgba(255, 99, 132, 0.2)',
                    yAxisID: 'yImpressions',
                    fill: false,
                    tension: 0.1
                }}
            ]
        }},
        options: {{
            responsive: true,
            maintainAspectRatio: false,
            interaction: {{ mode: 'index', intersect: false }},
            scales: {{
                yClicks: {{ type: 'linear', display: true, position: 'left', title: {{ display: true, text: 'Clicks' }} }},
                yImpressions: {{ type: 'linear', display: true, position: 'right', title: {{ display: true, text: 'Impressions' }}, grid: {{ drawOnChartArea: false }} }}
            }}
        }}
    }});
</script>
</body></html>"""

def run_report(service, site_url, months=16, anchor_end_date=None):
    """Executes the Key Performance Metrics report."""
    print(f"Running Key Performance Metrics for {site_url} ({months} months)...")
    
    # 1. Date Range
    if anchor_end_date:
        end_date_dt = datetime.strptime(anchor_end_date, '%Y-%m-%d').date()
    else:
        today = date.today()
        end_date_dt = today.replace(day=1) - timedelta(days=1)
        
    start_date_dt = (end_date_dt.replace(day=1) - relativedelta(months=months-1))
    
    start_date = start_date_dt.strftime('%Y-%m-%d')
    end_date = end_date_dt.strftime('%Y-%m-%d')

    # 2. Fetch Data (Aggregated by date for site-wide metrics)
    df = fetch_with_cache(service, site_url, start_date, end_date, ['date'])
    
    if df.empty:
        print("No data found.")
        return None

    # 3. Process to Monthly
    df['date'] = pd.to_datetime(df['date'])
    df['month'] = df['date'].dt.strftime('%Y-%m')
    
    monthly_df = df.groupby('month').agg({
        'clicks': 'sum',
        'impressions': 'sum',
        'position': 'mean'
    }).reset_index()
    
    monthly_df['ctr'] = monthly_df['clicks'] / monthly_df['impressions']
    monthly_df = monthly_df.sort_values('month', ascending=False)
    
    # Keep date object for sorting in chart
    monthly_df['month_date'] = pd.to_datetime(monthly_df['month'])

    # 4. Output Paths
    output_dir = get_output_dir(site_url)
    os.makedirs(output_dir, exist_ok=True)
    slug = get_filename_slug(site_url)
    
    most_recent = monthly_df['month'].iloc[0]
    file_prefix = f"key-metrics-{slug}-{most_recent}"
    
    csv_path = os.path.join(output_dir, f"{file_prefix}.csv")
    html_path = os.path.join(output_dir, f"{file_prefix}.html")

    # 5. Save and Generate
    monthly_df.to_csv(csv_path, index=False, encoding='utf-8')
    
    full_period_str = f"Monthly breakdown from {monthly_df['month'].min()} to {monthly_df['month'].max()}"
    html_content = create_single_site_html_report(monthly_df, site_url, full_period_str)
    
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
        
    print(f"CSV saved to: {csv_path}")
    print(f"HTML saved to: {html_path}")
    return html_path

if __name__ == '__main__':
    import argparse
    from core.client import get_gsc_service
    parser = argparse.ArgumentParser(description='Key performance metrics.')
    parser.add_argument('site_url', help='The site URL.')
    parser.add_argument('--start-date', help='Start date (YYYY-MM-DD).')
    parser.add_argument('--end-date', help='End date (YYYY-MM-DD).')
    parser.add_argument('--last-month', action='store_true', help='Run for the last calendar month.')
    parser.add_argument('--months', type=int, default=16)
    args = parser.parse_args()
    
    # Standardise date args
    start_date, end_date = parse_standard_date_args(args)
    
    service = get_gsc_service()
    if service:
        # We use end_date as the anchor for the 16-month lookback
        run_report(service, args.site_url, args.months, anchor_end_date=end_date)
