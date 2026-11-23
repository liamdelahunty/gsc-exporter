"""
Performs analysis of Google Search Console data, gathering key performance metrics on a monthly or weekly basis.
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
from core.date_utils import parse_standard_date_args, get_latest_available_date

def create_single_site_html_report(df, report_title, full_period_str, label_col='month', sort_col='month_date'):
    """Generates a simplified HTML report for a single site, including a chart."""
    df_table = df.copy()
    cols_to_drop = [c for c in ['month_date', 'week_start', 'week_end', 'sort_col'] if c in df_table.columns]
    if cols_to_drop:
        df_table = df_table.drop(columns=cols_to_drop)
    
    df_table['clicks'] = df_table['clicks'].apply(lambda x: f"{x:,.0f}")
    df_table['impressions'] = df_table['impressions'].apply(lambda x: f"{x:,.0f}")
    df_table['ctr'] = df_table['ctr'].apply(lambda x: f"{x:.2%}")
    df_table['position'] = df_table['position'].apply(lambda x: f"{x:.2f}")
    
    report_body = df_table.to_html(classes="table table-striped table-hover", index=False, border=0)
    if sort_col and sort_col in df.columns:
        chart_data = df.sort_values(by=sort_col).to_json(orient='records', date_format='iso')
    else:
        chart_data = df.sort_values(by=label_col).to_json(orient='records', date_format='iso')

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
    const labels = data.map(row => row['{label_col}']);

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

def run_report(service, site_url, months=16, anchor_end_date=None, weekly=False, weeks=4):
    """Executes the Key Performance Metrics report."""
    if weekly:
        print(f"Running Weekly Key Performance Metrics for {site_url} ({weeks} weeks)...")
        
        # 1. Date Range: Complete weeks ending on the most recent completed Sunday
        if anchor_end_date:
            if isinstance(anchor_end_date, str):
                anchor_dt = datetime.strptime(anchor_end_date, '%Y-%m-%d').date()
            elif isinstance(anchor_end_date, datetime):
                anchor_dt = anchor_end_date.date()
            else:
                anchor_dt = anchor_end_date
        else:
            anchor_dt = get_latest_available_date(service, site_url)
            if isinstance(anchor_dt, datetime):
                anchor_dt = anchor_dt.date()
                
        # Calculate most recent completed Sunday on or before anchor_dt
        # Python weekday(): Monday=0, ..., Sunday=6
        days_since_sunday = (anchor_dt.weekday() + 1) % 7
        end_sunday = anchor_dt - timedelta(days=days_since_sunday)
        start_monday = end_sunday - timedelta(days=(weeks * 7) - 1)
        
        start_date = start_monday.strftime('%Y-%m-%d')
        end_date = end_sunday.strftime('%Y-%m-%d')
        
        # 2. Fetch Data (Aggregated by date for site-wide metrics)
        df = fetch_with_cache(service, site_url, start_date, end_date, ['date'])
        
        if df.empty:
            print("No data found.")
            return None
            
        # 3. Process to Weekly
        df['date'] = pd.to_datetime(df['date'])
        # Assign each date to its week starting on Monday (Week Commencing from-date only)
        df['week_start'] = df['date'].apply(lambda d: d - timedelta(days=d.weekday()))
        df['Week Commencing'] = df['week_start'].dt.strftime('%Y-%m-%d')
        
        weekly_df = df.groupby(['Week Commencing', 'week_start']).agg({
            'clicks': 'sum',
            'impressions': 'sum',
            'position': 'mean'
        }).reset_index()
        
        weekly_df['ctr'] = weekly_df['clicks'] / weekly_df['impressions']
        # Sort descending by week_start (newest week first in table)
        weekly_df = weekly_df.sort_values('week_start', ascending=False)
        
        # 4. Output Paths
        output_dir = get_output_dir(site_url)
        os.makedirs(output_dir, exist_ok=True)
        slug = get_filename_slug(site_url)
        
        file_prefix = f"key-metrics-weekly-{slug}-{start_date}-{end_date}"
        csv_path = os.path.join(output_dir, f"{file_prefix}.csv")
        html_path = os.path.join(output_dir, f"{file_prefix}.html")
        
        # 5. Save and Generate
        csv_df = weekly_df.drop(columns=['week_start'], errors='ignore')
        csv_df.to_csv(csv_path, index=False, encoding='utf-8')
        
        full_period_str = f"Weekly breakdown ({weeks} weeks) from {start_date} to {end_date}"
        html_content = create_single_site_html_report(
            weekly_df, site_url, full_period_str, label_col='Week Commencing', sort_col='week_start'
        )
        
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
            
        print(f"CSV saved to: {csv_path}")
        print(f"HTML saved to: {html_path}")
        return html_path

    # Standard Monthly Report
    print(f"Running Key Performance Metrics for {site_url} ({months} months)...")
    
    # 1. Date Range
    if anchor_end_date:
        if isinstance(anchor_end_date, str):
            end_date_dt = datetime.strptime(anchor_end_date, '%Y-%m-%d').date()
        elif isinstance(anchor_end_date, datetime):
            end_date_dt = anchor_end_date.date()
        else:
            end_date_dt = anchor_end_date
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
    html_content = create_single_site_html_report(
        monthly_df, site_url, full_period_str, label_col='month', sort_col='month_date'
    )
    
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
    parser.add_argument('--last-7-days', action='store_true', help='Run for the last 7 available days.')
    parser.add_argument('--last-month', action='store_true', help='Run for the last calendar month.')
    parser.add_argument('--months', type=int, default=16, help='Number of months for monthly report, defaulting to 16.')
    parser.add_argument('--weekly', action='store_true', help='Run report on a weekly basis with weeks starting on Monday.')
    parser.add_argument('--weeks', type=int, default=None, help='Number of weeks for weekly report, defaulting to 4. Automatically enables weekly mode.')
    args = parser.parse_args()
    
    is_weekly = args.weekly or (args.weeks is not None)
    weeks = args.weeks if args.weeks is not None else 4
    
    service = get_gsc_service()
    if service:
        if is_weekly:
            anchor = args.end_date
            if not anchor and (args.last_month or args.last_7_days):
                _, anchor = parse_standard_date_args(args, service, args.site_url)
            run_report(service, args.site_url, anchor_end_date=anchor, weekly=True, weeks=weeks)
        else:
            start_date, end_date = parse_standard_date_args(args, service, args.site_url)
            # We use end_date as the anchor for the 16-month lookback
            run_report(service, args.site_url, months=args.months, anchor_end_date=end_date)
