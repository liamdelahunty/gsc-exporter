import os
import sys
import pandas as pd
import numpy as np
import argparse
from datetime import date, datetime, timedelta

# Add parent directory to sys.path to allow importing core
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.naming import get_output_dir, get_filename_slug
from core.cache import fetch_with_cache
from core.client import get_gsc_service

def _segment_queries(df):
    """Segments queries into position buckets."""
    bins = [0, 3.49, 10.49, 20.49, np.inf]
    labels = ['Positions 1-3', 'Positions 4-10', 'Positions 11-20', 'Positions 21+']
    df['position_segment'] = pd.cut(df['position'], bins=bins, labels=labels)
    return df

def create_html_report(df, report_title, period_str):
    """Generates an HTML report from the DataFrame."""
    df_html = df.copy()

    # Format numeric columns
    df_html['clicks'] = pd.to_numeric(df_html['clicks'], errors='coerce').fillna(0).apply(lambda x: f"{x:,.0f}")
    df_html['impressions'] = pd.to_numeric(df_html['impressions'], errors='coerce').fillna(0).apply(lambda x: f"{x:,.0f}")
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

def run_report(service, site_url, start_date=None, end_date=None):
    """
    Runs the query segmentation report.
    """
    if not start_date or not end_date:
        today = date.today()
        first_day_current_month = today.replace(day=1)
        last_day_last_month = first_day_current_month - timedelta(days=1)
        start_date = last_day_last_month.replace(day=1).strftime('%Y-%m-%d')
        end_date = last_day_last_month.strftime('%Y-%m-%d')

    print(f"Running query segmentation report for {site_url} ({start_date} to {end_date})")
    
    # 1. Fetch data
    df = fetch_with_cache(service, site_url, start_date, end_date, dimensions=['query'])
    
    if df.empty:
        print("No data found.")
        return

    # 2. Segment data
    df = _segment_queries(df)
    
    # 3. Save output
    output_dir = get_output_dir(site_url)
    os.makedirs(output_dir, exist_ok=True)
    slug = get_filename_slug(site_url)
    
    csv_path = os.path.join(output_dir, f"query-segmentation-{slug}-{start_date}-to-{end_date}.csv")
    html_path = os.path.join(output_dir, f"query-segmentation-{slug}-{start_date}-to-{end_date}.html")
    
    df.to_csv(csv_path, index=False, encoding='utf-8')
    
    # Save HTML
    html_content = create_html_report(
        df,
        f"Query Segmentation Report: {site_url}",
        f"{start_date} to {end_date}"
    )
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(html_content)

    print(f"CSV saved to: {csv_path}")
    print(f"HTML saved to: {html_path}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Run query segmentation analysis.')
    parser.add_argument('site_url', help='The URL of the site to analyse.')
    parser.add_argument('--start-date', help='Start date (YYYY-MM-DD).')
    parser.add_argument('--end-date', help='End date (YYYY-MM-DD).')
    parser.add_argument('--last-month', action='store_true', help='Run for the last calendar month.')
    
    args = parser.parse_args()
    
    if args.last_month:
        today = date.today()
        first_day_current_month = today.replace(day=1)
        last_day_last_month = first_day_current_month - timedelta(days=1)
        start_date = last_day_last_month.replace(day=1).strftime('%Y-%m-%d')
        end_date = last_day_last_month.strftime('%Y-%m-%d')
    else:
        start_date = args.start_date
        end_date = args.end_date
        
    if not start_date or not end_date:
        print("Error: Either provide --start-date and --end-date, or use --last-month.")
        sys.exit(1)
        
    service = get_gsc_service()
    if service:
        run_report(service, args.site_url, start_date, end_date)
