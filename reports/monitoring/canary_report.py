import argparse
import datetime
import json
import os
import sys
from jinja2 import Environment, FileSystemLoader
from googleapiclient.errors import HttpError

# Add project root to path so 'core' can be imported
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from core.client import get_gsc_service
from core.cache import fetch_with_cache
from core.date_utils import parse_standard_date_args

def get_latest_available_gsc_date(service, site_url, max_retries=10):
    """Determines the latest date for which GSC data is available."""
    current_date = datetime.date.today()
    for i in range(max_retries):
        check_date = current_date - datetime.timedelta(days=i)
        check_date_str = check_date.strftime('%Y-%m-%d')
        try:
            request = {
                'startDate': check_date_str,
                'endDate': check_date_str,
                'dimensions': ['date'],
                'rowLimit': 1
            }
            response = service.searchanalytics().query(siteUrl=site_url, body=request).execute()
            if 'rows' in response and response['rows']:
                return check_date
        except HttpError:
            continue
    return None

def calculate_pct_change(current, past):
    if past == 0 or past is None: return None
    return round(((current - past) / past) * 100, 1)

def get_status_class(pct, metric_type='clicks'):
    if pct is None: return ""
    if metric_type == 'position': pct = -pct
    if pct > 25: return "positive-strong-green"
    if pct > 10: return "positive-moderate-green"
    if pct < -25: return "red"
    if pct < -10: return "amber"
    return ""

def get_date_ranges(start_date_manual=None, service=None, site_url=None):
    if start_date_manual:
        start_date = datetime.datetime.strptime(start_date_manual, '%Y-%m-%d').date()
    elif service and site_url:
        latest = get_latest_available_gsc_date(service, site_url)
        # Use the latest available date as the end date for the current period
        end_date = latest
        start_date = end_date - datetime.timedelta(days=6)
    else:
        # Fallback to absolute last week
        today = datetime.date.today()
        # Still align to last Sunday if no GSC data
        end_date = today - datetime.timedelta(days=today.weekday() + 1)
        start_date = end_date - datetime.timedelta(days=6)
    
    # LW periods relative to new start/end
    lw_end = start_date - datetime.timedelta(days=1)
    lw_start = lw_end - datetime.timedelta(days=6)
    # LM periods
    lm_end = end_date - datetime.timedelta(days=28)
    lm_start = start_date - datetime.timedelta(days=28)
    
    ly_start = start_date - datetime.timedelta(days=364)
    ly_end = end_date - datetime.timedelta(days=364)
    
    return {
        "Current": f"{start_date.strftime('%a %Y-%m-%d')} to {end_date.strftime('%a %Y-%m-%d')}",
        "Last Week": f"{lw_start.strftime('%a %Y-%m-%d')} to {lw_end.strftime('%a %Y-%m-%d')}",
        "Last Month": f"{lm_start.strftime('%a %Y-%m-%d')} to {lm_end.strftime('%a %Y-%m-%d')}",
        "Last Year": f"{ly_start.strftime('%a %Y-%m-%d')} to {ly_end.strftime('%a %Y-%m-%d')}"
    }, start_date, end_date, lw_start, lw_end, lm_start, lm_end, ly_start, ly_end

def fetch_gsc_metrics(service, site_url, start, end, label=None):
    df = fetch_with_cache(service, site_url, start.isoformat(), end.isoformat(), dimensions=[], label=label)
    if df.empty:
        return {"clicks": 0, "impressions": 0, "ctr": 0, "position": 0}
    return {
        "clicks": df['clicks'].sum(),
        "impressions": df['impressions'].sum(),
        "ctr": df['ctr'].mean(),
        "position": df['position'].mean()
    }

def get_metric_table_data(cur_val, lw_val, lm_val, ly_val, metric_type):
    # Calculate Pct Changes vs Current
    lw_pct = calculate_pct_change(cur_val, lw_val)
    lm_pct = calculate_pct_change(cur_val, lm_val)
    ly_pct = calculate_pct_change(cur_val, ly_val)

    def format_val(v):
        return f"{v:,.2f}" if metric_type in ['ctr', 'position'] else f"{v:,.0f}"

    return {
        "cur": format_val(cur_val),
        "lw": format_val(lw_val), "lw_pct": lw_pct, "lw_class": get_status_class(lw_pct, metric_type),
        "lm": format_val(lm_val), "lm_pct": lm_pct, "lm_class": get_status_class(lm_pct, metric_type),
        "ly": format_val(ly_val), "ly_pct": ly_pct, "ly_class": get_status_class(ly_pct, metric_type)
    }

def run_report(args, service):
    with open(args.config, 'r') as f:
        properties = json.load(f)
    
    # We need the first site to determine the latest date if no date provided
    site_for_date = properties[0]['siteUrl'] if properties else None
    
    start_date, end_date = parse_standard_date_args(args, service, site_for_date)
    
    periods, cur_s, cur_e, lw_s, lw_e, lm_s, lm_e, ly_s, ly_e = get_date_ranges(
        args.start_date, service, site_for_date
    )
    
    # Structure for 4 tables
    metrics_data = {
        'clicks': {'title': 'Clicks', 'properties': []},
        'impressions': {'title': 'Impressions', 'properties': []},
        'ctr': {'title': 'CTR', 'properties': []},
        'position': {'title': 'Average Position', 'properties': []}
    }
    
    for prop in properties:
        site_url = prop['siteUrl']
        
        cur = fetch_gsc_metrics(service, site_url, cur_s, cur_e, label="Current")
        lw = fetch_gsc_metrics(service, site_url, lw_s, lw_e, label="Last-Week")
        lm = fetch_gsc_metrics(service, site_url, lm_s, lm_e, label="Last-Month")
        ly = fetch_gsc_metrics(service, site_url, ly_s, ly_e, label="Last-Year")
        
        for m_id in metrics_data.keys():
            m_data = get_metric_table_data(
                cur[m_id], lw[m_id], lm[m_id], ly[m_id], m_id
            )
            m_data['name'] = prop['name']
            metrics_data[m_id]['properties'].append(m_data)

    env = Environment(loader=FileSystemLoader('templates'))
    template = env.get_template('canary_report.html')
    
    html_output = template.render(
        report_timestamp=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        periods=periods,
        metrics_data=metrics_data
    )
    
    os.makedirs(args.output_dir, exist_ok=True)
    output_path = os.path.join(args.output_dir, f"gsc-monitoring-{datetime.date.today().isoformat()}.html")
    with open(output_path, 'w') as f:
        f.write(html_output)
    
    print(f"Report generated at: {output_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="config/properties.json")
    parser.add_argument("--output-dir", default="output/account")
    parser.add_argument("--start-date", help="Set week start date (YYYY-MM-DD)")
    parser.add_argument("--last-7-days", action='store_true', help="Run for the last 7 available days.")
    parser.add_argument("--last-month", action='store_true', help="Run for the last calendar month.")
    args = parser.parse_args()
    
    service = get_gsc_service()
    if service:
        run_report(args, service)
