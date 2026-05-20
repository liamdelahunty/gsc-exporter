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
    """Generates an HTML report from the DataFrame."""
    df_html = df.copy()

    # Format numeric columns
    df_html['clicks'] = pd.to_numeric(df_html['clicks'], errors='coerce').fillna(0).apply(lambda x: f"{x:,.0f}")
    df_html['impressions'] = pd.to_numeric(df_html['impressions'], errors='coerce').fillna(0).apply(lambda x: f"{x:,.0f}")
    df_html['queries'] = pd.to_numeric(df_html['queries'], errors='coerce').fillna(0).apply(lambda x: f"{x:,.0f}")
    df_html['pages'] = pd.to_numeric(df_html['pages'], errors='coerce').fillna(0).apply(lambda x: f"{x:,.0f}")
    df_html['ctr'] = pd.to_numeric(df_html['ctr'], errors='coerce').fillna(0).apply(lambda x: f"{x:.2%}")
    df_html['position'] = pd.to_numeric(df_html['position'], errors='coerce').fillna(0).apply(lambda x: f"{x:.2f}")

    table_html = df_html.to_html(classes="table table-striped table-hover", index=False, border=0)

    return f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{report_title}</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body {{ padding: 2rem; background-color: #f8f9fa; }}
        h1 {{ border-bottom: 2px solid #dee2e6; padding-bottom: .5rem; }}
        .table-responsive {{ margin-top: 2rem; }}
        footer {{ margin-top: 3rem; text-align: center; color: #6c757d; }}
    </style>
</head>
<body>
    <div class="container-fluid">
        <h1>{report_title}</h1>
        <p class="text-muted">Analysis period: {period_str}</p>
        <div class="table-responsive">
            {table_html}
        </div>
    </div>
    <footer>
        <p>Report generated on {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}. <a href="https://github.com/liamdelahunty/gsc-exporter" target="_blank">gsc-exporter</a></p>
    </footer>
</body>
</html>
"""

def run_report(service, site_url, months=16):
    """
    Runs the queries and pages analysis report.
    """
    print(f"Running queries/pages analysis for {site_url}")
    
    today = date.today()
    all_monthly_data = []

    # Fetch data for each of the last N months
    for i in range(1, months + 1):
        end_of_month = today.replace(day=1) - relativedelta(months=i - 1) - timedelta(days=1)
        start_of_month = end_of_month.replace(day=1)
        start_date = start_of_month.strftime('%Y-%m-%d')
        end_date = end_of_month.strftime('%Y-%m-%d')
        
        print(f"  - Fetching data for {start_of_month.strftime('%Y-%m')}...")
        
        # Use core.cache.fetch_with_cache to get data grouped by query/page
        df = fetch_with_cache(service, site_url, start_date, end_date, dimensions=['query', 'page'])
        
        if not df.empty:
            # Aggregate stats for the month
            monthly_totals = {
                'month': start_of_month.strftime('%Y-%m'),
                'clicks': df['clicks'].sum(),
                'impressions': df['impressions'].sum(),
                'queries': df['query'].nunique(),
                'pages': df['page'].nunique(),
                'ctr': df['clicks'].sum() / df['impressions'].sum() if df['impressions'].sum() > 0 else 0,
                'position': df['position'].mean()
            }
            all_monthly_data.append(monthly_totals)
    
    # Save output
    if all_monthly_data:
        df_final = pd.DataFrame(all_monthly_data)
        output_dir = get_output_dir(site_url)
        os.makedirs(output_dir, exist_ok=True)
        slug = get_filename_slug(site_url)
        
        csv_path = os.path.join(output_dir, f"queries-pages-analysis-{slug}-historical.csv")
        html_path = os.path.join(output_dir, f"queries-pages-analysis-{slug}-historical.html")
        
        df_final.to_csv(csv_path, index=False, encoding='utf-8')
        
        # Save HTML
        start_month = df_final['month'].min()
        end_month = df_final['month'].max()
        html_content = create_html_report(
            df_final,
            f"Queries and Pages Analysis: {site_url}",
            f"{start_month} to {end_month}"
        )
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(html_content)

        print(f"CSV saved to: {csv_path}")
        print(f"HTML saved to: {html_path}")
    else:
        print(f"No data found for {site_url}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Run queries and pages analysis.')
    parser.add_argument('site_url', help='The URL of the site to analyse.')
    parser.add_argument('--months', type=int, default=16, help='Number of months to analyse.')
    
    # Accept but ignore start/end date for compatibility with batch runner
    parser.add_argument('--start-date', help=argparse.SUPPRESS)
    parser.add_argument('--end-date', help=argparse.SUPPRESS)
    
    args = parser.parse_args()
    
    service = get_gsc_service()
    if service:
        run_report(service, args.site_url, args.months)
