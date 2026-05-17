"""
Unified caching system for GSC Exporter.
Handles hash-based caching with monthly fragmentation to maximise reusability.
"""
import os
import hashlib
import json
import time
import socket
import pandas as pd
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
from googleapiclient.errors import HttpError

CACHE_DIR = 'cache'

def _get_cache_paths(cache_key):
    """Returns the CSV and JSON paths for a given cache key."""
    if not os.path.exists(CACHE_DIR):
        os.makedirs(CACHE_DIR)
    csv_path = os.path.join(CACHE_DIR, f"{cache_key}.csv")
    json_path = os.path.join(CACHE_DIR, f"{cache_key}.json")
    return csv_path, json_path

def _get_monthly_chunks(start_date, end_date):
    """
    Splits a date range into monthly chunks.
    Dates can be string 'YYYY-MM-DD' or datetime.date objects.
    """
    if isinstance(start_date, str):
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
    if isinstance(end_date, str):
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()

    chunks = []
    current_start = start_date
    
    while current_start <= end_date:
        next_month_start = (current_start + relativedelta(months=1)).replace(day=1)
        current_end = min(next_month_start - relativedelta(days=1), end_date)
        chunks.append((current_start, current_end))
        current_start = next_month_start
        
    return chunks

def _fetch_from_api(service, site_url, start_date, end_date, dimensions, search_type='web', row_limit=10000):
    """Fetches performance data from GSC with pagination and retries."""
    all_data = []
    start_row = 0
    
    while True:
        success = False
        for attempt in range(3):
            try:
                request = {
                    'startDate': start_date,
                    'endDate': end_date,
                    'dimensions': dimensions,
                    'searchType': search_type,
                    'rowLimit': row_limit,
                    'startRow': start_row
                }
                response = service.searchanalytics().query(siteUrl=site_url, body=request).execute()

                if 'rows' in response:
                    rows = response['rows']
                    all_data.extend(rows)
                    if len(rows) < row_limit:
                        break
                    start_row += row_limit
                else:
                    break
                success = True
                break 
            except (socket.timeout, TimeoutError):
                time.sleep(5 * (attempt + 1))
            except HttpError as e:
                print(f"  - An HTTP error occurred: {e}")
                break 
        
        if not success or 'rows' not in response or len(response['rows']) < row_limit:
            break
            
    if not all_data:
        return pd.DataFrame()

    df = pd.DataFrame(all_data)
    # Extract dimensions from the 'keys' list
    df[dimensions] = pd.DataFrame(df['keys'].tolist(), index=df.index)
    df = df.drop(columns=['keys'])
    
    # Ensure numeric conversion
    for col in ['clicks', 'impressions', 'ctr', 'position']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        
    return df

def fetch_with_cache(service, site_url, start_date, end_date, dimensions, search_type='web'):
    """
    Fetches GSC data, using monthly fragmentation for the cache.
    Reassembles data from multiple months if necessary.
    """
    chunks = _get_monthly_chunks(start_date, end_date)
    all_dfs = []
    
    for chunk_start, chunk_end in chunks:
        s_str = chunk_start.strftime('%Y-%m-%d')
        e_str = chunk_end.strftime('%Y-%m-%d')
        
        # Create a unique key for this specific month/request
        dims = sorted(dimensions)
        cache_key_content = f"{site_url}|{s_str}|{e_str}|{','.join(dims)}|{search_type}"
        cache_key = hashlib.md5(cache_key_content.encode()).hexdigest()
        
        csv_path, json_path = _get_cache_paths(cache_key)
        
        if os.path.exists(csv_path):
            chunk_df = pd.read_csv(csv_path)
            all_dfs.append(chunk_df)
        else:
            chunk_df = _fetch_from_api(service, site_url, s_str, e_str, dimensions, search_type)
            if not chunk_df.empty:
                chunk_df.to_csv(csv_path, index=False)
                metadata = {
                    'site_url': site_url,
                    'start_date': s_str,
                    'end_date': e_str,
                    'dimensions': dimensions,
                    'search_type': search_type,
                    'fetched_at': datetime.now().isoformat()
                }
                with open(json_path, 'w') as f:
                    json.dump(metadata, f, indent=4)
                all_dfs.append(chunk_df)

    if not all_dfs:
        return pd.DataFrame()
        
    # Combine all months
    combined_df = pd.concat(all_dfs, ignore_index=True)
    
    # Aggregate across months
    agg_dict = {
        'clicks': 'sum',
        'impressions': 'sum',
        'position': 'mean'
    }
    
    # Keep all dimensions in groupby
    result_df = combined_df.groupby(dimensions).agg(agg_dict).reset_index()
    
    # Recalculate CTR
    result_df['ctr'] = result_df['clicks'] / result_df['impressions']
    
    # Sort by clicks as a sensible default
    result_df = result_df.sort_values('clicks', ascending=False)
    
    return result_df
