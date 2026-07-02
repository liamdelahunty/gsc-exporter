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
from core.date_utils import parse_standard_date_args

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

def run_report(service, site_url, start_date=None, end_date=None, months=None):
    """
    Runs the queries and pages analysis report.
    """
    if start_date and end_date and not months:
        # Standard date range mode
        print(f"Running queries/pages analysis for {site_url} ({start_date} to {end_date})")
        df = fetch_with_cache(service, site_url, start_date, end_date, dimensions=['query', 'page'])
        if df.empty:
            print(f"No data found for {site_url}")
            return

        summary_data = {
            'period': f"{start_date} to {end_date}",
            'clicks': df['clicks'].sum(),
            'impressions': df['impressions'].sum(),
            'queries': df['query'].nunique(),
            'pages': df['page'].nunique(),
            'ctr': df['clicks'].sum() / df['impressions'].sum() if df['impressions'].sum() > 0 else 0,
            'position': df['position'].mean()
        }
        df_final = pd.DataFrame([summary_data])
        display_range = f"{start_date} to {end_date}"
    else:
        # Historical monthly mode
        months = months or 16
        print(f"Running monthly queries/pages analysis for {site_url} ({months} months ending {end_date})")
        
        all_monthly_data = []
        base_end_dt = datetime.strptime(end_date, '%Y-%m-%d')

        # Fetch data for each of the last N months
        first_of_end_month = base_end_dt.replace(day=1)
        for i in range(months):
            month_dt = first_of_end_month - relativedelta(months=i)
            m_start = month_dt.strftime('%Y-%m-01')
            
            import calendar
            last_day = calendar.monthrange(month_dt.year, month_dt.month)[1]
            m_end = f"{month_dt.year:04d}-{month_dt.month:02d}-{last_day:02d}"
            if i == 0:
                m_end = end_date # Respect exact end_date for the target month
            
            print(f"  - Fetching data for {month_dt.strftime('%Y-%m')}...")
            
            df = fetch_with_cache(service, site_url, m_start, m_end, dimensions=['query', 'page'])
            
            if not df.empty:
                monthly_totals = {
                    'period': month_dt.strftime('%Y-%m'),
                    'clicks': df['clicks'].sum(),
                    'impressions': df['impressions'].sum(),
                    'queries': df['query'].nunique(),
                    'pages': df['page'].nunique(),
                    'ctr': df['clicks'].sum() / df['impressions'].sum() if df['impressions'].sum() > 0 else 0,
                    'position': df['position'].mean()
                }
                all_monthly_data.append(monthly_totals)
        
        if not all_monthly_data:
            print(f"No data found for {site_url}")
            return
            
        df_final = pd.DataFrame(all_monthly_data)
        df_final = df_final.sort_values(by='period', ascending=False)
        display_range = f"{df_final['period'].min()} to {df_final['period'].max()}"

    # Save output
    output_dir = get_output_dir(site_url)
    os.makedirs(output_dir, exist_ok=True)
    slug = get_filename_slug(site_url)
    
    file_prefix = f"queries-pages-analysis-{slug}-{end_date}"
    csv_path = os.path.join(output_dir, f"{file_prefix}.csv")
    html_path = os.path.join(output_dir, f"{file_prefix}.html")
    
    df_final.to_csv(csv_path, index=False, encoding='utf-8')
    
    # Save HTML
    html_content = create_html_report(
        df_final,
        f"Queries and Pages Analysis: {site_url}",
        display_range
    )
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(html_content)

    print(f"CSV saved to: {csv_path}")
    print(f"HTML saved to: {html_path}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Run queries and pages analysis.')
    parser.add_argument('site_url', help='The URL of the site to analyse.')
    parser.add_argument('--months', type=int, help='Number of months to analyse for historical report.')
    
    parser.add_argument('--start-date', help='Start date (YYYY-MM-DD).')
    parser.add_argument('--end-date', help='End date (YYYY-MM-DD).')
    parser.add_argument('--last-7-days', action='store_true', help='Run for the last 7 available days.')
    parser.add_argument('--last-month', action='store_true', help='Run for the last calendar month.')
    
    args = parser.parse_args()
    
    service = get_gsc_service()
    if service:
        start_date, end_date = parse_standard_date_args(args, service, args.site_url)
        # If the user explicitly provided --months, we do the historical report.
        # Otherwise, if they used --last-7-days or explicit dates, we do a single period report.
        run_report(service, args.site_url, start_date=start_date, end_date=end_date, months=args.months)

