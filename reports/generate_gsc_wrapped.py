"""
Generates a "Google Organic Wrapped"-style report for Google Search Console data.
Refactored for modular GSC Exporter.
"""
import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import pandas as pd
import re
from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta
from jinja2 import Environment, FileSystemLoader
from core.naming import get_output_dir, get_filename_slug
from core.cache import fetch_with_cache
from core.brand import get_brand_terms, classify_query
from core.date_utils import parse_standard_date_args, get_month_range_lookback

def generate_wrapped_narrative(wrapped_data):
    """Generates human-readable narrative strings."""
    narratives = {}
    narratives['overall_summary'] = (
        f"In the period {wrapped_data['report_period']}, your site received an incredible "
        f"{wrapped_data['total_clicks']:,} clicks from search, generating "
        f"{wrapped_data['total_impressions']:,} impressions across Google Search."
    )
    if wrapped_data['top_page'] != "N/A":
        narratives['top_page_highlight'] = (
            f"Your most popular page, '{wrapped_data['top_page']}', drove a massive "
            f"{wrapped_data['top_page_clicks']:,} clicks."
        )
    else:
        narratives['top_page_highlight'] = "No single top page could be identified."
    if wrapped_data['top_query'] != "N/A":
        narratives['top_query_highlight'] = (
            f"The keyword that brought you the most attention was '{wrapped_data['top_query']}', accounting for "
            f"{wrapped_data['top_query_clicks']:,} clicks."
        )
    else:
        narratives['top_query_highlight'] = "No single top query could be identified."
    narratives['reach_breadth'] = (
        f"Your content appeared for {wrapped_data['unique_queries_str']} different search queries "
        f"across {wrapped_data['unique_pages_str']} unique pages on your site."
    )
    if wrapped_data['most_clicked_month'] != "N/A":
        narratives['busiest_month'] = (
            f"Your busiest month for search clicks was {wrapped_data['most_clicked_month']}, bringing in "
            f"{wrapped_data['most_clicked_month_clicks']:,} clicks."
        )
    else:
        narratives['busiest_month'] = "No busiest month could be identified."
    return narratives

def run_report(service, site_url, start_date, end_date, brand_terms=None):
    """Executes the GSC Wrapped report."""
    print(f"Running GSC Wrapped Report for {site_url} ({start_date} to {end_date})...")
    
    date_range_label = f"{start_date} to {end_date}"

    # 2. Fetch Data
    # We need pages, queries, and daily data for the busiest month
    print("Fetching GSC data (this may take a moment)...")
    df_pages = fetch_with_cache(service, site_url, start_date, end_date, ['page'])
    df_queries = fetch_with_cache(service, site_url, start_date, end_date, ['query'])
    df_daily = fetch_with_cache(service, site_url, start_date, end_date, ['date'])

    if df_pages.empty and df_queries.empty:
        print("No data found for this period.")
        return None

    # 3. Calculations
    total_clicks = df_pages['clicks'].sum()
    total_impressions = df_pages['impressions'].sum()
    
    unique_pages = len(df_pages)
    unique_queries = len(df_queries)
    unique_pages_str = f"{unique_pages:,}"
    unique_queries_str = f"{unique_queries:,}"

    top_pages_list = [{'url': row['page'], 'clicks': row['clicks']} for _, row in df_pages.head(5).iterrows()]
    
    # Brand Logic
    if brand_terms is None:
        brand_terms = get_brand_terms(site_url)
    
    if brand_terms:
        df_queries['is_brand'] = df_queries['query'].apply(lambda x: classify_query(x, brand_terms))
        
        top_brand = df_queries[df_queries['is_brand']].head(5)
        top_non_brand = df_queries[~df_queries['is_brand']].head(5)
        
        top_brand_queries = [{'query': r['query'], 'clicks': r['clicks']} for _, r in top_brand.iterrows()]
        top_non_brand_queries = [{'query': r['query'], 'clicks': r['clicks']} for _, r in top_non_brand.iterrows()]
    else:
        top_brand_queries = []
        top_non_brand_queries = [{'query': r['query'], 'clicks': r['clicks']} for _, r in df_queries.head(5).iterrows()]

    top_query = top_non_brand_queries[0]['query'] if top_non_brand_queries else (top_brand_queries[0]['query'] if top_brand_queries else "N/A")
    top_query_clicks = top_non_brand_queries[0]['clicks'] if top_non_brand_queries else (top_brand_queries[0]['clicks'] if top_brand_queries else 0)

    # Busiest Months for other metrics
    most_impressed_month, most_impressed_month_impressions = "N/A", 0
    highest_ctr_month, highest_ctr_month_ctr = "N/A", 0
    best_position_month, best_position_month_position = "N/A", 0

    if not df_daily.empty:
        df_daily['month_date'] = pd.to_datetime(df_daily['date'])
        df_daily['month_name'] = df_daily['month_date'].dt.strftime('%B')
        
        monthly_agg = df_daily.groupby('month_name').agg({
            'clicks': 'sum',
            'impressions': 'sum',
            'ctr': 'mean',
            'position': 'mean'
        }).reset_index()

        top_month_clicks = monthly_agg.nlargest(1, 'clicks')
        if not top_month_clicks.empty:
            most_clicked_month = top_month_clicks.iloc[0]['month_name']
            most_clicked_month_clicks = top_month_clicks.iloc[0]['clicks']

        top_month_imps = monthly_agg.nlargest(1, 'impressions')
        if not top_month_imps.empty:
            most_impressed_month = top_month_imps.iloc[0]['month_name']
            most_impressed_month_impressions = top_month_imps.iloc[0]['impressions']

        top_month_ctr = monthly_agg.nlargest(1, 'ctr')
        if not top_month_ctr.empty:
            highest_ctr_month = top_month_ctr.iloc[0]['month_name']
            highest_ctr_month_ctr = top_month_ctr.iloc[0]['ctr']

        # Lowest position is best
        top_month_pos = monthly_agg.nsmallest(1, 'position')
        if not top_month_pos.empty:
            best_position_month = top_month_pos.iloc[0]['month_name']
            best_position_month_position = top_month_pos.iloc[0]['position']

    # 4. Final Data Object
    from urllib.parse import urlparse
    hostname = urlparse(site_url).hostname or site_url

    wrapped_data = {
        'site_url': site_url,
        'hostname': hostname,
        'report_period': date_range_label,
        'start_date': start_date,
        'end_date': end_date,
        'total_clicks': total_clicks,
        'total_impressions': total_impressions,
        'top_page': top_pages_list[0]['url'] if top_pages_list else "N/A",
        'top_page_clicks': top_pages_list[0]['clicks'] if top_pages_list else 0,
        'top_query': top_query,
        'top_query_clicks': top_query_clicks,
        'top_pages': top_pages_list,
        'top_brand_queries': top_brand_queries,
        'top_non_brand_queries': top_non_brand_queries,
        'unique_pages_str': unique_pages_str,
        'unique_queries_str': unique_queries_str,
        'most_clicked_month': most_clicked_month,
        'most_clicked_month_clicks': most_clicked_month_clicks,
        'most_impressed_month': most_impressed_month,
        'most_impressed_month_impressions': most_impressed_month_impressions,
        'highest_ctr_month': highest_ctr_month,
        'highest_ctr_month_ctr': highest_ctr_month_ctr,
        'best_position_month': best_position_month,
        'best_position_month_position': best_position_month_position,
    }
    
    narratives = generate_wrapped_narrative(wrapped_data)

    # 5. Render Template
    # Template loader expects 'templates' dir to be relative to the script or CWD
    # interactive-runner runs from project root.
    template_loader = FileSystemLoader('templates')
    env = Environment(loader=template_loader)
    template = env.get_template('gsc-wrapped-template.html')
    html_output = template.render(wrapped_data=wrapped_data, narratives=narratives)

    # 6. Output Paths
    output_dir = get_output_dir(site_url)
    os.makedirs(output_dir, exist_ok=True)
    slug = get_filename_slug(site_url)
    
    html_filename = f"gsc-wrapped-{slug}-{start_date}-to-{end_date}.html"
    html_output_path = os.path.join(output_dir, html_filename)

    csv_pages_filename = f"gsc-wrapped-{slug}-pages-{start_date}-to-{end_date}.csv"
    csv_queries_filename = f"gsc-wrapped-{slug}-queries-{start_date}-to-{end_date}.csv"
    csv_pages_path = os.path.join(output_dir, csv_pages_filename)
    csv_queries_path = os.path.join(output_dir, csv_queries_filename)

    with open(html_output_path, 'w', encoding='utf-8') as f:
        f.write(html_output)
    
    df_pages.to_csv(csv_pages_path, index=False, encoding='utf-8')
    df_queries.to_csv(csv_queries_path, index=False, encoding='utf-8')
        
    print(f"CSV saved to: {csv_pages_path}")
    print(f"CSV saved to: {csv_queries_path}")
    print(f"HTML saved to: {html_output_path}")
    return html_output_path

if __name__ == '__main__':
    import argparse
    from core.client import get_gsc_service
    
    parser = argparse.ArgumentParser(description='Generate GSC Wrapped report.')
    parser.add_argument('site_url', help='The URL of the site.')
    parser.add_argument('--start-date', help='Start date (YYYY-MM-DD).')
    parser.add_argument('--end-date', help='End date (YYYY-MM-DD).')
    parser.add_argument('--last-month', action='store_true', help='Run for the last calendar month.')
    parser.add_argument('--last-12-months', action='store_true', help='Run for the last 12 months.')
    
    args = parser.parse_args()
    
    if args.start_date and args.end_date:
        start_date, end_date = args.start_date, args.end_date
    elif args.last_12_months:
        _, end_date = parse_standard_date_args(args)
        start_date, end_date = get_month_range_lookback(end_date, months=12)
    else:
        # For GSC Wrapped, default to YTD if no specific dates provided
        start_date, end_date = parse_standard_date_args(args)
        if not args.start_date and not args.last_month:
            today = date.today()
            start_date = f"{today.year}-01-01"

    service = get_gsc_service()
    if service:
        run_report(service, args.site_url, start_date, end_date)
