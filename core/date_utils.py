"""
Standard date utilities for GSC Exporter.
"""
import time
import socket
from datetime import date, datetime, timedelta
from dateutil.relativedelta import relativedelta
from googleapiclient.errors import HttpError

def get_latest_available_date(service, site_url, max_retries=10):
    """
    Determines the latest date for which GSC data is available by querying
    backwards from today.
    """
    if not service:
        # Fallback if no service provided (e.g. during testing or if auth fails)
        fallback_date = date.today() - timedelta(days=3)
        print(f"  - No GSC service provided. Defaulting to fallback date: {fallback_date}")
        return fallback_date

    current_date = date.today()
    for i in range(max_retries):
        check_date = current_date - timedelta(days=i)
        check_date_str = check_date.strftime('%Y-%m-%d')
        
        try:
            request = {
                'startDate': check_date_str,
                'endDate': check_date_str,
                'dimensions': ['date'],
                'rowLimit': 1
            }
            # Use a very short timeout/small request to check availability
            response = service.searchanalytics().query(siteUrl=site_url, body=request).execute()
            
            if 'rows' in response and response['rows']:
                print(f"  - Latest available GSC data found for: {check_date_str}")
                return check_date
        except HttpError as e:
            if e.resp.status == 400: # No data for this date
                continue
        except Exception:
            continue
            
    # Default fallback if we can't find anything
    fallback_date = date.today() - timedelta(days=3)
    print(f"  - Could not determine latest GSC date. Using fallback: {fallback_date}")
    return fallback_date

def get_last_month_range(anchor_date=None):
    """
    Returns (start_date, end_date) for the last complete calendar month
    relative to the anchor_date (defaults to today).
    """
    if anchor_date is None:
        anchor_date = date.today()
    
    # If anchor_date is, say, June 1st, we want May.
    # If anchor_date is June 15th, we still want May (last complete month).
    first_of_this_month = anchor_date.replace(day=1)
    end_date_dt = first_of_this_month - timedelta(days=1)
    start_date_dt = end_date_dt.replace(day=1)
    return start_date_dt.strftime('%Y-%m-%d'), end_date_dt.strftime('%Y-%m-%d')

def get_last_7_days_range(anchor_date):
    """Returns (start_date, end_date) for the 7 days ending at anchor_date."""
    start_date_dt = anchor_date - timedelta(days=6)
    return start_date_dt.strftime('%Y-%m-%d'), anchor_date.strftime('%Y-%m-%d')

def get_month_range_lookback(end_date_str, months=16):
    """Returns (start_date, end_date) looking back X months from end_date_str."""
    if not end_date_str:
        # This shouldn't really happen with the new dynamic defaults, but keep for safety
        today = date.today()
        first_of_this_month = today.replace(day=1)
        end_dt = first_of_this_month - timedelta(days=1)
        end_date_str = end_dt.strftime('%Y-%m-%d')
    else:
        end_dt = datetime.strptime(end_date_str, '%Y-%m-%d')
    
    # Anchor to the first of the month for the lookback calculation
    start_dt = (end_dt.replace(day=1) - relativedelta(months=months-1))
    return start_dt.strftime('%Y-%m-%d'), end_date_str

def parse_standard_date_args(args, service=None, site_url=None):
    """
    Standardises date argument parsing across all reports.
    Priority:
    1. Explicit --start-date and --end-date
    2. --last-7-days flag (anchored to latest available data)
    3. --last-month flag (anchored to latest available data)
    4. Default to last available complete month if nothing else provided
    """
    # 1. Explicit dates
    if hasattr(args, 'start_date') and hasattr(args, 'end_date') and args.start_date and args.end_date:
        return args.start_date, args.end_date
    
    # We need the latest available date for all other options
    latest_date = get_latest_available_date(service, site_url)

    # 2. Last 7 days
    if hasattr(args, 'last_7_days') and args.last_7_days:
        return get_last_7_days_range(latest_date)

    # 3. Last month (or default)
    # If --last-month is requested, or if no date args are provided at all
    return get_last_month_range(latest_date)

def has_data_on_date(service, site_url, check_date):
    """Checks if there is any GSC data for a specific date."""
    if not service:
        return False
    check_date_str = check_date.strftime('%Y-%m-%d')
    try:
        request = {
            'startDate': check_date_str,
            'endDate': check_date_str,
            'dimensions': ['date'],
            'rowLimit': 1
        }
        response = service.searchanalytics().query(siteUrl=site_url, body=request).execute()
        return 'rows' in response and response['rows']
    except HttpError as e:
        if e.resp.status == 400: # No data for this date
            return False
        return False
    except Exception:
        return False

def get_first_available_gsc_date(service, site_url, latest_date, verbose=False):
    """
    Determines the first date for which GSC data is available using binary search.
    """
    if verbose:
        print("Searching for the first available date (this may take a moment)...")
    
    # GSC data is available for approx. 16 months. Search a wider range to be safe.
    low = latest_date - relativedelta(months=17)
    high = latest_date
    
    first_date = None
    
    while low <= high:
        mid = low + (high - low) // 2
        if verbose:
            print(f"Searching around: {mid.strftime('%Y-%m-%d')}")
        if has_data_on_date(service, site_url, mid):
            first_date = mid
            high = mid - timedelta(days=1) # Try to find an even earlier date
        else:
            low = mid + timedelta(days=1) # First date must be after mid
            
    return first_date

def get_first_complete_month_start(first_available_date):
    """
    Returns the first date of the first complete calendar month 
    on or after the first available GSC date.
    
    If the first available date is the 1st of a month, that month is complete.
    Otherwise, the first complete month starts on the 1st of the next month.
    """
    if not first_available_date:
        return None
    if first_available_date.day == 1:
        return first_available_date
    else:
        return (first_available_date + relativedelta(months=1)).replace(day=1)


