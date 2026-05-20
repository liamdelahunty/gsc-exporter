"""
Generates a seasonal performance report by comparing page-level data for the same month across multiple years.
Adapted for the modular GSC Exporter.
"""
import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pandas as pd
from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta
from core.naming import get_output_dir, get_filename_slug
from core.cache import fetch_with_cache

def create_seasonal_report_html(df, report_title, years_list):
    """Generates the HTML report for seasonal comparison."""
    
    display_df = df.copy()
    
    # Make URLs clickable and open in new window
    if 'page' in display_df.columns:
        display_df['page'] = display_df['page'].apply(lambda x: f'<a href="{x}" target="_blank" class="text-break">{x}</a>')

    table_html = display_df.to_html(classes="table table-striped table-hover", index=False, border=0, escape=False)
    
    return f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{report_title}</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body {{ padding: 2rem; }}
        h1 {{ border-bottom: 2px solid #dee2e6; padding-bottom: .5rem; margin-top: 2rem; }}
        .table thead th {{ background-color: #434343; color: #ffffff; text-align: left; }}
        .table td {{ word-wrap: break-word; min-width: 100px; max-width: 400px; }}
        .text-break {{ word-break: break-all !important; }}
        footer {{ margin-top: 3rem; text-align: center; color: #6c757d; }}
    </style>
</head>
<body>
    <div class="container-fluid">
        <h1>{report_title}</h1>
        <p>Comparing performance for the same month across years: {', '.join(map(str, years_list))}</p>
        <div class="table-responsive">
            {table_html}
        </div>
    </div>
    <footer><p>Report generated on {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}. <a href="https://github.com/liamdelahunty/gsc-exporter" target="_blank">gsc-exporter</a></p></footer>
</body>
</html>
"""

def run_report(service, site_url, month=None, years=3):
    """Executes the seasonal performance report."""
    if not month:
        # Default to last month
        today = date.today()
        target_month_date = today.replace(day=1) - timedelta(days=1)
        month = target_month_date.strftime('%Y-%m')

    print(f"Running Seasonal Performance Report for {site_url} for month {month} over {years} years...")

    target_dt = datetime.strptime(month, '%Y-%m')
    years_list = []
    all_years_data = []

    for i in range(years):
        year_dt = target_dt - relativedelta(years=i)
        year_str = year_dt.strftime('%Y-%m')
        
        # Calculate start and end date for the month
        start_date = year_dt.replace(day=1).strftime('%Y-%m-%d')
        end_date = (year_dt + relativedelta(months=1) - timedelta(days=1)).strftime('%Y-%m-%d')
        
        # Use core cache
        df_year = fetch_with_cache(service, site_url, start_date, end_date, ['page'], 'web')
        
        if df_year is not None and not df_year.empty:
            years_list.append(year_dt.year)
            cols_to_keep = ['page', 'clicks', 'impressions', 'ctr', 'position']
            df_year = df_year[[c for c in cols_to_keep if c in df_year.columns]]
            
            df_year = df_year.rename(columns={
                'clicks': f'clicks_{year_dt.year}',
                'impressions': f'impressions_{year_dt.year}',
                'ctr': f'ctr_{year_dt.year}',
                'position': f'position_{year_dt.year}'
            })
            all_years_data.append(df_year)

    if not all_years_data:
        print("No data found for any of the years.")
        return None

    merged_df = all_years_data[0]
    for df_next in all_years_data[1:]:
        merged_df = pd.merge(merged_df, df_next, on='page', how='outer')

    # Fill NaNs for clicks/impressions and convert to int
    for year in years_list:
        merged_df[f'clicks_{year}'] = merged_df[f'clicks_{year}'].fillna(0).astype(int)
        merged_df[f'impressions_{year}'] = merged_df[f'impressions_{year}'].fillna(0).astype(int)

    # Sort if possible
    if len(years_list) >= 2:
        curr_year = years_list[0]
        prev_year = years_list[1]
        if f'clicks_{curr_year}' in merged_df.columns and f'clicks_{prev_year}' in merged_df.columns:
            merged_df['clicks_diff'] = merged_df[f'clicks_{curr_year}'] - merged_df[f'clicks_{prev_year}']
            merged_df = merged_df.sort_values(by='clicks_diff', ascending=False)

    # Paths
    output_dir = os.path.join(get_output_dir(site_url), 'seasonal')
    os.makedirs(output_dir, exist_ok=True)
    
    file_prefix = f"seasonal-performance-report-{month}"
    csv_path = os.path.join(output_dir, f"{file_prefix}.csv")
    html_path = os.path.join(output_dir, f"{file_prefix}.html")
    
    merged_df.to_csv(csv_path, index=False, encoding='utf-8')
    
    report_title = f"Seasonal Performance Report: {target_dt.strftime('%B')} ({site_url})"
    html_content = create_seasonal_report_html(merged_df, report_title, years_list)
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
        
    print(f"CSV saved to: {csv_path}")
    print(f"HTML saved to: {html_path}")
    return html_path

if __name__ == '__main__':
    import argparse
    from core.client import get_gsc_service
    
    parser = argparse.ArgumentParser(description='Generate a seasonal performance report.')
    parser.add_argument('site_url', help='The URL of the site to analyse.')
    parser.add_argument('--month', help='The month to analyze in YYYY-MM format.')
    parser.add_argument('--years', type=int, default=3, help='Number of years to look back.')
    
    args = parser.parse_args()
    
    service = get_gsc_service()
    if service:
        run_report(service, args.site_url, args.month, args.years)
