"""
Standard date utilities for GSC Exporter.
"""
from datetime import date, datetime, timedelta
from dateutil.relativedelta import relativedelta

def get_last_month_range():
    """Returns (start_date, end_date) for the last complete calendar month."""
    today = date.today()
    end_date_dt = today.replace(day=1) - timedelta(days=1)
    start_date_dt = end_date_dt.replace(day=1)
    return start_date_dt.strftime('%Y-%m-%d'), end_date_dt.strftime('%Y-%m-%d')

def get_month_range_lookback(end_date_str, months=16):
    """Returns (start_date, end_date) looking back X months from end_date_str."""
    if not end_date_str:
        _, end_date_str = get_last_month_range()
    
    end_dt = datetime.strptime(end_date_str, '%Y-%m-%d')
    # Anchor to the first of the month for the lookback calculation
    start_dt = (end_dt.replace(day=1) - relativedelta(months=months-1))
    return start_dt.strftime('%Y-%m-%d'), end_date_str

def parse_standard_date_args(args):
    """
    Standardises date argument parsing across all reports.
    Priority:
    1. Explicit --start-date and --end-date
    2. --last-month flag
    3. Default to last month if nothing else provided
    """
    if hasattr(args, 'start_date') and hasattr(args, 'end_date') and args.start_date and args.end_date:
        return args.start_date, args.end_date
    
    # Check if last_month was requested explicitly or if we are just defaulting
    return get_last_month_range()
