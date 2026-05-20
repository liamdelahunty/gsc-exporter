import os
import sys
import pandas as pd
from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta
import argparse

# Add parent directory to sys.path to allow importing core
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.naming import get_output_dir
from core.cache import fetch_with_cache
from core.client import get_gsc_service

def run_report(service, site_url, months=16):
    """
    Runs the queries and pages analysis report.
    """
    print(f"Running queries/pages analysis for {site_url}")
    
    today = date.today()
    all_monthly_data = []

    # Fetch data for each of the last N months
    for i in range(1, months + 1):
        end_of_month = today.replace(day=1) - relativedelta(months=i - 1) - timedelta(days=1)
        start_of_month = end_of_month.replace(day=1)
        start_date = start_of_month.strftime('%Y-%m-%d')
        end_date = end_of_month.strftime('%Y-%m-%d')
        
        print(f"  - Fetching data for {start_of_month.strftime('%Y-%m')}...")
        
        # Use core.cache.fetch_with_cache to get data grouped by query/page
        df = fetch_with_cache(service, site_url, start_date, end_date, dimensions=['query', 'page'])
        
        if not df.empty:
            # Aggregate stats for the month
            monthly_totals = {
                'month': start_of_month.strftime('%Y-%m'),
                'clicks': df['clicks'].sum(),
                'impressions': df['impressions'].sum(),
                'queries': df['query'].nunique(),
                'pages': df['page'].nunique(),
                'ctr': df['clicks'].sum() / df['impressions'].sum() if df['impressions'].sum() > 0 else 0,
                'position': df['position'].mean()
            }
            all_monthly_data.append(monthly_totals)
    
    # Save output
    if all_monthly_data:
        df_final = pd.DataFrame(all_monthly_data)
        output_dir = get_output_dir(site_url)
        os.makedirs(output_dir, exist_ok=True)
        csv_path = os.path.join(output_dir, "queries-pages-analysis-historical.csv")
        df_final.to_csv(csv_path, index=False)
        print(f"Report saved to {csv_path}")
    else:
        print(f"No data found for {site_url}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Run queries and pages analysis.')
    parser.add_argument('site_url', help='The URL of the site to analyse.')
    parser.add_argument('--months', type=int, default=16, help='Number of months to analyse.')
    
    # Accept but ignore start/end date for compatibility with batch runner
    parser.add_argument('--start-date', help=argparse.SUPPRESS)
    parser.add_argument('--end-date', help=argparse.SUPPRESS)
    
    args = parser.parse_args()
    
    service = get_gsc_service()
    if service:
        run_report(service, args.site_url, args.months)
