"""
Generates a report identifying pages with "out of the ordinary" traffic spikes.
Adapted for the modular GSC Exporter.
"""
import os
import pandas as pd
import numpy as np
from datetime import date
from dateutil.relativedelta import relativedelta
from core.naming import get_output_dir, get_filename_slug
from core.cache import fetch_with_cache

def run_report(service, site_url, months=24, threshold=2.0, search_type='web'):
    """Executes the seasonal page spike report."""
    print(f"Running Seasonal Page Spike Report for {site_url} ({months} months, threshold {threshold})...")
    
    today = date.today()
    # End of last full month
    end_date_dt = today.replace(day=1) - relativedelta(days=1)
    
    monthly_data = []
    
    for i in range(months):
        chunk_end = end_date_dt - relativedelta(months=i)
        chunk_start = chunk_end.replace(day=1)
        
        s_str = chunk_start.strftime('%Y-%m-%d')
        e_str = chunk_end.strftime('%Y-%m-%d')
        
        print(f"  - Processing {chunk_start.strftime('%Y-%m')}...")
        df = fetch_with_cache(service, site_url, s_str, e_str, ['page'], search_type)
        if not df.empty:
            df['month'] = chunk_start.strftime('%Y-%m')
            monthly_data.append(df)

    if not monthly_data:
        print("No data found for the specified period.")
        return None
        
    full_df = pd.concat(monthly_data, ignore_index=True)
    
    # Identify spikes for the most recent month
    latest_month = end_date_dt.strftime('%Y-%m')
    latest_df = full_df[full_df['month'] == latest_month].copy()
    historical_df = full_df[full_df['month'] != latest_month]
    
    if latest_df.empty or historical_df.empty:
        print("Insufficient data for spike analysis (need at least 2 months).")
        return None

    # Calculate historical stats per page
    stats = historical_df.groupby('page').agg({
        'clicks': ['mean', 'std'],
        'impressions': ['mean', 'std']
    })
    stats.columns = ['clicks_mean', 'clicks_std', 'impressions_mean', 'impressions_std']
    stats = stats.reset_index()
    
    # Merge stats into latest data
    merged = pd.merge(latest_df, stats, on='page', how='left')
    
    # Calculate Z-scores
    merged['clicks_z'] = (merged['clicks'] - merged['clicks_mean']) / merged['clicks_std']
    merged['impressions_z'] = (merged['impressions'] - merged['impressions_mean']) / merged['impressions_std']
    
    # Filter by threshold
    spikes = merged[(merged['clicks_z'] > threshold) | (merged['impressions_z'] > threshold)].copy()
    spikes = spikes.sort_values(by='clicks_z', ascending=False)
    
    # Define output paths
    output_dir = get_output_dir(site_url)
    os.makedirs(output_dir, exist_ok=True)
    slug = get_filename_slug(site_url)
    
    run_date_str = date.today().strftime('%Y-%m-%d')
    file_prefix = f"seasonal-page-spike-{slug}-{run_date_str}"
    csv_path = os.path.join(output_dir, f"{file_prefix}.csv")
    
    # Save CSV
    spikes.to_csv(csv_path, index=False)
    print(f"Spike report completed: {csv_path}")
    
    # (HTML generation omitted for brevity in this pilot, 
    # but could be added similarly to page-level-report)
    
    return csv_path

if __name__ == '__main__':
    import argparse
    from core.client import get_gsc_service
    
    parser = argparse.ArgumentParser(description='Identify traffic spikes.')
    parser.add_argument('site_url', help='The URL of the site to analyse.')
    parser.add_argument('--months', type=int, default=24, help='Number of months to analyse.')
    parser.add_argument('--threshold', type=float, default=2.0, help='Z-score threshold.')
    parser.add_argument('--search-type', default='web', help='The search type.')
    
    args = parser.parse_args()
    
    service = get_gsc_service()
    if service:
        run_report(service, args.site_url, args.months, args.threshold, args.search_type)
