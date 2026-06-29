"""
Generates a consolidated weekly editorial summary report for a site.
Fetches Web, Discover, and News search performance for a 7-day period (or custom range)
and compares it with the preceding period of the same length. Displays a copy-pasteable
email summary in the console and saves a detailed HTML dashboard and CSV.
"""
import os
import sys
import argparse
import pandas as pd
from datetime import datetime, timedelta
from jinja2 import Environment, FileSystemLoader

# Add parent directory to sys.path to allow importing core
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.naming import get_output_dir, get_filename_slug
from core.cache import fetch_with_cache
from core.client import get_gsc_service
from core.date_utils import parse_standard_date_args

def comma_format(value, is_int=False):
    if value is None or (isinstance(value, str) and not value.strip()):
        return "-"
    try:
        val = float(value)
        if is_int or val.is_integer():
            return f"{int(val):,}"
        return f"{val:,.2f}"
    except (ValueError, TypeError):
        return value

def pct_format(value):
    if value is None:
        return "-"
    try:
        return f"{float(value):.2%}"
    except (ValueError, TypeError):
        return value

def float_format(value):
    if value is None:
        return "-"
    try:
        return f"{float(value):.2f}"
    except (ValueError, TypeError):
        return value

def delta_pill(val, is_pct_pts=False, is_pos=False):
    if val is None:
        return '<span class="delta-pill delta-neutral">0.0%</span>'
        
    if is_pos:
        # Position: lower is better (ranking improvement)
        try:
            val_float = float(val)
            if val_float == 0:
                return '<span class="delta-pill delta-neutral" style="background-color: #f1f5f9; color: #64748b; font-size: 0.8rem; font-weight: 600; padding: 0.125rem 0.375rem; border-radius: 4px;">0.00</span>'
            elif val_float < 0:
                # E.g. -2.5 is positive improvement
                return f'<span class="delta-pill delta-positive" style="background-color: #ecfdf5; color: #10b981; font-size: 0.8rem; font-weight: 600; padding: 0.125rem 0.375rem; border-radius: 4px;">+{abs(val_float):.2f} (up)</span>'
            else:
                # E.g. +2.5 is negative ranking drop
                return f'<span class="delta-pill delta-negative" style="background-color: #fef2f2; color: #ef4444; font-size: 0.8rem; font-weight: 600; padding: 0.125rem 0.375rem; border-radius: 4px;">-{val_float:.2f} (down)</span>'
        except (ValueError, TypeError):
            return "-"

    if is_pct_pts:
        # CTR change in percentage points
        try:
            val_float = float(val)
            pts = val_float * 100
            if pts == 0:
                return '<span class="delta-pill delta-neutral" style="background-color: #f1f5f9; color: #64748b; font-size: 0.8rem; font-weight: 600; padding: 0.125rem 0.375rem; border-radius: 4px;">0.00 pp</span>'
            elif pts > 0:
                return f'<span class="delta-pill delta-positive" style="background-color: #ecfdf5; color: #10b981; font-size: 0.8rem; font-weight: 600; padding: 0.125rem 0.375rem; border-radius: 4px;">+{pts:.2f} pp</span>'
            else:
                return f'<span class="delta-pill delta-negative" style="background-color: #fef2f2; color: #ef4444; font-size: 0.8rem; font-weight: 600; padding: 0.125rem 0.375rem; border-radius: 4px;">{pts:.2f} pp</span>'
        except (ValueError, TypeError):
            return "-"

    # Count deltas (clicks, impressions, pages, queries) which contain raw & pct
    if isinstance(val, dict):
        raw_val = val.get('raw', 0)
        pct_val = val.get('pct', 0)
    else:
        raw_val = val
        pct_val = 0
        
    try:
        raw_float = float(raw_val)
        pct_float = float(pct_val)
        
        if raw_float == 0:
            return '<span class="delta-pill delta-neutral" style="background-color: #f1f5f9; color: #64748b; font-size: 0.8rem; font-weight: 600; padding: 0.125rem 0.375rem; border-radius: 4px;">0.0%</span>'
        
        sign = "+" if raw_float > 0 else ""
        if raw_float > 0:
            return f'<span class="delta-pill delta-positive" style="background-color: #ecfdf5; color: #10b981; font-size: 0.8rem; font-weight: 600; padding: 0.125rem 0.375rem; border-radius: 4px;">{sign}{int(raw_float):,} ({pct_float:+.1%})</span>'
        else:
            return f'<span class="delta-pill delta-negative" style="background-color: #fef2f2; color: #ef4444; font-size: 0.8rem; font-weight: 600; padding: 0.125rem 0.375rem; border-radius: 4px;">{int(raw_float):,} ({pct_float:+.1%})</span>'
    except (ValueError, TypeError):
        return "-"

def compile_search_type_data(service, site_url, start_date, end_date, prev_start_date, prev_end_date, search_type, limit=10):
    """Fetches and processes current and previous period performance for a search type."""
    # 1. Fetch totals (empty dimensions)
    df_totals = fetch_with_cache(service, site_url, start_date, end_date, [], search_type)
    df_totals_prev = fetch_with_cache(service, site_url, prev_start_date, prev_end_date, [], search_type)
    
    # 2. Fetch pages (['page'] dimension)
    df_pages = fetch_with_cache(service, site_url, start_date, end_date, ['page'], search_type)
    df_pages_prev = fetch_with_cache(service, site_url, prev_start_date, prev_end_date, ['page'], search_type)
    
    # 3. Fetch queries (['query'] dimension) - if not discover
    if search_type != 'discover':
        df_queries = fetch_with_cache(service, site_url, start_date, end_date, ['query'], search_type)
        df_queries_prev = fetch_with_cache(service, site_url, prev_start_date, prev_end_date, ['query'], search_type)
    else:
        df_queries = pd.DataFrame()
        df_queries_prev = pd.DataFrame()

    if df_totals.empty and df_pages.empty:
        return {'empty': True}

    # Extract current totals
    if not df_totals.empty:
        clicks = float(df_totals.iloc[0]['clicks'])
        impressions = float(df_totals.iloc[0]['impressions'])
        ctr = float(df_totals.iloc[0]['ctr'])
        position = float(df_totals.iloc[0]['position']) if 'position' in df_totals.columns else 0.0
    else:
        clicks = float(df_pages['clicks'].sum()) if not df_pages.empty else 0.0
        impressions = float(df_pages['impressions'].sum()) if not df_pages.empty else 0.0
        ctr = clicks / impressions if impressions > 0 else 0.0
        position = 0.0
        
    # Extract previous totals
    if not df_totals_prev.empty:
        clicks_prev = float(df_totals_prev.iloc[0]['clicks'])
        impressions_prev = float(df_totals_prev.iloc[0]['impressions'])
        ctr_prev = float(df_totals_prev.iloc[0]['ctr'])
        position_prev = float(df_totals_prev.iloc[0]['position']) if 'position' in df_totals_prev.columns else 0.0
    else:
        clicks_prev = float(df_pages_prev['clicks'].sum()) if not df_pages_prev.empty else 0.0
        impressions_prev = float(df_pages_prev['impressions'].sum()) if not df_pages_prev.empty else 0.0
        ctr_prev = clicks_prev / impressions_prev if impressions_prev > 0 else 0.0
        position_prev = 0.0
        
    # Unique Pages
    pages = len(df_pages)
    pages_prev = len(df_pages_prev)
    
    # Unique Queries
    queries = len(df_queries) if not df_queries.empty else 0
    queries_prev = len(df_queries_prev) if not df_queries_prev.empty else 0
    
    # Best performing page (current)
    best_performing_page = "N/A"
    best_performing_clicks = 0
    if not df_pages.empty:
        df_pages_sorted = df_pages.sort_values(by='clicks', ascending=False)
        best_performing_page = df_pages_sorted.iloc[0]['page']
        best_performing_clicks = float(df_pages_sorted.iloc[0]['clicks'])
        
    # Deltas
    clicks_delta = clicks - clicks_prev
    clicks_delta_pct = clicks_delta / clicks_prev if clicks_prev > 0 else (1.0 if clicks > 0 else 0.0)
    
    impressions_delta = impressions - impressions_prev
    impressions_delta_pct = impressions_delta / impressions_prev if impressions_prev > 0 else (1.0 if impressions > 0 else 0.0)
    
    ctr_delta = ctr - ctr_prev
    position_delta = position - position_prev
    
    pages_delta = pages - pages_prev
    pages_delta_pct = pages_delta / pages_prev if pages_prev > 0 else (1.0 if pages > 0 else 0.0)
    
    queries_delta = queries - queries_prev
    queries_delta_pct = queries_delta / queries_prev if queries_prev > 0 else (1.0 if queries > 0 else 0.0)
    
    # Top Pages List
    top_pages_list = []
    if not df_pages.empty:
        df_pages_top = df_pages.sort_values(by='clicks', ascending=False).head(limit)
        for _, row in df_pages_top.iterrows():
            top_pages_list.append({
                'page': row['page'],
                'clicks': float(row['clicks']),
                'impressions': float(row['impressions']),
                'ctr': float(row['ctr']),
                'position': float(row['position']) if 'position' in df_pages.columns else 0.0
            })
            
    return {
        'empty': False,
        'clicks': clicks,
        'clicks_prev': clicks_prev,
        'clicks_delta': {'raw': clicks_delta, 'pct': clicks_delta_pct},
        'impressions': impressions,
        'impressions_prev': impressions_prev,
        'impressions_delta': {'raw': impressions_delta, 'pct': impressions_delta_pct},
        'ctr': ctr,
        'ctr_prev': ctr_prev,
        'ctr_delta': ctr_delta,
        'position': position,
        'position_prev': position_prev,
        'position_delta': position_delta,
        'pages': pages,
        'pages_prev': pages_prev,
        'pages_delta': {'raw': pages_delta, 'pct': pages_delta_pct},
        'queries': queries,
        'queries_prev': queries_prev,
        'queries_delta': {'raw': queries_delta, 'pct': queries_delta_pct},
        'best_performing_page': best_performing_page,
        'best_performing_clicks': best_performing_clicks,
        'top_pages': top_pages_list
    }

def generate_email_text(site_url, web_data, discover_data, news_data, start_date, end_date):
    """Compiles the plain text copy-paste email summary."""
    lines = []
    lines.append(f"Google Search Console Weekly Report for {site_url}")
    lines.append(f"Period: {start_date} to {end_date}\n")
    
    # 1. News
    lines.append("News:")
    if not news_data.get('empty', True):
        lines.append(f"Best performing: {news_data['best_performing_page']}")
        lines.append("Overall:")
        lines.append(f"Number of Pages     {int(news_data['pages']):,}")
        lines.append(f"Total Clicks        {int(news_data['clicks']):,}")
        lines.append(f"Total Impressions   {int(news_data['impressions']):,}")
        lines.append(f"Average CTR         {news_data['ctr']:.2%}")
        lines.append(f"Average Position    {news_data['position']:.2f}")
        lines.append(f"Total Unique Queries {int(news_data['queries']):,}")
    else:
        lines.append("No Google News traffic recorded.")
    lines.append("")
    
    # 2. Discover
    lines.append("Discover:")
    if not discover_data.get('empty', True):
        lines.append(f"Best performing: {discover_data['best_performing_page']}")
        lines.append(f"Number of Pages     {int(discover_data['pages']):,}")
        lines.append(f"Total Clicks        {int(discover_data['clicks']):,}")
        lines.append(f"Total Impressions   {int(discover_data['impressions']):,}")
        lines.append(f"Average CTR         {discover_data['ctr']:.2%}")
    else:
        lines.append("No Google Discover traffic recorded.")
    lines.append("")
    
    # 3. Web
    lines.append("Web:")
    if not web_data.get('empty', True):
        bp_clicks = int(web_data['best_performing_clicks'])
        lines.append(f"Best performing: {web_data['best_performing_page']} ({bp_clicks:,} clicks!)")
        lines.append(f"Number of Pages     {int(web_data['pages']):,}")
        lines.append(f"Total Clicks        {int(web_data['clicks']):,}")
        lines.append(f"Total Impressions   {int(web_data['impressions']):,}")
        lines.append(f"Average CTR         {web_data['ctr']:.2%}")
        lines.append(f"Average Position    {web_data['position']:.2f}")
        lines.append(f"Total Unique Queries {int(web_data['queries']):,}")
    else:
        lines.append("No Web search traffic recorded.")
        
    return "\n".join(lines)

def print_terminal_comparison(search_type_name, data):
    """Helper to display metrics comparison in the terminal."""
    if data.get('empty', True):
        print(f"\n--- {search_type_name} ---")
        print("No traffic data found.")
        return
        
    c_clicks = int(data['clicks'])
    p_clicks = int(data['clicks_prev'])
    c_imps = int(data['impressions'])
    p_imps = int(data['impressions_prev'])
    
    click_pct = data['clicks_delta']['pct']
    imp_pct = data['impressions_delta']['pct']
    
    print(f"\n--- {search_type_name} Comparison ---")
    print(f"Clicks:      {c_clicks:,} vs {p_clicks:,} ({click_pct:+.1%})")
    print(f"Impressions: {c_imps:,} vs {p_imps:,} ({imp_pct:+.1%})")
    print(f"CTR:         {data['ctr']:.2%} vs {data['ctr_prev']:.2%} ({data['ctr_delta']*100:+.2f} pp)")
    if 'position' in data and data['position'] > 0:
        print(f"Avg Position: {data['position']:.2f} vs {data['position_prev']:.2f} (change: {data['position_delta']:+.2f})")
    print(f"Pages:       {data['pages']:,} vs {data['pages_prev']:,} (change: {data['pages_delta']['raw']:+})")
    if 'queries' in data and data['queries'] > 0:
        print(f"Queries:     {data['queries']:,} vs {data['queries_prev']:,} (change: {data['queries_delta']['raw']:+})")
    print(f"Best Page:   {data['best_performing_page']} ({int(data['best_performing_clicks']):,} clicks)")

def run_report(service, site_url, start_date, end_date, limit=10):
    """Executes the weekly editorial summary report."""
    print(f"Generating Weekly Editorial Summary for {site_url}...")
    print(f"Current Period:  {start_date} to {end_date}")
    
    # Calculate previous period of identical length
    s_dt = datetime.strptime(start_date, '%Y-%m-%d')
    e_dt = datetime.strptime(end_date, '%Y-%m-%d')
    delta_days = (e_dt - s_dt).days + 1
    
    prev_e_dt = s_dt - timedelta(days=1)
    prev_s_dt = prev_e_dt - timedelta(days=delta_days - 1)
    
    prev_start_date = prev_s_dt.strftime('%Y-%m-%d')
    prev_end_date = prev_e_dt.strftime('%Y-%m-%d')
    print(f"Previous Period: {prev_start_date} to {prev_end_date} ({delta_days} days)")
    
    # Fetch data for all three search types
    web_data = compile_search_type_data(service, site_url, start_date, end_date, prev_start_date, prev_end_date, 'web', limit)
    discover_data = compile_search_type_data(service, site_url, start_date, end_date, prev_start_date, prev_end_date, 'discover', limit)
    news_data = compile_search_type_data(service, site_url, start_date, end_date, prev_start_date, prev_end_date, 'news', limit)
    
    # Generate the plain text copy-paste email summary
    email_text = generate_email_text(site_url, web_data, discover_data, news_data, start_date, end_date)
    
    # Render HTML template
    template_loader = FileSystemLoader('templates')
    env = Environment(loader=template_loader)
    env.filters['comma_format'] = comma_format
    env.filters['pct_format'] = pct_format
    env.filters['float_format'] = float_format
    env.filters['delta_pill'] = delta_pill
    
    template = env.get_template('weekly-editorial-summary-template.html')
    
    # Render HTML templates (Internal and Distribution versions)
    html_internal = template.render(
        page_title="Weekly Search Console Summary (Internal)",
        is_internal=True,
        site_url=site_url,
        current_period_str=f"{start_date} to {end_date}",
        previous_period_str=f"{prev_start_date} to {prev_end_date}",
        generation_date=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        email_summary_text=email_text,
        web_metrics=web_data,
        discover_metrics=discover_data,
        news_metrics=news_data,
        web_top_pages=web_data.get('top_pages', []),
        discover_top_pages=discover_data.get('top_pages', []),
        news_top_pages=news_data.get('top_pages', [])
    )
    
    html_distribution = template.render(
        page_title="Weekly Search Console Summary",
        is_internal=False,
        site_url=site_url,
        current_period_str=f"{start_date} to {end_date}",
        previous_period_str=f"{prev_start_date} to {prev_end_date}",
        generation_date=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        email_summary_text="",
        web_metrics=web_data,
        discover_metrics=discover_data,
        news_metrics=news_data,
        web_top_pages=web_data.get('top_pages', []),
        discover_top_pages=discover_data.get('top_pages', []),
        news_top_pages=news_data.get('top_pages', [])
    )
    
    # Determine output path
    output_dir = get_output_dir(site_url)
    os.makedirs(output_dir, exist_ok=True)
    slug = get_filename_slug(site_url)
    
    html_path_internal = os.path.join(output_dir, f"weekly-editorial-summary-{slug}-{start_date}-to-{end_date}-internal.html")
    html_path_dist = os.path.join(output_dir, f"weekly-editorial-summary-{slug}-{start_date}-to-{end_date}-distribution.html")
    csv_path = os.path.join(output_dir, f"weekly-editorial-summary-{slug}-{start_date}-to-{end_date}.csv")
    
    # Write HTML files
    with open(html_path_internal, 'w', encoding='utf-8') as f:
        f.write(html_internal)
        
    with open(html_path_dist, 'w', encoding='utf-8') as f:
        f.write(html_distribution)
        
    # Generate Summary CSV
    summary_rows = []
    for stype, data in [('Web', web_data), ('Discover', discover_data), ('News', news_data)]:
        if not data.get('empty', True):
            summary_rows.append({
                'Search Type': stype,
                'Clicks (Current)': data['clicks'],
                'Clicks (Previous)': data['clicks_prev'],
                'Clicks Delta': data['clicks_delta']['raw'],
                'Clicks Delta %': data['clicks_delta']['pct'],
                'Impressions (Current)': data['impressions'],
                'Impressions (Previous)': data['impressions_prev'],
                'Impressions Delta': data['impressions_delta']['raw'],
                'Impressions Delta %': data['impressions_delta']['pct'],
                'CTR (Current)': data['ctr'],
                'CTR (Previous)': data['ctr_prev'],
                'CTR Delta': data['ctr_delta'],
                'Avg Position (Current)': data.get('position', 0),
                'Avg Position (Previous)': data.get('position_prev', 0),
                'Avg Position Delta': data.get('position_delta', 0),
                'Pages (Current)': data['pages'],
                'Pages (Previous)': data['pages_prev'],
                'Pages Delta': data['pages_delta']['raw'],
                'Queries (Current)': data.get('queries', 0),
                'Queries (Previous)': data.get('queries_prev', 0),
                'Queries Delta': data.get('queries_delta', {}).get('raw', 0),
                'Best Performing Page': data['best_performing_page'],
                'Best Performing Page Clicks': data['best_performing_clicks']
            })
            
    df_summary = pd.DataFrame(summary_rows)
    df_summary.to_csv(csv_path, index=False, encoding='utf-8')
    
    # Display results to console
    print("\n" + "="*60)
    print("COPY-PASTE EMAIL SUMMARY:")
    print("="*60)
    print(email_text)
    print("="*60)
    
    # Also print enhanced terminal comparison
    print_terminal_comparison("Web Search", web_data)
    print_terminal_comparison("Google Discover", discover_data)
    print_terminal_comparison("Google News", news_data)
    
    print("\n" + "="*60)
    print(f"HTML Report (Internal):     {html_path_internal}")
    print(f"HTML Report (Distribution): {html_path_dist}")
    print(f"CSV Report generated:       {csv_path}")
    print("="*60 + "\n")
    
    return html_path_internal, html_path_dist, csv_path

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Generates a consolidated weekly editorial summary report.')
    parser.add_argument('site_url', help='The URL/property of the site to analyse (e.g. sc-domain:accountancydaily.co).')
    parser.add_argument('--start-date', help='Start date (YYYY-MM-DD).')
    parser.add_argument('--end-date', help='End date (YYYY-MM-DD).')
    parser.add_argument('--last-month', action='store_true', help='Run for the last complete calendar month.')
    parser.add_argument('--last-7-days', action='store_true', help='Run for the last 7 available days.')
    parser.add_argument('--limit', type=int, default=10, help='Limit for top pages to display (default 10).')
    
    args = parser.parse_args()
    
    # Default to last 7 days if no other date option is explicitly selected
    if not args.start_date and not args.end_date and not args.last_month:
        args.last_7_days = True
        
    service = get_gsc_service()
    if service:
        start_date, end_date = parse_standard_date_args(args, service, args.site_url)
        run_report(service, args.site_url, start_date, end_date, args.limit)
