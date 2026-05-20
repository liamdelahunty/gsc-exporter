import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import pandas as pd
from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta
from jinja2 import Environment, FileSystemLoader
from core.naming import get_output_dir, get_filename_slug
from core.cache import fetch_with_cache

def generate_html_report(df, site_url, html_output_path):
    """Generates the HTML report."""
    start_month = df['month'].min()
    end_month = df['month'].max()

    styles = [dict(selector="td", props=[("text-align", "right")])]

    # Summary Calculations
    web_clicks = df['web_clicks'].sum()
    discover_clicks = df.get('discover_clicks', pd.Series([0])).sum()
    news_clicks = df.get('news_clicks', pd.Series([0])).sum()
    total_clicks = web_clicks + discover_clicks + news_clicks

    summary_clicks_rows = [
        {'Metric': 'Total', 'Web Clicks': f"{web_clicks:,.0f}", 'Discover Clicks': f"{discover_clicks:,.0f}", 'News Clicks': f"{news_clicks:,.0f}", 'Total': f"{total_clicks:,.0f}"},
        {'Metric': 'Percentage', 
         'Web Clicks': f"{(web_clicks/total_clicks*100):.2f}%" if total_clicks else '0%',
         'Discover Clicks': f"{(discover_clicks/total_clicks*100):.2f}%" if total_clicks else '0%',
         'News Clicks': f"{(news_clicks/total_clicks*100):.2f}%" if total_clicks else '0%',
         'Total': '100%'}
    ]
    clicks_summary_table = pd.DataFrame(summary_clicks_rows).style.set_table_attributes('class="table table-bordered table-sm"').set_table_styles(styles).hide(axis='index').to_html()

    web_imps = df['web_impressions'].sum()
    discover_imps = df.get('discover_impressions', pd.Series([0])).sum()
    news_imps = df.get('news_impressions', pd.Series([0])).sum()
    total_imps = web_imps + discover_imps + news_imps

    summary_imps_rows = [
        {'Metric': 'Total', 'Web Impressions': f"{web_imps:,.0f}", 'Discover Impressions': f"{discover_imps:,.0f}", 'News Impressions': f"{news_imps:,.0f}", 'Total': f"{total_imps:,.0f}"},
        {'Metric': 'Percentage',
         'Web Impressions': f"{(web_imps/total_imps*100):.2f}%" if total_imps else '0%',
         'Discover Impressions': f"{(discover_imps/total_imps*100):.2f}%" if total_imps else '0%',
         'News Impressions': f"{(news_imps/total_imps*100):.2f}%" if total_imps else '0%',
         'Total': '100%'}
    ]
    imps_summary_table = pd.DataFrame(summary_imps_rows).style.set_table_attributes('class="table table-bordered table-sm"').set_table_styles(styles).hide(axis='index').to_html()

    # Monthly Breakdown
    df_fmt = df.copy()
    # Ensure all search type columns exist for formatting
    for col in ['web_clicks', 'discover_clicks', 'news_clicks', 'total_clicks', 
                'web_impressions', 'discover_impressions', 'news_impressions', 'total_impressions']:
        if col not in df_fmt.columns:
            df_fmt[col] = 0

    for col in df_fmt.columns:
        if 'clicks' in col or 'impressions' in col:
            df_fmt[col] = df_fmt[col].apply(lambda x: f"{x:,.0f}")
        elif 'ctr' in col:
            df_fmt[col] = df_fmt[col].apply(lambda x: f"{x:.2%}")

    monthly_clicks_table = df_fmt[['month', 'web_clicks', 'discover_clicks', 'news_clicks', 'total_clicks']].style.set_table_attributes('class="table table-bordered table-sm"').set_table_styles(styles).hide(axis='index').to_html()
    monthly_imps_table = df_fmt[['month', 'web_impressions', 'discover_impressions', 'news_impressions', 'total_impressions']].style.set_table_attributes('class="table table-bordered table-sm"').set_table_styles(styles).hide(axis='index').to_html()
    data_table = df_fmt.style.set_table_attributes('class="dataframe table table-striped table-hover"').set_table_styles(styles).hide(axis='index').to_html()

    chart_data = df.sort_values('month').to_json(orient='records')

    template_loader = FileSystemLoader('templates')
    env = Environment(loader=template_loader)
    template = env.get_template('consolidated-traffic-report-template.html')

    html_content = template.render(
        site_url=site_url,
        start_month=start_month,
        end_month=end_month,
        clicks_summary_table=clicks_summary_table,
        impressions_summary_table=imps_summary_table,
        monthly_clicks_table=monthly_clicks_table,
        monthly_impressions_table=monthly_imps_table,
        data_table=data_table,
        chart_data=chart_data,
        generation_date=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    )

    with open(html_output_path, 'w', encoding='utf-8') as f:
        f.write(html_content)

def run_report(service, site_url, months=16):
    """Executes the consolidated traffic report."""
    print(f"Running Consolidated Traffic Report for {site_url} ({months} months)...")
    
    # 1. Determine Date Range
    today = date.today()
    # Go back to the last complete month
    end_date_dt = today.replace(day=1) - timedelta(days=1)
    start_date_dt = (end_date_dt.replace(day=1) - relativedelta(months=months-1))
    
    start_date = start_date_dt.strftime('%Y-%m-%d')
    end_date = end_date_dt.strftime('%Y-%m-%d')

    # 2. Fetch Data with Cache (Daily data, will aggregate by month)
    web_df = fetch_with_cache(service, site_url, start_date, end_date, ['date'], 'web')
    discover_df = fetch_with_cache(service, site_url, start_date, end_date, ['date'], 'discover')
    news_df = fetch_with_cache(service, site_url, start_date, end_date, ['date'], 'googleNews')

    def process_to_monthly(df, search_type):
        if df.empty:
            return pd.DataFrame(columns=['month', f'{search_type}_clicks', f'{search_type}_impressions'])
        df['date'] = pd.to_datetime(df['date'])
        df['month'] = df['date'].dt.strftime('%Y-%m')
        agg = df.groupby('month').agg({
            'clicks': 'sum',
            'impressions': 'sum'
        }).reset_index()
        agg.rename(columns={'clicks': f'{search_type}_clicks', 'impressions': f'{search_type}_impressions'}, inplace=True)
        return agg

    web_m = process_to_monthly(web_df, 'web')
    discover_m = process_to_monthly(discover_df, 'discover')
    news_m = process_to_monthly(news_df, 'news')

    # 3. Merge
    merged_df = web_m
    for other in [discover_m, news_m]:
        if not other.empty:
            merged_df = pd.merge(merged_df, other, on='month', how='outer')
    
    merged_df.fillna(0, inplace=True)
    
    # Calculate totals
    merged_df['total_clicks'] = merged_df[[c for c in merged_df.columns if 'clicks' in c]].sum(axis=1)
    merged_df['total_impressions'] = merged_df[[c for c in merged_df.columns if 'impressions' in c]].sum(axis=1)
    merged_df['total_ctr'] = merged_df['total_clicks'] / merged_df['total_impressions']
    
    merged_df = merged_df.sort_values('month', ascending=False)

    # 4. Output Paths
    output_dir = get_output_dir(site_url)
    os.makedirs(output_dir, exist_ok=True)
    slug = get_filename_slug(site_url)
    
    file_prefix = f"consolidated-traffic-{slug}-{start_date}-to-{end_date}"
    csv_path = os.path.join(output_dir, f"{file_prefix}.csv")
    html_path = os.path.join(output_dir, f"{file_prefix}.html")

    # 5. Save and Generate
    merged_df.to_csv(csv_path, index=False, encoding='utf-8')
    generate_html_report(merged_df, site_url, html_path)
    
    print(f"CSV saved to: {csv_path}")
    print(f"HTML saved to: {html_path}")
    return html_path

if __name__ == '__main__':
    import argparse
    from core.client import get_gsc_service
    
    parser = argparse.ArgumentParser(description='Generate a consolidated performance report.')
    parser.add_argument('site_url', help='The URL of the site to analyse.')
    parser.add_argument('--months', type=int, default=16, help='Number of months to include.')
    
    args = parser.parse_args()
    service = get_gsc_service()
    if service:
        run_report(service, args.site_url, args.months)
