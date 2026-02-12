"""
Performs an account-wide or single-site analysis of Google Search Console Discover data,
gathering key performance metrics for each complete calendar month.

This script authenticates with the Google Search Console API. It can either fetch a
list of all sites associated with the account or use a specific site URL provided as an
argument. For each site, it retrieves the clicks, impressions, and CTR for
Discover data for each full calendar month over the last 16 months.

The aggregated data is then compiled into a CSV file and an HTML report.
"""

import os
import pandas as pd
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.auth import exceptions
from datetime import datetime, timedelta, date
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
    # 1. Try to load existing credentials
    if os.path.exists(TOKEN_FILE):
        try:
            creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
        except Exception as e:
            print(f"Could not load credentials from {TOKEN_FILE}. Error: {e}")
            print("Will attempt to re-authenticate.")
            creds = None

    # 2. If there are no credentials or they are invalid, refresh or re-authenticate
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                print("Credentials have expired. Attempting to refresh...")
                creds.refresh(Request())
            except exceptions.RefreshError as e:
                print(f"Error refreshing token: {e}")
                print("The refresh token is expired or revoked. Deleting it and re-authenticating.")
                if os.path.exists(TOKEN_FILE):
                    os.remove(TOKEN_FILE)
                creds = None  # Force re-authentication
        
        if not creds:
            if not os.path.exists(CLIENT_SECRET_FILE):
                print(f"Error: {CLIENT_SECRET_FILE} not found. Please follow setup instructions in README.md.")
                return None
            
            print("A browser window will open for you to authorize access.")
            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        
        # Save the new or refreshed credentials for the next run
        with open(TOKEN_FILE, 'w') as token:
            token.write(creds.to_json())
            print("Authentication successful. Credentials saved.")

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
            'endDate': end_date,
            'searchType': 'discover'  # Specify 'discover' search type
        }
        response = service.searchanalytics().query(siteUrl=site_url, body=request).execute()
        
        if 'rows' in response and response['rows']:
            data = response['rows'][0]
            # Discover data does not have 'position', so set it to 0.0 or remove it
            if 'position' not in data:
                data['position'] = 0.0
            return data
        else:
            # If no data is returned, provide a default structure with 0s
            return {'clicks': 0, 'impressions': 0, 'ctr': 0.0, 'position': 0.0}
    except HttpError as e:
        if e.resp.status == 403:
            print(f"Warning: Insufficient permission for site {site_url}. Skipping further monthly data for this property.")
            return "PERMISSION_DENIED" # Special indicator
        # GSC returns 400 if 'discover' data is not available for the site or date range
        if e.resp.status == 400 and "Bad Request" in str(e):
            print(f"No Discover data available for site {site_url} from {start_date} to {end_date} (HTTP 400). Skipping.")
            return None # Treat as no data
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
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Account-Wide Google Discover Performance Report</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body {{ padding-top: 56px; }} /* Offset for fixed header */
        h1 {{ padding-bottom: .5rem; }}
        h2 {{ border-bottom: 2px solid #dee2e6; padding-bottom: .5rem; margin-top: 2rem; }}
        .table-responsive {{ max-height: 800px; }}
        footer {{ margin-top: 3rem; text-align: center; color: #6c757d; }}
    </style>
</head>
<body>
    <header class="navbar navbar-expand-lg navbar-light bg-light border-bottom mb-4 fixed-top">
        <div class="container-fluid">
            <h1 class="h3 mb-0">Account-Wide Google Discover Performance Report</h1>
        </div>
    </header>
    <main class="container-fluid py-4 flex-grow-1">
        <h2>Index</h2>
        {index_html}
        {site_sections_html}
    </main>
    <footer class="footer mt-auto py-3 bg-light">
        <div class="container text-center">
            <span class="text-muted">Report generated on {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}. <a href="https://github.com/liamdelahunty/gsc-exporter" target="_blank">gsc-exporter</a></span>
        </div>
    </footer>
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
"""

def create_single_site_html_report(df, report_title, full_period_str):
    """Generates a simplified HTML report for a single site, including a chart."""
    # Prepare data for the table by formatting numbers
    df_table = df.drop(columns=['site_url', 'position']).copy() # Drop position as it's not relevant for Discover
    df_table['clicks'] = df_table['clicks'].apply(lambda x: f"{x:,.0f}")
    df_table['impressions'] = df_table['impressions'].apply(lambda x: f"{x:,.0f}")
    df_table['ctr'] = df_table['ctr'].apply(lambda x: f"{x:.2%}")
    # df_table['position'] = df_table['position'].apply(lambda x: f"{x:.2f}") # Removed position
    report_body = df_table.to_html(classes="table table-striped table-hover", index=False, border=0)

    # Prepare data for the chart (use the original unformatted dataframe)
    chart_data = df.sort_values(by='month').to_json(orient='records')

    return f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Google Discover Performance Report for {report_title}</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body {{ padding-top: 56px; }} /* Offset for fixed header */
        h1 {{ padding-bottom: .5rem; }}
        h2 {{ border-bottom: 2px solid #dee2e6; padding-bottom: .5rem; margin-top: 2rem; }}
        .table thead th {{ background-color: #434343; color: #ffffff; text-align: left; }}
        footer {{ margin-top: 3rem; text-align: center; color: #6c757d; }}
    </style>
</head>
<body>
    <header class="navbar navbar-expand-lg navbar-light bg-light border-bottom mb-4 fixed-top">
        <div class="container-fluid">
            <h1 class="h3 mb-0">Google Discover Performance Report for {report_title}</h1>
        </div>
    </header>
    <main class="container-fluid py-4 flex-grow-1">
        <p class="text-muted">Analysis for the period: {full_period_str}</p>
        <div class="card my-4">
            <div class="card-header"><h3>Clicks vs. Impressions</h3></div>
            <div class="card-body"><canvas id="performanceChart"></canvas></div>
        </div>
        <h2>Data Table</h2>
        <div class="table-responsive">{report_body}</div>
    </main>
    <footer class="footer mt-auto py-3 bg-light">
        <div class="container text-center">
            <span class="text-muted">Report generated on {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}. <a href="https://github.com/liamdelahunty/gsc-exporter" target="_blank">gsc-exporter</a></span>
        </div>
    </footer>
    <script>
        const data = {chart_data};
        const labels = data.map(row => row.month);

        new Chart(document.getElementById('performanceChart'), {{
            type: 'line',
            data: {{
                labels: labels,
                datasets: [
                    {{
                        label: 'Clicks',
                        data: data.map(row => row.clicks),
                        borderColor: 'rgba(54, 162, 235, 1)',
                        backgroundColor: 'rgba(54, 162, 235, 0.2)',
                        yAxisID: 'yClicks',
                        fill: false,
                        tension: 0.1
                    }},
                    {{
                        label: 'Impressions',
                        data: data.map(row => row.impressions),
                        borderColor: 'rgba(255, 99, 132, 1)',
                        backgroundColor: 'rgba(255, 99, 132, 0.2)',
                        yAxisID: 'yImpressions',
                        fill: false,
                        tension: 0.1
                    }}
                ]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                interaction: {{
                    mode: 'index',
                    intersect: false,
                }},
                scales: {{
                    yClicks: {{
                        type: 'linear',
                        display: true,
                        position: 'left',
                        title: {{
                            display: true,
                            text: 'Clicks'
                        }}
                    }},
                    yImpressions: {{
                        type: 'linear',
                        display: true,
                        position: 'right',
                        title: {{
                            display: true,
                            text: 'Impressions'
                        }},
                        grid: {{
                            drawOnChartArea: false, // only draw grid for the first Y axis
                        }}
                    }}
                }}
            }}
        }});
    </script>
</body>
</html>
"""

def generate_site_sections(df, sorted_sites):
    """Generates HTML sections for each site."""
    sections_html = ''
    for site in sorted_sites:
        anchor = site.replace('https://', '').replace('http://', '').replace(':', '-').replace('/', '-').replace('.', '-')
        sections_html += f'<h2 id="{anchor}" class="mt-5">{site}</h2>'
        # Drop position from the site-specific dataframe before generating HTML
        site_df = df[df['site_url'] == site].drop(columns=['site_url', 'position'])
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
    parser = argparse.ArgumentParser(description='Run a monthly Discover performance analysis for a GSC property.')
    parser.add_argument('site_url', nargs='?', default=None, help='The URL of the site to analyse. If not provided, runs for all sites.')
    parser.add_argument('--use-cache', action='store_true', help='Use a cached CSV file from a previous run if it exists.')
    args = parser.parse_args()

    most_recent_month = (date.today().replace(day=1) - timedelta(days=1)).strftime('%Y-%m')

    if args.site_url:
        site = args.site_url
        if site.startswith('sc-domain:'):
            host_plain = site.replace('sc-domain:', '')
        else:
            host_plain = urlparse(site).netloc
        
        host_dir = host_plain.replace('www.', '')
        output_dir = os.path.join('output', host_dir)
        file_prefix = f"discover-key-performance-metrics-{host_dir.replace('.', '-')}-{most_recent_month}" # Updated file prefix
    else:
        output_dir = os.path.join('output', 'account')
        file_prefix = f"discover-key-performance-metrics-account-wide-{most_recent_month}" # Updated file prefix

    os.makedirs(output_dir, exist_ok=True)
    csv_output_path = os.path.join(output_dir, f'{file_prefix}.csv')
    html_output_path = os.path.join(output_dir, f'{file_prefix}.html')

    df = None
    sites = []

    if args.use_cache and os.path.exists(csv_output_path):
        print(f"Found cached data at {csv_output_path}. Using it to generate report.")
        df = pd.read_csv(csv_output_path)
        # If we load from cache, we need to reconstruct the 'sites' list for the multi-site report
        if 'site_url' in df.columns:
            sites = sorted(df['site_url'].unique(), key=get_sort_key)
    
    if df is None:
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
        
        try:
            df.to_csv(csv_output_path, index=False)
            print(f"\nSuccessfully exported CSV to {csv_output_path}")
            print(f"Hint: To recreate this report from the saved data, use the --use-cache flag.")
        except PermissionError:
            print(f"\nError: Permission denied when writing to the output directory.")
            return

    # Proceed with report generation using the dataframe 'df'
    try:
        if args.site_url:
            # Filter the dataframe for the single site if it was loaded from an account-wide cache
            df_single = df[df['site_url'] == args.site_url]
            
            # Determine the full period covered by the data
            if not df_single.empty:
                min_month = df_single['month'].min()
                max_month = df_single['month'].max()
                full_period_str = f"Monthly breakdown from {min_month} to {max_month}"
            else:
                full_period_str = "No data available for this period."

            html_output = create_single_site_html_report(df_single, args.site_url, full_period_str)
        else:
            # For multi-site report, format the dataframe before passing
            html_df = df.copy()
            html_df['clicks'] = html_df['clicks'].apply(lambda x: f"{x:,.0f}")
            html_df['impressions'] = html_df['impressions'].apply(lambda x: f"{x:,.0f}")
            html_df['ctr'] = html_df['ctr'].apply(lambda x: f"{x:.2%}")
            html_df['position'] = html_df['position'].apply(lambda x: f"{x:.2f}") # This column will exist but be 0.0 for discover data
            html_output = create_multi_site_html_report(html_df, sites)
        
        with open(html_output_path, 'w', encoding='utf-8') as f:
            f.write(html_output)
        print(f"Successfully created HTML report at {html_output_path}")
    except PermissionError:
        print(f"\nError: Permission denied when writing to the output directory.")

if __name__ == '__main__':
    main()
