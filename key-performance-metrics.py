"""
Performs an account-wide or single-site analysis of Google Search Console data,
gathering key performance metrics for each complete calendar month.

This script authenticates with the Google Search Console API. It can either fetch a
list of all sites associated with the account or use a specific site URL provided as an
argument. For each site, it retrieves the clicks, impressions, CTR, and average position
for each full calendar month over the last 16 months.

The aggregated data is then compiled into a CSV file and an HTML report.
"""

import os
import pandas as pd
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta
from urllib.parse import urlparse
import argparse
from functools import cmp_to_key

# --- Configuration ---
SCOPES = ['https://www.googleapis.com/auth/webmasters.readonly']
CLIENT_SECRET_FILE = 'client_secret.json'
TOKEN_FILE = 'token.json'

def get_gsc_service():
    """Authenticates and returns a Google Search Console service object."""
    creds = None
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(CLIENT_SECRET_FILE):
                print(f"Error: {CLIENT_SECRET_FILE} not found.")
                print("Please download your client secret from the Google API Console and place it in the root directory.")
                return None
            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_FILE, 'w') as token:
            token.write(creds.to_json())
    return build('webmasters', 'v3', credentials=creds)

def get_all_sites(service):
    """Fetches a list of all sites in the user's GSC account."""
    sites = []
    try:
        site_list = service.sites().list().execute()
        if 'siteEntry' in site_list:
            sites = [s['siteUrl'] for s in site_list['siteEntry']]
    except HttpError as e:
        print(f"An HTTP error occurred while fetching sites: {e}")
    except Exception as e:
        print(f"An unexpected error occurred while fetching sites: {e}")
    return sites

def get_monthly_performance_data(service, site_url, start_date, end_date):
    """Fetches performance data from GSC for a given date range."""
    try:
        request = {
            'startDate': start_date,
            'endDate': end_date
        }
        response = service.searchanalytics().query(siteUrl=site_url, body=request).execute()
        if 'rows' in response:
            return response['rows'][0]
    except HttpError as e:
        if e.resp.status == 403:
            print(f"Warning: Insufficient permission for site {site_url}. Skipping further monthly data for this property.")
            return "PERMISSION_DENIED" # Special indicator
        print(f"An HTTP error occurred for site {site_url} from {start_date} to {end_date}: {e}")
    except Exception as e:
        print(f"An unexpected error occurred for site {site_url} from {start_date} to {end_date}: {e}")
    return None

def create_multi_site_html_report(df, sorted_sites):
    """Generates an HTML report for multiple sites with an index."""
    index_html = '<ul>'
    current_root_domain = None
    for site in sorted_sites:
        root_domain, order, subdomain = get_sort_key(site)
        if root_domain != current_root_domain:
            if current_root_domain is not None:
                index_html += '</ul></li>'
            index_html += f'<li><strong>{root_domain}</strong><ul>'
            current_root_domain = root_domain
        anchor = site.replace('https://', '').replace('http://', '').replace(':', '-').replace('/', '-').replace('.', '-')
        if order == 0 or order == 1:
            index_html += f'<li><a href="#{anchor}">{site}</a></li>'
        else:
            index_html += f'<li>&nbsp;&nbsp;&nbsp;&nbsp;<a href="#{anchor}">{site}</a></li>'
    if current_root_domain is not None:
        index_html += '</ul></li>'
    index_html += '</ul>'

    site_sections_html = generate_site_sections(df, sorted_sites)

    return f"""
<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Account-Wide GSC Performance Report</title><link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
<style>body{{padding:2rem;}}.table-responsive{{max-height:800px;}}h1,h2{{border-bottom:2px solid #dee2e6;padding-bottom:.5rem;margin-top:2rem;}}footer{{margin-top:3rem;text-align:center;color:#6c757d;}}</style></head>
<body><div class="container-fluid"><h1 id="top">Account-Wide GSC Performance Report</h1><h2>Index</h2>{index_html}{site_sections_html}</div>
<footer><p><a href="https://github.com/liamdelahunty/gsc-exporter" target="_blank">gsc-exporter</a></p></footer></body></html>"""

def create_single_site_html_report(df, site_url):
    """Generates a simplified HTML report for a single site."""
    df_no_site = df.drop(columns=['site_url'])
    report_body = df_no_site.to_html(classes="table table-striped table-hover", index=False, border=0)
    return f"""
<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>GSC Performance Report for {site_url}</title><link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
<style>body{{padding:2rem;}}h1{{border-bottom:2px solid #dee2e6;padding-bottom:.5rem;margin-top:2rem;}}footer{{margin-top:3rem;text-align:center;color:#6c757d;}}</style></head>
<body><div class="container-fluid"><h1>GSC Performance Report for {site_url}</h1><div class="table-responsive">{report_body}</div></div>
<footer><p><a href="https://github.com/liamdelahunty/gsc-exporter" target="_blank">gsc-exporter</a></p></footer></body></html>"""

def generate_site_sections(df, sorted_sites):
    """Generates HTML sections for each site."""
    sections_html = ''
    for site in sorted_sites:
        anchor = site.replace('https://', '').replace('http://', '').replace(':', '-').replace('/', '-').replace('.', '-')
        sections_html += f'<h2 id="{anchor}" class="mt-5">{site}</h2>'
        site_df = df[df['site_url'] == site].drop(columns=['site_url'])
        if not site_df.empty:
            sections_html += '<div class="table-responsive">'
            sections_html += site_df.to_html(classes="table table-striped table-hover", index=False, border=0)
            sections_html += '</div><p><a href="#top">Back to Top</a></p>'
        else:
            sections_html += '<p>No data available for this site.</p><p><a href="#top">Back to Top</a></p>'
    return sections_html

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

def main():
    """Main function to run the analysis."""
    parser = argparse.ArgumentParser(description='Run a monthly performance analysis for a GSC property.')
    parser.add_argument('site_url', nargs='?', default=None, help='The URL of the site to analyse. If not provided, runs for all sites.')
    args = parser.parse_args()

    service = get_gsc_service()
    if not service:
        return

    if args.site_url:
        sites = [args.site_url]
    else:
        sites = get_all_sites(service)
        if not sites:
            print("No sites found in your account.")
            return
        sites.sort(key=get_sort_key)

    all_data = []
    today = date.today()

    for site_url in sites:
        print(f"\nFetching data for site: {site_url}")
        for i in range(1, 17):
            end_of_month = today.replace(day=1) - relativedelta(months=i - 1) - timedelta(days=1)
            start_of_month = end_of_month.replace(day=1)
            start_date = start_of_month.strftime('%Y-%m-%d')
            end_date = end_of_month.strftime('%Y-%m-%d')

            data = get_monthly_performance_data(service, site_url, start_date, end_date)
            if data == "PERMISSION_DENIED":
                break
            elif data:
                all_data.append({'site_url': site_url, 'month': start_of_month.strftime('%Y-%m'), **data})
    
    if not all_data:
        print("No performance data found.")
        return

    df = pd.DataFrame(all_data)
    most_recent_month = (today.replace(day=1) - timedelta(days=1)).strftime('%Y-%m')

    if args.site_url:
        site = args.site_url
        if site.startswith('sc-domain:'):
            host_plain = site.replace('sc-domain:', '')
        else:
            host_plain = urlparse(site).netloc
        
        host_dir = host_plain.replace('www.', '')
        output_dir = os.path.join('output', host_dir)
        file_prefix = f"key-performance-metrics-{host_dir.replace('.', '-')}-{most_recent_month}"
    else:
        output_dir = os.path.join('output', 'account')
        file_prefix = f"key-performance-metrics-account-wide-{most_recent_month}"

    os.makedirs(output_dir, exist_ok=True)
    csv_output_path = os.path.join(output_dir, f'{file_prefix}.csv')
    html_output_path = os.path.join(output_dir, f'{file_prefix}.html')
    
    try:
        df.to_csv(csv_output_path, index=False)
        print(f"\nSuccessfully exported CSV to {csv_output_path}")

        html_df = df.copy()
        html_df['ctr'] = html_df['ctr'].apply(lambda x: f"{x:.2%}")
        html_df['position'] = html_df['position'].apply(lambda x: f"{x:.2f}")

        if args.site_url:
            html_output = create_single_site_html_report(html_df, args.site_url)
        else:
            html_output = create_multi_site_html_report(html_df, sites)
        
        with open(html_output_path, 'w', encoding='utf-8') as f:
            f.write(html_output)
        print(f"Successfully created HTML report at {html_output_path}")
    except PermissionError:
        print(f"\nError: Permission denied when writing to the output directory.")

if __name__ == '__main__':
    main()
