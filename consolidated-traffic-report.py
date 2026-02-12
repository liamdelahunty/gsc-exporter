"""
Performs an account-wide or single-site analysis of Google Search Console data,
gathering key performance metrics (clicks, impressions, CTR) for both Discover and Web search types
for each complete calendar month.

This script authenticates with the Google Search Console API. It can either fetch a
list of all sites associated with the account or use a specific site URL provided as an
argument. For each site, it retrieves the clicks, impressions, and CTR for
both Discover and Web data for each full calendar month over the last 16 months.

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

def get_monthly_performance_data(service, site_url, start_date, end_date, search_type):
    """
    Fetches performance data from GSC for a given date range and search type.
    Returns a dictionary with clicks, impressions, and ctr, or None if no data.
    """
    try:
        request = {
            'startDate': start_date,
            'endDate': end_date,
            'searchType': search_type
        }
        response = service.searchanalytics().query(siteUrl=site_url, body=request).execute()
        
        if 'rows' in response and response['rows']:
            data = response['rows'][0]
            # Discover data does not have 'position', but we are explicitly ignoring it anyway.
            return {
                'clicks': data.get('clicks', 0),
                'impressions': data.get('impressions', 0),
                'ctr': data.get('ctr', 0.0)
            }
        else:
            return {'clicks': 0, 'impressions': 0, 'ctr': 0.0}
    except HttpError as e:
        if e.resp.status == 403:
            print(f"Warning: Insufficient permission for site {site_url} for {search_type} data. Skipping.")
            return "PERMISSION_DENIED" # Special indicator
        # GSC returns 400 if 'discover' data is not available for the site or date range
        if e.resp.status == 400: # "Bad Request" check is not always reliable in error message
            print(f"No {search_type} data available for site {site_url} from {start_date} to {end_date} (HTTP 400). Skipping.")
            return None # Treat as no data
        print(f"An HTTP error occurred for site {site_url} from {start_date} to {end_date} ({search_type}): {e}")
    except Exception as e:
        print(f"An unexpected error occurred for site {site_url} from {start_date} to {end_date} ({search_type}): {e}")
    return None

def create_multi_site_html_report(df, sorted_sites):
    """Generates an HTML report for multiple sites with an index, displaying consolidated data."""
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
    <title>Account-Wide Google Search Performance Report (Discover & Web)</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body {{ padding-top: 56px; }} /* Offset for fixed header */
        h1 {{ border-bottom: 2px solid #dee2e6; padding-bottom: .5rem; }}
        h2 {{ border-bottom: 2px solid #dee2e6; padding-bottom: .5rem; margin-top: 2rem; }}
        .table-responsive {{ max-height: 800px; }}
        footer {{ margin-top: 3rem; text-align: center; color: #6c757d; }}
    </style>
</head>
<body>
    <header class="navbar navbar-expand-lg navbar-light bg-light border-bottom mb-4 fixed-top">
        <div class="container-fluid">
            <h1 class="h3 mb-0">Account-Wide Google Search Performance Report (Discover & Web)</h1>
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
    df_table = df.copy() 
    df_table['discover_clicks'] = df_table['discover_clicks'].apply(lambda x: f"{x:,.0f}")
    df_table['discover_impressions'] = df_table['discover_impressions'].apply(lambda x: f"{x:,.0f}")
    df_table['discover_ctr'] = df_table['discover_ctr'].apply(lambda x: f"{x:.2%}")
    df_table['web_clicks'] = df_table['web_clicks'].apply(lambda x: f"{x:,.0f}")
    df_table['web_impressions'] = df_table['web_impressions'].apply(lambda x: f"{x:,.0f}")
    df_table['web_ctr'] = df_table['web_ctr'].apply(lambda x: f"{x:.2%}")
    df_table['total_clicks'] = df_table['total_clicks'].apply(lambda x: f"{x:,.0f}")
    df_table['total_impressions'] = df_table['total_impressions'].apply(lambda x: f"{x:,.0f}")
    df_table['total_ctr'] = df_table['total_ctr'].apply(lambda x: f"{x:.2%}")

    report_body = df_table.to_html(classes="table table-striped table-hover", index=False, border=0)

    # Prepare data for the chart (use the original unformatted dataframe for numerical values)
    chart_data = df.sort_values(by='month').to_json(orient='records')

    return f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Google Search Performance Report (Discover & Web) for {report_title}</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body {{ padding-top: 56px; }} /* Offset for fixed header */
        h1 {{ border-bottom: 2px solid #dee2e6; padding-bottom: .5rem; }}
        h2 {{ border-bottom: 2px solid #dee2e6; padding-bottom: .5rem; margin-top: 2rem; }}
        .table thead th {{ background-color: #434343; color: #ffffff; text-align: left; }}
        footer {{ margin-top: 3rem; text-align: center; color: #6c757d; }}
    </style>
</head>
<body>
    <header class="navbar navbar-expand-lg navbar-light bg-light border-bottom mb-4 fixed-top">
        <div class="container-fluid">
            <h1 class="h3 mb-0">Google Search Performance Report (Discover & Web) for {report_title}</h1>
        </div>
    </header>
    <main class="container-fluid py-4 flex-grow-1">
        <p class="text-muted">Analysis for the period: {full_period_str}</p>
        <div class="card my-4">
            <div class="card-header"><h3>Total Clicks vs. Total Impressions</h3></div>
            <div class="card-body"><canvas id="performanceChart"></canvas></div>
        </div>
        <div class="card my-4">
            <div class="card-header"><h3>Discover Clicks vs. Web Clicks</h3></div>
            <div class="card-body"><canvas id="clicksChart"></canvas></div>
        </div>
        <div class="card my-4">
            <div class="card-header"><h3>Discover Impressions vs. Web Impressions</h3></div>
            <div class="card-body"><canvas id="impressionsChart"></canvas></div>
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
                        label: 'Total Clicks',
                        data: data.map(row => row.total_clicks),
                        borderColor: 'rgba(54, 162, 235, 1)',
                        backgroundColor: 'rgba(54, 162, 235, 0.2)',
                        yAxisID: 'yClicks',
                        fill: false,
                        tension: 0.1
                    }},
                    {{
                        label: 'Total Impressions',
                        data: data.map(row => row.total_impressions),
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
                            text: 'Total Clicks'
                        }}
                    }},
                    yImpressions: {{
                        type: 'linear',
                        display: true,
                        position: 'right',
                        title: {{
                            display: true,
                            text: 'Total Impressions'
                        }},
                        grid: {{
                            drawOnChartArea: false, // only draw grid for the first Y axis
                        }}
                    }}
                }}
            }}
        }});

        new Chart(document.getElementById('clicksChart'), {{
            type: 'line',
            data: {{
                labels: labels,
                datasets: [
                    {{
                        label: 'Discover Clicks',
                        data: data.map(row => row.discover_clicks),
                        borderColor: 'rgba(75, 192, 192, 1)',
                        backgroundColor: 'rgba(75, 192, 192, 0.2)',
                        fill: false,
                        tension: 0.1
                    }},
                    {{
                        label: 'Web Clicks',
                        data: data.map(row => row.web_clicks),
                        borderColor: 'rgba(153, 102, 255, 1)',
                        backgroundColor: 'rgba(153, 102, 255, 0.2)',
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
                    y: {{
                        beginAtZero: true,
                        title: {{
                            display: true,
                            text: 'Clicks'
                        }}
                    }}
                }}
            }}
        }});

        new Chart(document.getElementById('impressionsChart'), {{
            type: 'line',
            data: {{
                labels: labels,
                datasets: [
                    {{
                        label: 'Discover Impressions',
                        data: data.map(row => row.discover_impressions),
                        borderColor: 'rgba(255, 159, 64, 1)',
                        backgroundColor: 'rgba(255, 159, 64, 0.2)',
                        fill: false,
                        tension: 0.1
                    }},
                    {{
                        label: 'Web Impressions',
                        data: data.map(row => row.web_impressions),
                        borderColor: 'rgba(201, 203, 207, 1)',
                        backgroundColor: 'rgba(201, 203, 207, 0.2)',
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
                    y: {{
                        beginAtZero: true,
                        title: {{
                            display: true,
                            text: 'Impressions'
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
        # Filter data for the current site and format it for display
        site_df = df[df['site_url'] == site].drop(columns=['site_url']).copy()
        
        # Format numeric columns for display
        site_df['discover_clicks'] = site_df['discover_clicks'].apply(lambda x: f"{x:,.0f}")
        site_df['discover_impressions'] = site_df['discover_impressions'].apply(lambda x: f"{x:,.0f}")
        site_df['discover_ctr'] = site_df['discover_ctr'].apply(lambda x: f"{x:.2%}")
        site_df['web_clicks'] = site_df['web_clicks'].apply(lambda x: f"{x:,.0f}")
        site_df['web_impressions'] = site_df['web_impressions'].apply(lambda x: f"{x:,.0f}")
        site_df['web_ctr'] = site_df['web_ctr'].apply(lambda x: f"{x:.2%}")
        site_df['total_clicks'] = site_df['total_clicks'].apply(lambda x: f"{x:,.0f}")
        site_df['total_impressions'] = site_df['total_impressions'].apply(lambda x: f"{x:,.0f}")
        site_df['total_ctr'] = site_df['total_ctr'].apply(lambda x: f"{x:.2%}")

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
    """Main function to run the consolidated performance analysis."""
    parser = argparse.ArgumentParser(description='Run a monthly consolidated Discover and Web performance analysis for a GSC property.')
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
        file_prefix = f"consolidated-performance-{host_dir.replace('.', '-')}-{most_recent_month}"
    else:
        output_dir = os.path.join('output', 'account')
        file_prefix = f"consolidated-performance-account-wide-{most_recent_month}"

    os.makedirs(output_dir, exist_ok=True)
    csv_output_path = os.path.join(output_dir, f'{file_prefix}.csv')
    html_output_path = os.path.join(output_dir, f'{file_prefix}.html')

    df = None
    sites = []

    if args.use_cache and os.path.exists(csv_output_path):
        print(f"Found cached data at {csv_output_path}. Using it to generate report.")
        df = pd.read_csv(csv_output_path)
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
            for i in range(1, 17): # Last 16 months
                end_of_month = today.replace(day=1) - relativedelta(months=i - 1) - timedelta(days=1)
                start_of_month = end_of_month.replace(day=1)
                start_date = start_of_month.strftime('%Y-%m-%d')
                end_date = end_of_month.strftime('%Y-%m-%d')

                print(f"  Fetching for {start_of_month.strftime('%Y-%m')}:")
                discover_data = get_monthly_performance_data(service, site_url, start_date, end_date, 'discover')
                web_data = get_monthly_performance_data(service, site_url, start_date, end_date, 'web')

                if discover_data == "PERMISSION_DENIED" or web_data == "PERMISSION_DENIED":
                    break # Stop processing this site if permission is denied for either

                # Initialize data with zeros if None (meaning no data for that search type)
                discover_data = discover_data if discover_data is not None else {'clicks': 0, 'impressions': 0, 'ctr': 0.0}
                web_data = web_data if web_data is not None else {'clicks': 0, 'impressions': 0, 'ctr': 0.0}

                total_clicks = discover_data['clicks'] + web_data['clicks']
                total_impressions = discover_data['impressions'] + web_data['impressions']
                total_ctr = total_clicks / total_impressions if total_impressions > 0 else 0.0

                all_data.append({
                    'site_url': site_url,
                    'month': start_of_month.strftime('%Y-%m'),
                    'discover_clicks': discover_data['clicks'],
                    'discover_impressions': discover_data['impressions'],
                    'discover_ctr': discover_data['ctr'],
                    'web_clicks': web_data['clicks'],
                    'web_impressions': web_data['impressions'],
                    'web_ctr': web_data['ctr'],
                    'total_clicks': total_clicks,
                    'total_impressions': total_impressions,
                    'total_ctr': total_ctr
                })
        
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
            html_output = create_multi_site_html_report(df.copy(), sites) # Pass a copy to avoid modifying original df
        
        with open(html_output_path, 'w', encoding='utf-8') as f:
            f.write(html_output)
        print(f"Successfully created HTML report at {html_output_path}")
    except PermissionError:
        print(f"\nError: Permission denied when writing to the output directory.")

if __name__ == '__main__':
    main()
