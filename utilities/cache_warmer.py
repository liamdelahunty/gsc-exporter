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
from core.date_utils import get_latest_available_date, get_month_range_lookback, get_last_month_range

# Define the "Golden" dimension sets
GOLDEN_DIMENSIONS = [
    (['date'], "Daily Totals"),
    (['page'], "Page-level Data"),
    (['query'], "Query-level Data"),
    (['page', 'query'], "Page-Query Mapping (Granular)")
]

def warm_site(service, site_url, lookback_months=16):
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
    
    print(f"Lookback: {lookback_months} full months ({start_date} to {end_date})")
    
    # 2. Iterate through Golden Dimensions
    for dims, label in GOLDEN_DIMENSIONS:
        print(f"\n>>> Priming {label} (Dimensions: {dims})...")
        try:
            # fetch_with_cache handles the monthly fragmentation and local saving
            fetch_with_cache(service, site_url, start_date, end_date, dims, label=f"Warming {label}")
        except Exception as e:
            print(f"  [!] Error warming {label}: {e}")

def main():
    parser = argparse.ArgumentParser(description='Prime the GSC cache with "Golden" dimensions.')
    parser.add_argument('sites', nargs='*', help='Individual site URLs to warm.')
    parser.add_argument('--file', help='Path to a text file containing site URLs.')
    parser.add_argument('--months', type=int, default=16, help='Number of months to look back (default 16).')
    
    args = parser.parse_args()
    
    service = get_gsc_service()
    if not service:
        print("Error: Could not authenticate GSC service.")
        sys.exit(1)
        
    site_list = args.sites if args.sites else []
    
    if args.file:
        if os.path.exists(args.file):
            with open(args.file, 'r') as f:
                site_list.extend([line.strip() for line in f if line.strip() and not line.strip().startswith('#')])
        else:
            print(f"Error: File '{args.file}' not found.")
            
    if not site_list:
        print("No sites provided. Please specify site URLs or use --file.")
        sys.exit(0)
        
    print(f"Starting Cache Warmer for {len(site_list)} sites...")
    
    for site in site_list:
        warm_site(service, site, args.months)
        
    print(f"\n{'='*60}")
    print("CACHE WARMING COMPLETE")
    print(f"{'='*60}")

if __name__ == '__main__':
    main()
