import os
import sys
import pandas as pd
from functools import reduce
import argparse
from datetime import date, datetime, timedelta

# Add parent directory to sys.path to allow importing core
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.naming import get_output_dir, get_filename_slug
from core.cache import fetch_with_cache
from core.client import get_gsc_service

SEARCH_TYPES = ['web', 'image', 'video', 'news', 'discover', 'googleNews']

def create_html_report(df, report_title, period_str):
    """Generates an HTML report from the DataFrame."""
    df_html = df.copy()

    # Format numeric columns
    for col in df_html.columns:
        if any(suffix in col for suffix in ['_clicks', '_impressions']):
            df_html[col] = pd.to_numeric(df_html[col], errors='coerce').fillna(0).apply(lambda x: f"{x:,.0f}")
        elif '_ctr' in col:
            df_html[col] = pd.to_numeric(df_html[col], errors='coerce').fillna(0).apply(lambda x: f"{x:.2%}")
        elif '_position' in col:
            df_html[col] = pd.to_numeric(df_html[col], errors='coerce').fillna(0).apply(lambda x: f"{x:.2f}")

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

def run_report(service, site_url, start_date, end_date):
    """
    Runs the search type performance report.
    """
    print(f"Running search type performance report for {site_url} ({start_date} to {end_date})")
    
    all_data_dfs = []
    
    # 1. Fetch data for each search type
    for st in SEARCH_TYPES:
        df = fetch_with_cache(service, site_url, start_date, end_date, dimensions=['date'], search_type=st)
        
        if not df.empty:
            # Rename columns to include search type
            rename_dict = {
                'clicks': f'{st}_clicks',
                'impressions': f'{st}_impressions',
                'ctr': f'{st}_ctr',
                'position': f'{st}_position'
            }
            df.rename(columns=rename_dict, inplace=True)
            all_data_dfs.append(df)
    
    if not all_data_dfs:
        print("No data found.")
        return

    # 2. Merge data
    merged_df = reduce(lambda left, right: pd.merge(left, right, on='date', how='outer'), all_data_dfs)
    merged_df.fillna(0, inplace=True)
    merged_df = merged_df.sort_values('date', ascending=False)
    
    # 3. Save output
    output_dir = get_output_dir(site_url)
    os.makedirs(output_dir, exist_ok=True)
    slug = get_filename_slug(site_url)
    
    csv_path = os.path.join(output_dir, f"search-type-performance-{slug}-{start_date}-to-{end_date}.csv")
    html_path = os.path.join(output_dir, f"search-type-performance-{slug}-{start_date}-to-{end_date}.html")
    
    merged_df.to_csv(csv_path, index=False, encoding='utf-8')
    
    # Save HTML
    html_content = create_html_report(
        merged_df,
        f"Search Type Performance: {site_url}",
        f"{start_date} to {end_date}"
    )
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(html_content)

    print(f"CSV saved to: {csv_path}")
    print(f"HTML saved to: {html_path}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Run search type performance analysis.')
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
