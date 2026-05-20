import os
import sys
import pandas as pd
import numpy as np
import argparse
from datetime import date, timedelta

# Add parent directory to sys.path to allow importing core
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.naming import get_output_dir
from core.cache import fetch_with_cache
from core.client import get_gsc_service

def _segment_queries(df):
    """Segments queries into position buckets."""
    bins = [0, 3.49, 10.49, 20.49, np.inf]
    labels = ['Positions 1-3', 'Positions 4-10', 'Positions 11-20', 'Positions 21+']
    df['position_segment'] = pd.cut(df['position'], bins=bins, labels=labels)
    return df

def run_report(service, site_url, start_date, end_date):
    """
    Runs the query segmentation report.
    """
    print(f"Running query segmentation report for {site_url} ({start_date} to {end_date})")
    
    # 1. Fetch data
    df = fetch_with_cache(service, site_url, start_date, end_date, dimensions=['query'])
    
    if df.empty:
        print("No data found.")
        return

    # 2. Segment data
    df = _segment_queries(df)
    
    # 3. Save output
    output_dir = get_output_dir(site_url)
    os.makedirs(output_dir, exist_ok=True)
    csv_path = os.path.join(output_dir, f"query-segmentation-{start_date}-to-{end_date}.csv")
    df.to_csv(csv_path, index=False)
    print(f"Report saved to {csv_path}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Run query segmentation analysis.')
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
