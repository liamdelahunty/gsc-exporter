"""
Utility to proactively fetch and cache Google Search Console data for multiple sites.
Primes the 'Golden Caches' (Page, Query, Page+Query, and Date) for 16 months.
"""
import os
import sys
import argparse
from datetime import date
from dateutil.relativedelta import relativedelta

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.client import get_gsc_service
from core.cache import fetch_with_cache
from core.date_utils import (
    get_latest_available_date, 
    get_month_range_lookback, 
    get_last_month_range,
    get_first_available_gsc_date,
    get_first_complete_month_start
)

# Define the "Golden" dimension sets
GOLDEN_DIMENSIONS = [
    (['date'], "Daily Totals"),
    (['page'], "Page-level Data"),
    (['query'], "Query-level Data"),
    (['page', 'query'], "Page-Query Mapping (Granular)")
]

def warm_site(service, site_url, lookback_months=16, max_rows=100000):
    """Primes all golden dimension caches for a single site."""
    print(f"\n{'='*60}")
    print(f"WARMING CACHE FOR: {site_url}")
    print(f"{'='*60}")
    
    # 1. Determine Date Range
    latest = get_latest_available_date(service, site_url)
    
    # Get the last complete month range to ensure we only cache full months
    _, end_date = get_last_month_range(latest)
    
    # Get the start date for the lookback (e.g. 16 full months)
    start_date, _ = get_month_range_lookback(end_date, lookback_months)
    
    # Get the first available date of the property to avoid caching partial months
    first_avail = get_first_available_gsc_date(service, site_url, latest, verbose=False)
    if first_avail:
        first_complete_start = get_first_complete_month_start(first_avail)
        if first_complete_start:
            first_complete_start_str = first_complete_start.strftime('%Y-%m-%d')
            # If the calculated start date is before the first complete month, adjust it forward
            if start_date < first_complete_start_str:
                print(f"  - First available GSC date is {first_avail.strftime('%Y-%m-%d')}.")
                print(f"  - Adjusting warming start date from {start_date} to {first_complete_start_str} to avoid incomplete months.")
                start_date = first_complete_start_str
                
    if start_date > end_date:
        print(f"  - No complete calendar months available to warm (latest available date is {latest.strftime('%Y-%m-%d')}).")
        return
        
    print(f"Lookback: {lookback_months} full months ({start_date} to {end_date})")
    
    # 2. Iterate through Golden Dimensions
    for dims, label in GOLDEN_DIMENSIONS:
        print(f"\n>>> Priming {label} (Dimensions: {dims})...")
        try:
            # Cap the multi-dimensional (granular) mapping to prevent pagination latency issues
            chunk_max_rows = max_rows if len(dims) > 1 else None
            # fetch_with_cache handles the monthly fragmentation and local saving
            fetch_with_cache(service, site_url, start_date, end_date, dims, label=f"Warming {label}", max_rows=chunk_max_rows)
        except Exception as e:
            print(f"  [!] Error warming {label}: {e}")

def main():
    parser = argparse.ArgumentParser(description='Prime the GSC cache with "Golden" dimensions.')
    parser.add_argument('sites', nargs='*', help='Individual site URLs to warm.')
    parser.add_argument('--file', help='Path to a text file containing site URLs.')
    parser.add_argument('--months', type=int, default=16, help='Number of months to look back (default 16).')
    parser.add_argument('--max-rows', type=int, default=100000, help='Maximum rows to fetch per month for multi-dimensional granular data (default 100000).')
    
    args = parser.parse_args()
    
    service = get_gsc_service()
    if not service:
        print("Error: Could not authenticate GSC service.")
        sys.exit(1)
        
    site_list = args.sites if args.sites else []
    
    if args.file:
        if os.path.exists(args.file):
            with open(args.file, 'r', encoding='utf-8') as f:
                site_list.extend([line.strip() for line in f if line.strip() and not line.strip().startswith('#')])
        else:
            print(f"Error: File '{args.file}' not found.")
            
    if not site_list:
        print("No sites provided. Please specify site URLs or use --file.")
        sys.exit(0)
        
    print(f"Starting Cache Warmer for {len(site_list)} sites...")
    
    for site in site_list:
        warm_site(service, site, args.months, args.max_rows)
        
    print(f"\n{'='*60}")
    print("CACHE WARMING COMPLETE")
    print(f"{'='*60}")

if __name__ == '__main__':
    main()
