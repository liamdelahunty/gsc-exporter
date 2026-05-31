"""
Generates a summary report of Google Search Console performance data for various date ranges.
Adapted for the modular GSC Exporter.
"""
import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import pandas as pd
from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta
from urllib.parse import urlparse
from core.naming import get_output_dir, get_filename_slug
from core.cache import fetch_with_cache
from core.date_utils import parse_standard_date_args
from jinja2 import Environment, FileSystemLoader

def get_sort_key(site_url):
    """Creates a sort key for a site URL."""
    if site_url.startswith('sc-domain:'):
        root_domain = site_url.replace('sc-domain:', '')
        order = 0
        subdomain = ''
    else:
        netloc = urlparse(site_url).netloc
        parts = netloc.split('.')
        if len(parts) > 2 and parts[-2] in ['co', 'com', 'org', 'net', 'gov', 'edu'] and len(parts[-3]) > 2:
            root_domain = '.'.join(parts[-3:])
        elif len(parts) > 2:
            root_domain = '.'.join(parts[-2:])
        else:
            root_domain = netloc
        if netloc.startswith('www.'):
            order = 1
            subdomain = ''
        else:
            order = 2
            subdomain = netloc.split('.')[0]
    return (root_domain, order, subdomain)

def create_summary_report_html(df, report_title, date_range_str, site_url=None):
    """Generates a summary HTML report from a DataFrame using a Jinja2 template."""

    report_df = df.copy()
    report_df['sort_key'] = report_df['site_url'].apply(get_sort_key)
    report_df = report_df.sort_values(by=['sort_key', 'clicks'], ascending=[True, False]).drop(columns=['sort_key'])

    # Format numbers
    report_df['clicks'] = report_df['clicks'].apply(lambda x: f"{x:,.0f}")
    report_df['impressions'] = report_df['impressions'].apply(lambda x: f"{x:,.0f}")
    report_df['ctr'] = report_df['ctr'].apply(lambda x: f"{x:.2%}")
    report_df['position'] = report_df['position'].apply(lambda x: f"{x:,.2f}")
    if 'queries' in report_df.columns:
        report_df['queries'] = report_df['queries'].apply(lambda x: f"{x:,.0f}")
    if 'pages' in report_df.columns:
        report_df['pages'] = report_df['pages'].apply(lambda x: f"{x:,.0f}")

    report_df = report_df.rename(columns={
        'site_url': 'Property',
        'clicks': 'Total Clicks',
        'impressions': 'Impressions',
        'ctr': 'CTR',
        'position': 'Avg. Position',
        'queries': '# Queries',
        'pages': '# Pages'
    })

    cols = ['Property', 'Total Clicks', 'Impressions', 'CTR', 'Avg. Position']
    if '# Queries' in report_df.columns: cols.append('# Queries')
    if '# Pages' in report_df.columns: cols.append('# Pages')
    report_df = report_df[cols]

    table_html = report_df.to_html(classes="table table-striped table-hover", index=False, border=0)

    template_loader = FileSystemLoader('resources')
    env = Environment(loader=template_loader)
    template = env.get_template('report-blank.html')

    html_output = template.render(
        title=report_title,
        report_name=report_title,
        domain_name=site_url if site_url else "Account Summary", # Use site_url if available, else "Account Summary"
        date_range=date_range_str,
        main_content=f'<div class="table-responsive">{table_html}</div>'
    )

    return html_output

def run_report(service, sites, start_date, end_date, report_label=None):
    """Executes the monthly summary report for a list of sites."""
    if isinstance(sites, str):
        sites = [sites]

    print(f"Running Monthly Summary Report for {len(sites)} sites ({start_date} to {end_date})...")

    all_data = []
    for site_url in sites:
        print(f"  - Processing {site_url}...")
        # Get overall totals
        df_totals = fetch_with_cache(service, site_url, start_date, end_date, [])
        if not df_totals.empty:
            row = df_totals.iloc[0].to_dict()
            # Get unique query and page counts
            df_queries = fetch_with_cache(service, site_url, start_date, end_date, ['query'])
            df_pages = fetch_with_cache(service, site_url, start_date, end_date, ['page'])
            row['queries'] = len(df_queries)
            row['pages'] = len(df_pages)
            row['site_url'] = site_url
            row['month'] = start_date[:7] # Add month column for historical report
            all_data.append(row)

    if not all_data:
        print("No data found for the given sites and period.")
        return None

    df = pd.DataFrame(all_data)

    # Define Output Paths
    if len(sites) == 1:
        output_dir = get_output_dir(sites[0])
        slug = get_filename_slug(sites[0])
        label = slug
        report_site_url = sites[0]
    else:
        output_dir = os.path.join('output', 'account')
        label = report_label if report_label else "account-wide"
        report_site_url = None

    os.makedirs(output_dir, exist_ok=True)
    file_prefix = f"monthly-summary-report-{label}-{start_date}-to-{end_date}"
    csv_path = os.path.join(output_dir, f"{file_prefix}.csv")
    html_path = os.path.join(output_dir, f"{file_prefix}.html")

    df.to_csv(csv_path, index=False, encoding='utf-8')

    report_title = f"GSC Monthly Summary"
    if len(sites) == 1: report_title += f" for {sites[0]}"

    html_content = create_summary_report_html(df, report_title, f"{start_date} to {end_date}", report_site_url)
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(html_content)

    print(f"CSV saved to: {csv_path}")
    print(f"HTML saved to: {html_path}")
    return html_path

if __name__ == '__main__':
    import argparse
    from core.client import get_gsc_service

    parser = argparse.ArgumentParser(description='Run a monthly summary report.')
    parser.add_argument('site_url', nargs='?', help='The URL of the site to analyse.')
    parser.add_argument('--sites-file', help='Text file with site URLs.')
    parser.add_argument('--start-date', help='Start date (YYYY-MM-DD).')
    parser.add_argument('--end-date', help='End date (YYYY-MM-DD).')
    parser.add_argument('--last-month', action='store_true', help='Run for the last calendar month.')

    args = parser.parse_args()
    start_date, end_date = parse_standard_date_args(args)

    sites = []
    if args.sites_file:
        with open(args.sites_file, 'r') as f:
            sites = [line.strip() for line in f if line.strip()]
    elif args.site_url:
        sites = [args.site_url]

    service = get_gsc_service()
    if service and sites:
        run_report(service, sites, start_date, end_date)