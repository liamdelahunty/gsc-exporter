import os
import sys
import pandas as pd
from functools import reduce
import argparse
from datetime import date, timedelta

# Add parent directory to sys.path to allow importing core
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.naming import get_output_dir
from core.cache import fetch_with_cache
from core.client import get_gsc_service

SEARCH_TYPES = ['web', 'image', 'video', 'news', 'discover', 'googleNews']

def run_report(service, site_url, start_date, end_date):
    """
    Runs the search type performance report.
    """
    print(f"Running search type performance report for {site_url} ({start_date} to {end_date})")
    
    all_data_dfs = []
    
    # 1. Fetch data for each search type
    for st in SEARCH_TYPES:
        df = fetch_with_cache(service, site_url, start_date, end_date, dimensions=['date'], search_type=st)
        
        if not df.empty:
            # Rename columns to include search type
            rename_dict = {
                'clicks': f'{st}_clicks',
                'impressions': f'{st}_impressions',
                'ctr': f'{st}_ctr',
                'position': f'{st}_position'
            }
            df.rename(columns=rename_dict, inplace=True)
            all_data_dfs.append(df)
    
    if not all_data_dfs:
        print("No data found.")
        return

    # 2. Merge data
    merged_df = reduce(lambda left, right: pd.merge(left, right, on='date', how='outer'), all_data_dfs)
    merged_df.fillna(0, inplace=True)
    merged_df = merged_df.sort_values('date', ascending=False)
    
    # 3. Save output
    output_dir = get_output_dir(site_url)
    os.makedirs(output_dir, exist_ok=True)
    csv_path = os.path.join(output_dir, f"search-type-performance-{start_date}-to-{end_date}.csv")
    merged_df.to_csv(csv_path, index=False)
    print(f"Report saved to {csv_path}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Run search type performance analysis.')
    parser.add_argument('site_url', help='The URL of the site to analyse.')
    parser.add_argument('--start-date', help='Start date (YYYY-MM-DD).')
    parser.add_argument('--end-date', help='End date (YYYY-MM-DD).')
    parser.add_argument('--last-month', action='store_true', help='Run for the last calendar month.')
    
    args = parser.parse_args()
    
    if args.last_month:
        today = date.today()
        first_day_current_month = today.replace(day=1)
        last_day_last_month = first_day_current_month - timedelta(days=1)
        start_date = last_day_last_month.replace(day=1).strftime('%Y-%m-%d')
        end_date = last_day_last_month.strftime('%Y-%m-%d')
    else:
        start_date = args.start_date
        end_date = args.end_date
        
    if not start_date or not end_date:
        print("Error: Either provide --start-date and --end-date, or use --last-month.")
        sys.exit(1)
        
    service = get_gsc_service()
    if service:
        run_report(service, args.site_url, start_date, end_date)
