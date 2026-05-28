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

def parse_standard_date_args(args):
    """
    Standardises date argument parsing across all reports.
    Priority:
    1. Explicit --start-date and --end-date
    2. --last-month flag
    3. Default to last month if nothing else provided
    """
    if args.start_date and args.end_date:
        return args.start_date, args.end_date
    
    # Default/Fallthrough to last month
    return get_last_month_range()
