"""
Generates a report identifying queries with "out of the ordinary" traffic spikes.
Adapted for the modular GSC Exporter.
"""
import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pandas as pd
import numpy as np
from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta
from core.naming import get_output_dir, get_filename_slug
from core.cache import fetch_with_cache
from core.date_utils import parse_standard_date_args, get_month_range_lookback

def create_report_html(spikes_df, report_title, site_url, months_count):
    """Generates the HTML report for spikes."""
    if spikes_df.empty:
        return f"<html><head><title>{report_title}</title></head><body><h1>{report_title}</h1><p>No spikes detected.</p></body></html>"

    display_df = spikes_df.copy()
    display_df['clicks'] = display_df['clicks'].apply(lambda x: f"{x:,}")
    display_df['impressions'] = display_df['impressions'].apply(lambda x: f"{x:,}")
    display_df['avg_clicks'] = display_df['avg_clicks'].apply(lambda x: f"{x:,.2f}")
    display_df['avg_impressions'] = display_df['avg_impressions'].apply(lambda x: f"{x:,.2f}")
    display_df['clicks_z_score'] = display_df['clicks_z_score'].apply(lambda x: f"{x:.2f}" if not pd.isna(x) else "N/A")
    display_df['impressions_z_score'] = display_df['impressions_z_score'].apply(lambda x: f"{x:.2f}" if not pd.isna(x) else "N/A")

    table_html = display_df.to_html(classes="table table-striped table-hover", index=False, border=0)
    
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
        h1 {{ border-bottom: 2px solid #dee2e6; padding-bottom: .5rem; margin-bottom: 1rem; }}
        .table thead th {{ background-color: #434343; color: #ffffff; text-align: left; }}
        footer {{ margin-top: 3rem; text-align: center; color: #6c757d; }}
    </style>
</head>
<body>
    <div class="container-fluid">
        <h1>{report_title}</h1>
        <p class="lead">Seasonal analysis identifying queries with traffic significantly higher than their historical average (analyzing last {months_count} months).</p>
        <p class="text-muted">Domain: {site_url}</p>
        <div class="table-responsive">
            {table_html}
        </div>
    </div>
    <footer><p>Report generated on {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}. <a href="https://github.com/liamdelahunty/gsc-exporter" target="_blank">gsc-exporter</a></p></footer>
</body>
</html>
"""

def run_report(service, site_url, start_date, end_date, threshold=2.0, min_clicks=10):
    """Executes the seasonal query spike report."""
    print(f"Running Seasonal Query Spike Report for {site_url} (target: {end_date}, threshold {threshold})...")
    
    all_data_frames = []
    end_dt = datetime.strptime(end_date, '%Y-%m-%d')
    
    for i in range(16):
        month_dt = end_dt - relativedelta(months=i)
        month_str = month_dt.strftime('%Y-%m')
        
        # Calculate start and end date for the month
        m_start = month_dt.replace(day=1).strftime('%Y-%m-%d')
        m_end = (month_dt + relativedelta(months=1) - timedelta(days=1)).strftime('%Y-%m-%d')
        if i == 0:
            m_end = end_date
        
        # Use core cache
        df_month = fetch_with_cache(service, site_url, m_start, m_end, ['query'], 'web')
        
        if df_month is not None and not df_month.empty:
            df_month['month'] = month_str
            df_month = df_month[['month', 'query', 'clicks', 'impressions']]
            all_data_frames.append(df_month)

    if not all_data_frames:
        print("No data found.")
        return None

    df = pd.concat(all_data_frames, ignore_index=True)
    
    stats = df.groupby('query').agg({
        'clicks': ['mean', 'std', 'count'],
        'impressions': ['mean', 'std']
    })
    stats.columns = ['_'.join(col).strip() for col in stats.columns.values]
    stats = stats.reset_index()

    df = df.merge(stats, on='query')

    df['clicks_z_score'] = (df['clicks'] - df['clicks_mean']) / df['clicks_std'].replace(0, np.nan)
    df['impressions_z_score'] = (df['impressions'] - df['impressions_mean']) / df['impressions_std'].replace(0, np.nan)

    is_spike = (
        ((df['clicks_z_score'] > threshold) | (df['impressions_z_score'] > threshold)) &
        (df['clicks'] >= min_clicks)
    )
    
    spikes = df[is_spike].copy()
    spikes['max_z'] = spikes[['clicks_z_score', 'impressions_z_score']].max(axis=1)
    spikes = spikes.sort_values(by=['month', 'max_z'], ascending=[False, False])

    report_df = spikes[[
        'month', 'query', 'clicks', 'clicks_mean', 'clicks_z_score', 
        'impressions', 'impressions_mean', 'impressions_z_score'
    ]]
    report_df = report_df.rename(columns={
        'clicks_mean': 'avg_clicks',
        'impressions_mean': 'avg_impressions'
    })

    # Paths
    output_dir = get_output_dir(site_url)
    os.makedirs(output_dir, exist_ok=True)
    slug = get_filename_slug(site_url)
    
    file_prefix = f"seasonal-query-spikes-{slug}-{start_date}-to-{end_date}"
    csv_path = os.path.join(output_dir, f"{file_prefix}.csv")
    html_path = os.path.join(output_dir, f"{file_prefix}.html")
    
    report_df.to_csv(csv_path, index=False, encoding='utf-8')
    
    report_title = f"Seasonal Query Spikes Report: {site_url}"
    html_content = create_report_html(report_df, report_title, site_url, 16)
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
        
    print(f"CSV saved to: {csv_path}")
    print(f"HTML saved to: {html_path}")
    return html_path

if __name__ == '__main__':
    import argparse
    from core.client import get_gsc_service
    
    parser = argparse.ArgumentParser(description='Identify seasonal queries with traffic spikes.')
    parser.add_argument('site_url', help='The GSC site URL')
    parser.add_argument('--start-date', help='Start date (YYYY-MM-DD).')
    parser.add_argument('--end-date', help='End date (YYYY-MM-DD).')
    parser.add_argument('--last-month', action='store_true', help='Run for the last calendar month.')
    parser.add_argument('--threshold', type=float, default=2.0, help='Z-score threshold.')
    parser.add_argument('--min-clicks', type=int, default=10, help='Minimum clicks.')
    
    args = parser.parse_args()
    start_date, end_date = parse_standard_date_args(args)
    
    service = get_gsc_service()
    if service:
        run_report(service, args.site_url, start_date, end_date, args.threshold, args.min_clicks)
