import pandas as pd
import os
from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta
from core.naming import get_output_dir
from core.cache import fetch_with_cache

def _process_df_into_distribution(df):
    """Processes DataFrame query data into aggregated position distribution."""
    distribution = {
        'clicks_pos_1_3': 0, 'impressions_pos_1_3': 0,
        'clicks_pos_4_10': 0, 'impressions_pos_4_10': 0,
        'clicks_pos_11_20': 0, 'impressions_pos_11_20': 0,
        'clicks_pos_21_plus': 0, 'impressions_pos_21_plus': 0,
        'total_clicks': df['clicks'].sum(), 'total_impressions': df['impressions'].sum()
    }
    
    # Position logic
    for _, row in df.iterrows():
        pos = row['position']
        clicks = row['clicks']
        imps = row['impressions']
        
        if 1 <= pos <= 3:
            distribution['clicks_pos_1_3'] += clicks
            distribution['impressions_pos_1_3'] += imps
        elif 4 <= pos <= 10:
            distribution['clicks_pos_4_10'] += clicks
            distribution['impressions_pos_4_10'] += imps
        elif 11 <= pos <= 20:
            distribution['clicks_pos_11_20'] += clicks
            distribution['impressions_pos_11_20'] += imps
        elif pos >= 21:
            distribution['clicks_pos_21_plus'] += clicks
            distribution['impressions_pos_21_plus'] += imps
            
    return distribution

def run_report(service, site_url, months=16):
    """
    Runs the query position analysis report.
    """
    print(f"Running query position analysis for {site_url}")
    
    today = date.today()
    all_monthly_data = []

    # Fetch data for each of the last N months
    for i in range(1, months + 1):
        end_of_month = today.replace(day=1) - relativedelta(months=i - 1) - timedelta(days=1)
        start_of_month = end_of_month.replace(day=1)
        start_date = start_of_month.strftime('%Y-%m-%d')
        end_date = end_of_month.strftime('%Y-%m-%d')
        
        print(f"  - Fetching data for {start_of_month.strftime('%Y-%m')}...")
        
        # Use core.cache.fetch_with_cache grouped by query
        df = fetch_with_cache(service, site_url, start_date, end_date, dimensions=['query'])
        
        if not df.empty:
            distribution = _process_df_into_distribution(df)
            distribution['month'] = start_of_month.strftime('%Y-%m')
            all_monthly_data.append(distribution)
    
    # Save output
    if all_monthly_data:
        df_final = pd.DataFrame(all_monthly_data)
        output_dir = get_output_dir(site_url)
        os.makedirs(output_dir, exist_ok=True)
        csv_path = os.path.join(output_dir, f"query-position-analysis-{start_of_month.strftime('%Y-%m')}.csv")
        df_final.to_csv(csv_path, index=False)
        print(f"Report saved to {csv_path}")
    else:
        print(f"No data found for {site_url}")
