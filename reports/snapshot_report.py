"""
Generates a single-period performance snapshot for a Google Search Console property.
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

def create_snapshot_html_report(page_title, period_str, summary_df, df_top_clicks, df_top_impressions, df_low_ctr, df_devices, df_countries):
    """Generates an HTML report from the snapshot analysis dataframes."""
    
    # Format and convert summary DataFrame to HTML
    summary_df['Clicks'] = summary_df['Clicks'].apply(lambda x: f"{int(x):,}")
    summary_df['Impressions'] = summary_df['Impressions'].apply(lambda x: f"{int(x):,}")
    summary_df['CTR'] = summary_df['CTR'].apply(lambda x: f"{x:.2%}")
    summary_df['Position'] = summary_df['Position'].apply(lambda x: f"{x:.2f}")
    summary_table_html = summary_df.to_html(classes="table table-striped table-hover", index=False, border=0, table_id="summary-table")


    # Helper to convert dataframe to HTML table with Bootstrap classes
    def df_to_html(df, table_id, float_format="%.2f"):
        if df.empty:
            return "<p>No data available for this section.</p>"
        
        df = df.copy()
        # Custom styling for CTR and Position columns
        if 'ctr' in df.columns:
            df['ctr'] = df['ctr'].apply(lambda x: f"{x:.2%}")
        if 'position' in df.columns:
            df['position'] = df['position'].apply(lambda x: f"{x:.2f}")

        # Add formatting for clicks and impressions
        for col in df.columns:
            if 'clicks' in col or 'impressions' in col:
                # Ensure the column is numeric before formatting
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
                df[col] = df[col].apply(lambda x: f"{int(x):,}") # Format as integer with commas

        return df.to_html(classes="table table-striped table-hover", index=False, table_id=table_id, border=0, float_format=float_format)

    html_template = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{page_title}</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body {{ padding: 2rem; }}
        .table-responsive {{ max-height: 500px; overflow-y: auto; }}
        h2 {{ border-bottom: 2px solid #dee2e6; padding-bottom: 0.5rem; margin-top: 2rem; }}
        footer {{ margin-top: 3rem; text-align: center; color: #6c757d; }}
        .table thead th {{ text-align: center; }}
        #summary-table th, #summary-table td {{ text-align: left; }}
    </style>
</head>
<body>
    <div class="container-fluid">
        <h1 class="mb-3">{page_title}</h1>
        <p class="text-muted">Analysis for the period: {period_str}</p>

        <h2>Overall Performance Summary</h2>
        <div class="table-responsive">
            {summary_table_html}
        </div>

        <h2>Top Pages by Clicks</h2>
        <p class="text-muted">The pages driving the most organic clicks during this period.</p>
        <div class="table-responsive">
            {df_to_html(df_top_clicks, 'table-top-clicks')}
        </div>

        <h2>Top Pages by Impressions</h2>
        <p class="text-muted">The pages with the highest visibility in search results during this period.</p>
        <div class="table-responsive">
            {df_to_html(df_top_impressions, 'table-top-impressions')}
        </div>

        <h2>High Impressions, Low CTR Opportunities</h2>
        <p class="text-muted">These pages are displayed frequently in search results but receive relatively few clicks.</p>
        <div class="table-responsive">
            {df_to_html(df_low_ctr, 'table-low-ctr')}
        </div>

        <h2>Performance by Device</h2>
        <p class="text-muted">Breakdown of organic search performance across different device types.</p>
        <div class="table-responsive">
            {df_to_html(df_devices, 'table-devices')}
        </div>

        <h2>Performance by Country</h2>
        <p class="text-muted">Breakdown of organic search performance by country, indicating where your audience is located.</p>
        <div class="table-responsive">
            {df_to_html(df_countries, 'table-countries')}
        </div>
        
    </div>

    <footer>
        <p>Report generated on {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}. <a href="https://github.com/liamdelahunty/gsc-exporter" target="_blank">gsc-exporter</a></p>
    </footer>
</body>
</html>
"""
    return html_template

def run_report(service, site_url, start_date, end_date):
    """Executes the snapshot report."""
    print(f"Running Snapshot Report for {site_url} ({start_date} to {end_date})...")

    # Fetch data for different dimensions
    df_pages = fetch_with_cache(service, site_url, start_date, end_date, ['page'], 'web')
    df_devices = fetch_with_cache(service, site_url, start_date, end_date, ['device'], 'web')
    df_countries = fetch_with_cache(service, site_url, start_date, end_date, ['country'], 'web')

    if df_pages.empty:
        print("No page data found.")
        return None

    # --- Analysis for HTML Observations ---
    total_clicks = df_pages['clicks'].sum()
    total_impressions = df_pages['impressions'].sum()
    average_ctr = total_clicks / total_impressions if total_impressions > 0 else 0
    weighted_position_sum = (df_pages['position'] * df_pages['impressions']).sum()
    average_position = weighted_position_sum / total_impressions if total_impressions > 0 else 0
    
    summary_df = pd.DataFrame([{
        'Clicks': total_clicks,
        'Impressions': total_impressions,
        'CTR': average_ctr,
        'Position': average_position
    }])

    # Top pages
    df_top_clicks = df_pages.sort_values(by='clicks', ascending=False).head(20)
    df_top_impressions = df_pages.sort_values(by='impressions', ascending=False).head(20)
    
    # Low CTR
    df_low_ctr = df_pages[
        (df_pages['impressions'] >= 1000) & (df_pages['ctr'] < 0.01)
    ].sort_values(by='impressions', ascending=False).head(20)

    # Output paths
    output_dir = get_output_dir(site_url)
    os.makedirs(output_dir, exist_ok=True)
    slug = get_filename_slug(site_url)
    
    base_file_prefix = f"snapshot-{slug}-{start_date}-to-{end_date}"
    html_path = os.path.join(output_dir, f"{base_file_prefix}-report.html")

    # Generate and save HTML
    html_content = create_snapshot_html_report(
        page_title=f"Performance Snapshot for {site_url}",
        period_str=f"{start_date} to {end_date}",
        summary_df=summary_df,
        df_top_clicks=df_top_clicks,
        df_top_impressions=df_top_impressions,
        df_low_ctr=df_low_ctr,
        df_devices=df_devices,
        df_countries=df_countries
    )
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
        
    print(f"Report completed: {html_path}")
    return html_path

if __name__ == '__main__':
    import argparse
    from core.client import get_gsc_service
    
    parser = argparse.ArgumentParser(description='Generate a performance snapshot.')
    parser.add_argument('site_url', help='The URL of the site to analyse.')
    parser.add_argument('--start-date', help='Start date (YYYY-MM-DD).')
    parser.add_argument('--end-date', help='End date (YYYY-MM-DD).')
    parser.add_argument('--last-month', action='store_true', help='Run for the last calendar month.')
    
    args = parser.parse_args()
    
    if args.last_month:
        today = date.today()
        # Last month
        end_date_dt = today.replace(day=1) - relativedelta(days=1)
        start_date_dt = end_date_dt.replace(day=1)
        
        start_date = start_date_dt.strftime('%Y-%m-%d')
        end_date = end_date_dt.strftime('%Y-%m-%d')
    else:
        start_date = args.start_date
        end_date = args.end_date
    
    if not start_date or not end_date:
        print("Error: Either provide --start-date and --end-date, or use --last-month.")
        sys.exit(1)
        
    service = get_gsc_service()
    if service:
        run_report(service, args.site_url, start_date, end_date)
