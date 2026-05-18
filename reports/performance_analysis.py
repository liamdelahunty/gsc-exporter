import pandas as pd
import os
from core.naming import get_output_dir
from core.cache import fetch_with_cache

def run_report(service, site_url, start_date, end_date, comparison_start_date=None, comparison_end_date=None):
    """
    Runs the performance analysis report.
    """
    print(f"Running performance analysis for {site_url}")

    # Fetch data for current period
    df_current = fetch_with_cache(service, site_url, start_date, end_date, dimensions=['query', 'page'])
    
    # Fetch data for comparison period if provided
    if comparison_start_date and comparison_end_date:
        df_previous = fetch_with_cache(service, site_url, comparison_start_date, comparison_end_date, dimensions=['query', 'page'])
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
            df_merged[col] = 0

    # Fill NaN values
    numeric_cols = df_merged.select_dtypes(include=['number']).columns
    df_merged[numeric_cols] = df_merged[numeric_cols].fillna(0)
    
    # Calculate deltas
    df_merged['clicks_delta'] = df_merged['clicks_current'] - df_merged['clicks_previous']
    
    # Save output
    output_dir = get_output_dir(site_url)
    os.makedirs(output_dir, exist_ok=True)
    csv_path = os.path.join(output_dir, f"performance-analysis-{start_date}-to-{end_date}.csv")
    df_merged.to_csv(csv_path, index=False)
    print(f"Report saved to {csv_path}")
