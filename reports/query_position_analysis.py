import os
import sys
import pandas as pd
from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta
import argparse

# Add parent directory to sys.path to allow importing core
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.naming import get_output_dir, get_filename_slug
from core.cache import fetch_with_cache
from core.client import get_gsc_service

def create_html_report(df, report_title, period_str):
    """Generates an HTML report with Chart.js visualizations."""
    df_table = df.copy()
    # Format for table
    for col in df_table.columns:
        if ('clicks' in col or 'impressions' in col) and col != 'month':
            df_table[col] = df_table[col].apply(lambda x: f"{x:,.0f}")
    
    report_body = df_table.to_html(classes="table table-striped table-hover", index=False, border=0)
    chart_data = df.sort_values(by='month').to_json(orient='records')

    return f"""
<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Query Position Report for {report_title}</title><link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<style>body{{padding:2rem;background-color: #f8f9fa;}}h1,h2{{border-bottom:2px solid #dee2e6;padding-bottom:.5rem;margin-top:2rem;}}.table thead th {{background-color: #434343;color: #ffffff;text-align: left;}}footer{{margin-top:3rem;text-align:center;color:#6c757d;}}</style></head>
<body><div class="container-fluid"><h1>Query Position Report for {report_title}</h1>
<p class="text-muted">Analysis for the period: {period_str}</p>
<div class="row my-4">
    <div class="col-lg-6"><div class="card"><div class="card-header"><h3>Clicks by Position</h3></div><div class="card-body"><canvas id="clicksChart"></canvas></div></div></div>
    <div class="col-lg-6"><div class="card"><div class="card-header"><h3>Impressions by Position</h3></div><div class="card-body"><canvas id="impressionsChart"></canvas></div></div></div>
</div>
<div class="row my-4">
    <div class="col-lg-6"><div class="card"><div class="card-header"><h3>Total Clicks</h3></div><div class="card-body"><canvas id="totalClicksChart"></canvas></div></div></div>
    <div class="col-lg-6"><div class="card"><div class="card-header"><h3>Total Impressions</h3></div><div class="card-body"><canvas id="totalImpressionsChart"></canvas></div></div></div>
</div>
<h2>Data Table</h2>
<div class="table-responsive">{report_body}</div></div>
<footer><p>Report generated on {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}. <a href="https://github.com/liamdelahunty/gsc-exporter" target="_blank">gsc-exporter</a></p></footer>
<script>
    const data = {chart_data};
    const labels = data.map(row => row.month);
    const chartConfig = {{
        'clicks': {{
            'element': 'clicksChart',
            'datasets': [
                {{'label': 'Pos 1-3', 'data': data.map(row => row.clicks_pos_1_3), 'borderColor': 'rgba(75, 192, 192, 1)'}},
                {{'label': 'Pos 4-10', 'data': data.map(row => row.clicks_pos_4_10), 'borderColor': 'rgba(54, 162, 235, 1)'}},
                {{'label': 'Pos 11-20', 'data': data.map(row => row.clicks_pos_11_20), 'borderColor': 'rgba(255, 206, 86, 1)'}},
                {{'label': 'Pos 21+', 'data': data.map(row => row.clicks_pos_21_plus), 'borderColor': 'rgba(255, 99, 132, 1)'}}
            ]
        }},
        'impressions': {{
            'element': 'impressionsChart',
            'datasets': [
                {{'label': 'Pos 1-3', 'data': data.map(row => row.impressions_pos_1_3), 'borderColor': 'rgba(75, 192, 192, 1)'}},
                {{'label': 'Pos 4-10', 'data': data.map(row => row.impressions_pos_4_10), 'borderColor': 'rgba(54, 162, 235, 1)'}},
                {{'label': 'Pos 11-20', 'data': data.map(row => row.impressions_pos_11_20), 'borderColor': 'rgba(255, 206, 86, 1)'}},
                {{'label': 'Pos 21+', 'data': data.map(row => row.impressions_pos_21_plus), 'borderColor': 'rgba(255, 99, 132, 1)'}}
            ]
        }},
        'total_clicks': {{
            'element': 'totalClicksChart',
            'datasets': [
                {{'label': 'Total Clicks', 'data': data.map(row => row.total_clicks), 'borderColor': 'rgba(153, 102, 255, 1)'}}
            ]
        }},
        'total_impressions': {{
            'element': 'totalImpressionsChart',
            'datasets': [
                {{'label': 'Total Impressions', 'data': data.map(row => row.total_impressions), 'borderColor': 'rgba(255, 159, 64, 1)'}}
            ]
        }}
    }};
    for (const [key, config] of Object.entries(chartConfig)) {{
        new Chart(document.getElementById(config.element), {{
            type: 'line',
            data: {{
                labels: labels,
                datasets: config.datasets.map(ds => ({{...ds, fill: false, tension: 0.1}}))
            }},
            options: {{ scales: {{ y: {{ beginAtZero: true }} }} }}
        }});
    }}
</script>
</body></html>"""

def _process_df_into_distribution(df):
    """Processes DataFrame query data into aggregated position distribution."""
    distribution = {
        'clicks_pos_1_3': 0, 'impressions_pos_1_3': 0,
        'clicks_pos_4_10': 0, 'impressions_pos_4_10': 0,
        'clicks_pos_11_20': 0, 'impressions_pos_11_20': 0,
        'clicks_pos_21_plus': 0, 'impressions_pos_21_plus': 0,
        'total_clicks': df['clicks'].sum(), 'total_impressions': df['impressions'].sum()
    }
    
    # Position logic
    for _, row in df.iterrows():
        pos = row['position']
        clicks = row['clicks']
        imps = row['impressions']
        
        if 1 <= pos <= 3.49: # Handle inclusive range
            distribution['clicks_pos_1_3'] += clicks
            distribution['impressions_pos_1_3'] += imps
        elif 3.5 <= pos <= 10.49:
            distribution['clicks_pos_4_10'] += clicks
            distribution['impressions_pos_4_10'] += imps
        elif 10.5 <= pos <= 20.49:
            distribution['clicks_pos_11_20'] += clicks
            distribution['impressions_pos_11_20'] += imps
        elif pos >= 20.5:
            distribution['clicks_pos_21_plus'] += clicks
            distribution['impressions_pos_21_plus'] += imps
            
    return distribution

def run_report(service, site_url, months=16):
    """
    Runs the query position analysis report.
    """
    print(f"Running query position analysis for {site_url}")
    
    today = date.today()
    all_monthly_data = []

    # Fetch data for each of the last N months
    for i in range(1, months + 1):
        end_of_month = today.replace(day=1) - relativedelta(months=i - 1) - timedelta(days=1)
        start_of_month = end_of_month.replace(day=1)
        start_date = start_of_month.strftime('%Y-%m-%d')
        end_date = end_of_month.strftime('%Y-%m-%d')
        
        print(f"  - Fetching data for {start_of_month.strftime('%Y-%m')}...")
        
        # Use core.cache.fetch_with_cache grouped by query
        df = fetch_with_cache(service, site_url, start_date, end_date, dimensions=['query'])
        
        if not df.empty:
            distribution = _process_df_into_distribution(df)
            distribution['month'] = start_of_month.strftime('%Y-%m')
            all_monthly_data.append(distribution)
    
    # Save output
    if all_monthly_data:
        df_final = pd.DataFrame(all_monthly_data)
        output_dir = get_output_dir(site_url)
        os.makedirs(output_dir, exist_ok=True)
        csv_path = os.path.join(output_dir, "query-position-analysis-historical.csv")
        html_path = os.path.join(output_dir, "query-position-analysis-historical.html")
        df_final.to_csv(csv_path, index=False)
        
        # Generate HTML
        start_month = df_final['month'].min()
        end_month = df_final['month'].max()
        html_content = create_html_report(df_final, site_url, f"{start_month} to {end_month}")
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
            
        print(f"Report saved to {csv_path}")
        print(f"HTML report saved to {html_path}")
    else:
        print(f"No data found for {site_url}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Run query position analysis.')
    parser.add_argument('site_url', help='The URL of the site to analyse.')
    parser.add_argument('--months', type=int, default=16, help='Number of months to analyse.')
    
    # Accept but ignore start/end date for compatibility with batch runner
    parser.add_argument('--start-date', help=argparse.SUPPRESS)
    parser.add_argument('--end-date', help=argparse.SUPPRESS)
    
    args = parser.parse_args()
    
    service = get_gsc_service()
    if service:
        run_report(service, args.site_url, args.months)
