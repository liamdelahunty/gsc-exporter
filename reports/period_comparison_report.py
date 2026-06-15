"""
A script to compare performance across two time periods, providing charts
and query-level delta analysis.
"""
import os
import sys
import pandas as pd
import json
from datetime import datetime, date, timedelta
import argparse

# Add parent directory to sys.path to allow importing core
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.naming import get_output_dir, get_filename_slug
from core.cache import fetch_with_cache
from core.client import get_gsc_service
from core.date_utils import parse_standard_date_args
from jinja2 import Environment, FileSystemLoader

def apply_delta_formatting(val, is_pct=False):
    if pd.isna(val) or val == 0:
        return "-"
    
    formatted_val = f"{val:.2%}" if is_pct else f"{int(val):,}"
    
    if val > 0:
        return f'<span class="positive">+{formatted_val}</span>'
    else:
        return f'<span class="negative">{formatted_val}</span>'
        
def apply_position_formatting(val):
    if pd.isna(val) or val == 0:
        return "-"
    
    formatted_val = f"{val:.2f}"
    
    # Lower position is better (negative delta is positive change)
    if val < 0:
        return f'<span class="positive">{formatted_val}</span>'
    else:
        return f'<span class="negative">+{formatted_val}</span>'

def create_html_report(page_title, current_period_str, previous_period_str, chart_data, df_queries):
    """Generates an HTML report using a Jinja2 template."""
    
    def df_to_html(df):
        if df.empty:
            return "<p>No data available for this section.</p>"
        
        df = df.copy()
        
        # Format base metrics
        for col_name in ['CTR (Current)', 'CTR (Previous)']:
            if col_name in df.columns:
                df[col_name] = df[col_name].apply(lambda x: f"{x:.2%}" if pd.notnull(x) else "-")
        for col_name in ['Pos (Current)', 'Pos (Previous)']:
            if col_name in df.columns:
                df[col_name] = df[col_name].apply(lambda x: f"{x:.2f}" if pd.notnull(x) else "-")
        for col in ['Clicks (Current)', 'Clicks (Previous)', 'Impr. (Current)', 'Impr. (Previous)']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).apply(lambda x: f"{int(x):,}")

        # Apply delta styling
        if 'Clicks Delta' in df.columns:
            df['Clicks Delta'] = df['Clicks Delta_raw'].apply(lambda x: apply_delta_formatting(x))
        if 'Impr. Delta' in df.columns:
            df['Impr. Delta'] = df['Impr. Delta_raw'].apply(lambda x: apply_delta_formatting(x))
        if 'CTR Delta' in df.columns:
            df['CTR Delta'] = df['CTR Delta_raw'].apply(lambda x: apply_delta_formatting(x, is_pct=True))
        if 'Pos Delta' in df.columns:
            df['Pos Delta'] = df['Pos Delta_raw'].apply(lambda x: apply_position_formatting(x))

        # Drop raw columns before rendering
        cols_to_drop = [c for c in df.columns if c.endswith('_raw')]
        df = df.drop(columns=cols_to_drop)

        return df.to_html(classes="table table-striped table-hover", index=False, escape=False, border=0)

    template_loader = FileSystemLoader('templates')
    env = Environment(loader=template_loader)
    template = env.get_template('period-comparison-template.html')

    html_content = template.render(
        page_title=page_title,
        current_period_str=current_period_str,
        previous_period_str=previous_period_str,
        chart_data=json.dumps(chart_data),
        df_queries_html=df_to_html(df_queries),
        generation_date=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    )
    return html_content

def run_report(service, site_url, start_date, end_date):
    print(f"Running Period Comparison for {site_url} ({start_date} to {end_date})")

    s_dt = datetime.strptime(start_date, '%Y-%m-%d')
    e_dt = datetime.strptime(end_date, '%Y-%m-%d')
    delta_days = (e_dt - s_dt).days + 1
    
    prev_e_dt = s_dt - timedelta(days=1)
    prev_s_dt = prev_e_dt - timedelta(days=delta_days - 1)
    
    prev_start_date = prev_s_dt.strftime('%Y-%m-%d')
    prev_end_date = prev_e_dt.strftime('%Y-%m-%d')
    
    print(f"Comparison period: {prev_start_date} to {prev_end_date} ({delta_days} days)")

    # 1. Fetch Daily Data for Charts
    df_date_cur = fetch_with_cache(service, site_url, start_date, end_date, dimensions=['date']).copy()
    df_date_prev = fetch_with_cache(service, site_url, prev_start_date, prev_end_date, dimensions=['date']).copy()
    
    chart_data = []
    if not df_date_cur.empty and not df_date_prev.empty:
        df_date_cur['date'] = pd.to_datetime(df_date_cur['date'])
        df_date_prev['date'] = pd.to_datetime(df_date_prev['date'])
        
        df_date_cur = df_date_cur.sort_values('date').reset_index(drop=True)
        df_date_prev = df_date_prev.sort_values('date').reset_index(drop=True)
        
        # Merge on index to align days
        for i in range(max(len(df_date_cur), len(df_date_prev))):
            cur_row = df_date_cur.iloc[i] if i < len(df_date_cur) else None
            prev_row = df_date_prev.iloc[i] if i < len(df_date_prev) else None
            
            label = cur_row['date'].strftime('%b %d') if cur_row is not None else f"Day {i+1}"
            
            chart_data.append({
                'label': label,
                'clicks_current': float(cur_row['clicks']) if cur_row is not None else 0,
                'impressions_current': float(cur_row['impressions']) if cur_row is not None else 0,
                'clicks_previous': float(prev_row['clicks']) if prev_row is not None else 0,
                'impressions_previous': float(prev_row['impressions']) if prev_row is not None else 0
            })

    # 2. Fetch Query Data
    df_q_cur = fetch_with_cache(service, site_url, start_date, end_date, dimensions=['query']).copy()
    df_q_prev = fetch_with_cache(service, site_url, prev_start_date, prev_end_date, dimensions=['query']).copy()

    if df_q_cur.empty and df_q_prev.empty:
        print("No query data found for either period.")
        return

    # Rename columns and merge
    df_q_cur.rename(columns={'clicks': 'Clicks (Current)', 'impressions': 'Impr. (Current)', 'ctr': 'CTR (Current)', 'position': 'Pos (Current)'}, inplace=True)
    df_q_prev.rename(columns={'clicks': 'Clicks (Previous)', 'impressions': 'Impr. (Previous)', 'ctr': 'CTR (Previous)', 'position': 'Pos (Previous)'}, inplace=True)
    
    if not df_q_prev.empty:
        df_merged = pd.merge(df_q_cur, df_q_prev, on=['query'], how='outer')
    else:
        df_merged = df_q_cur
        for col in ['Clicks (Previous)', 'Impr. (Previous)', 'CTR (Previous)', 'Pos (Previous)']:
            df_merged[col] = 0

    num_cols = df_merged.select_dtypes(include=['number']).columns
    df_merged[num_cols] = df_merged[num_cols].fillna(0)
    
    # Calculate deltas (raw values for styling)
    df_merged['Clicks Delta_raw'] = df_merged['Clicks (Current)'] - df_merged['Clicks (Previous)']
    df_merged['Impr. Delta_raw'] = df_merged['Impr. (Current)'] - df_merged['Impr. (Previous)']
    df_merged['CTR Delta_raw'] = df_merged['CTR (Current)'] - df_merged['CTR (Previous)']
    df_merged['Pos Delta_raw'] = df_merged['Pos (Current)'] - df_merged['Pos (Previous)']

    # Create empty formatted columns so they exist in right order
    df_merged['Clicks Delta'] = ""
    df_merged['Impr. Delta'] = ""
    df_merged['CTR Delta'] = ""
    df_merged['Pos Delta'] = ""

    # Sort and reorder
    df_final = df_merged.sort_values(by='Clicks (Current)', ascending=False).head(200)
    
    columns_order = [
        'query', 
        'Clicks (Current)', 'Clicks (Previous)', 'Clicks Delta', 'Clicks Delta_raw',
        'Impr. (Current)', 'Impr. (Previous)', 'Impr. Delta', 'Impr. Delta_raw',
        'CTR (Current)', 'CTR (Previous)', 'CTR Delta', 'CTR Delta_raw',
        'Pos (Current)', 'Pos (Previous)', 'Pos Delta', 'Pos Delta_raw'
    ]
    # Keep only available columns
    columns_order = [c for c in columns_order if c in df_final.columns]
    df_final = df_final[columns_order]

    # Output paths
    output_dir = get_output_dir(site_url)
    os.makedirs(output_dir, exist_ok=True)
    slug = get_filename_slug(site_url)
    
    csv_path = os.path.join(output_dir, f"period-comparison-{slug}-{start_date}-to-{end_date}.csv")
    html_path = os.path.join(output_dir, f"period-comparison-{slug}-{start_date}-to-{end_date}.html")
    
    # Save CSV (exclude HTML styling columns)
    csv_cols = [c for c in columns_order if not c.endswith('_raw') and 'Delta' not in c or c.endswith('_raw')]
    df_csv = df_final[csv_cols].copy()
    # Rename raw cols for clean CSV
    df_csv.rename(columns={c: c.replace('_raw', '') for c in df_csv.columns if c.endswith('_raw')}, inplace=True)
    df_csv.to_csv(csv_path, index=False, encoding='utf-8')
    
    # Generate and save HTML
    html_content = create_html_report(
        page_title=f"Period Comparison for {site_url}",
        current_period_str=f"{start_date} to {end_date}",
        previous_period_str=f"{prev_start_date} to {prev_end_date}",
        chart_data=chart_data,
        df_queries=df_final
    )
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
        
    print(f"CSV saved to: {csv_path}")
    print(f"HTML saved to: {html_path}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Run period comparison report.')
    parser.add_argument('site_url', help='The URL of the site to analyse.')
    parser.add_argument('--start-date', help='Start date (YYYY-MM-DD).')
    parser.add_argument('--end-date', help='End date (YYYY-MM-DD).')
    parser.add_argument('--last-7-days', action='store_true', help='Run for the last 7 available days.')
    parser.add_argument('--last-month', action='store_true', help='Run for the last calendar month.')
    
    args = parser.parse_args()
    
    service = get_gsc_service()
    if service:
        start_date, end_date = parse_standard_date_args(args, service, args.site_url)
        run_report(service, args.site_url, start_date, end_date)