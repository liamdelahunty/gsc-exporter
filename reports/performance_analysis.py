"""
A script for performance analysis of Google Search Console data.

This script fetches performance data (clicks, impressions, CTR, position) for two 
different time periods, compares them, and generates a report highlighting best/worst 
performing pages and pages with low CTR.

Usage:
    python performance-analysis.py <site_url> [comparison_flag] [filter_flags]

Examples:
    python performance-analysis.py https://www.example.com --last-month
"""
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

from jinja2 import Environment, FileSystemLoader

def create_html_report(page_title, current_period_str, previous_period_str, df_best, df_worst, df_low_ctr, df_rising_stars, df_falling_stars):
    """Generates an HTML report using a Jinja2 template."""
    
    # Helper to convert dataframe to HTML table with Bootstrap classes
    def df_to_html(df, table_id):
        if df.empty:
            return "<p>No data available for this section.</p>"
        
        df = df.copy()
        # Format CTR and Position columns first
        for col_name in ['ctr_current', 'ctr_previous']:
            if col_name in df.columns:
                df[col_name] = df[col_name].apply(lambda x: f"{x:.2%}")
        for col_name in ['position_current', 'position_previous']:
            if col_name in df.columns:
                df[col_name] = df[col_name].apply(lambda x: f"{x:.2f}")

        # Format Clicks and Impressions columns with comma separators
        for col in df.columns:
            if 'clicks' in col or 'impressions' in col:
                # Ensure the column is numeric before formatting
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
                df[col] = df[col].apply(lambda x: f"{int(x):,}") # Format as integer with commas

        return df.to_html(classes="table table-striped table-hover", index=False, table_id=table_id, border=0)

    template_loader = FileSystemLoader('templates')
    env = Environment(loader=template_loader)
    template = env.get_template('performance-analysis-template.html')

    html_content = template.render(
        page_title=page_title,
        current_period_str=current_period_str,
        previous_period_str=previous_period_str,
        df_best_html=df_to_html(df_best, 'table-best'),
        df_worst_html=df_to_html(df_worst, 'table-worst'),
        df_rising_stars_html=df_to_html(df_rising_stars, 'table-rising'),
        df_falling_stars_html=df_to_html(df_falling_stars, 'table-falling'),
        df_low_ctr_html=df_to_html(df_low_ctr, 'table-low-ctr'),
        generation_date=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    )
    
    return html_content

def run_report(service, site_url, start_date, end_date, comparison_start_date=None, comparison_end_date=None):
    """
    Runs the performance analysis report.
    """
    print(f"Running performance analysis for {site_url} ({start_date} to {end_date})")

    # Fetch data for current period
    df_current = fetch_with_cache(service, site_url, start_date, end_date, dimensions=['query', 'page']).copy()
    
    # Fetch data for comparison period if provided
    if comparison_start_date and comparison_end_date:
        df_previous = fetch_with_cache(service, site_url, comparison_start_date, comparison_end_date, dimensions=['query', 'page']).copy()
    else:
        df_previous = pd.DataFrame()

    # Merge and process data
    if df_current.empty and df_previous.empty:
        print("No data found for either period.")
        return

    # Rename columns and merge
    df_current.rename(columns={
        'clicks': 'clicks_current', 'impressions': 'impressions_current',
        'ctr': 'ctr_current', 'position': 'position_current'
    }, inplace=True)

    if not df_previous.empty:
        df_previous.rename(columns={
            'clicks': 'clicks_previous', 'impressions': 'impressions_previous',
            'ctr': 'ctr_previous', 'position': 'position_previous'
        }, inplace=True)
        df_merged = pd.merge(df_current, df_previous, on=['page', 'query'], how='outer')
    else:
        df_merged = df_current
        for col in ['clicks_previous', 'impressions_previous', 'ctr_previous', 'position_previous']:
            if col not in df_merged.columns:
                df_merged[col] = 0

    # Fill NaN values
    numeric_cols = df_merged.select_dtypes(include=['number']).columns
    df_merged[numeric_cols] = df_merged[numeric_cols].fillna(0)
    
    # Calculate deltas
    df_merged['clicks_delta'] = df_merged['clicks_current'] - df_merged['clicks_previous']
    df_merged['impressions_delta'] = df_merged['impressions_current'] - df_merged['impressions_previous']
    df_merged['ctr_delta'] = df_merged['ctr_current'] - df_merged['ctr_previous']
    df_merged['position_delta'] = df_merged['position_previous'] - df_merged['position_current']
    
    # Sort for analysis
    df_best = df_merged.sort_values(by='clicks_delta', ascending=False).head(20)
    df_worst = df_merged.sort_values(by='clicks_delta', ascending=True).head(20)

    # Identify low CTR opportunities
    low_ctr_threshold_impressions = 1000
    low_ctr_threshold_ctr = 0.01
    df_low_ctr = df_merged[
        (df_merged['impressions_current'] >= low_ctr_threshold_impressions) &
        (df_merged['ctr_current'] < low_ctr_threshold_ctr)
    ].sort_values(by='impressions_current', ascending=False).head(20)

    # Identify Rising and Falling Stars
    rising_stars_prev_impressions_max = 50
    rising_stars_curr_impressions_min = 500
    df_rising_stars = df_merged[
        (df_merged['impressions_previous'] < rising_stars_prev_impressions_max) &
        (df_merged['impressions_current'] >= rising_stars_curr_impressions_min)
    ].sort_values(by='impressions_current', ascending=False).head(20)

    falling_stars_prev_clicks_min = 500
    falling_stars_curr_clicks_max = 50
    df_falling_stars = df_merged[
        (df_merged['clicks_previous'] >= falling_stars_prev_clicks_min) &
        (df_merged['clicks_current'] < falling_stars_curr_clicks_max)
    ].sort_values(by='clicks_delta', ascending=True).head(20)

    # Output paths
    output_dir = get_output_dir(site_url)
    os.makedirs(output_dir, exist_ok=True)
    slug = get_filename_slug(site_url)
    
    csv_path = os.path.join(output_dir, f"performance-analysis-{slug}-{start_date}-to-{end_date}.csv")
    html_path = os.path.join(output_dir, f"performance-analysis-{slug}-{start_date}-to-{end_date}.html")
    
    # Save CSV
    df_merged.to_csv(csv_path, index=False, encoding='utf-8')
    
    # Generate and save HTML
    html_content = create_html_report(
        page_title=f"Performance Analysis for {site_url}",
        current_period_str=f"{start_date} to {end_date}",
        previous_period_str=f"{comparison_start_date} to {comparison_end_date}" if comparison_start_date else "N/A",
        df_best=df_best,
        df_worst=df_worst,
        df_low_ctr=df_low_ctr,
        df_rising_stars=df_rising_stars,
        df_falling_stars=df_falling_stars
    )
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
        
    print(f"CSV saved to: {csv_path}")
    print(f"HTML saved to: {html_path}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Run performance analysis.')
    parser.add_argument('site_url', help='The URL of the site to analyse.')
    parser.add_argument('--start-date', help='Start date (YYYY-MM-DD).')
    parser.add_argument('--end-date', help='End date (YYYY-MM-DD).')
    parser.add_argument('--last-7-days', action='store_true', help='Run for the last 7 available days.')
    parser.add_argument('--last-month', action='store_true', help='Run for the last calendar month.')
    
    args = parser.parse_args()
    
    service = get_gsc_service()
    if service:
        start_date, end_date = parse_standard_date_args(args, service, args.site_url)
        
        # Calculate comparison period (previous period of same length)
        s_dt = datetime.strptime(start_date, '%Y-%m-%d')
        e_dt = datetime.strptime(end_date, '%Y-%m-%d')
        delta = e_dt - s_dt + timedelta(days=1)
        comparison_end_date_dt = s_dt - timedelta(days=1)
        comparison_start_date_dt = comparison_end_date_dt - delta + timedelta(days=1)
        
        comparison_start_date = comparison_start_date_dt.strftime('%Y-%m-%d')
        comparison_end_date = comparison_end_date_dt.strftime('%Y-%m-%d')
        
        run_report(service, args.site_url, start_date, end_date, comparison_start_date, comparison_end_date)
