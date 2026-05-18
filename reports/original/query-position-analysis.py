"""
Performs an account-wide or single-site analysis of Google Search Console data,
gathering query position distribution metrics for each complete calendar month.

This script authenticates with the GSC API. It can either process all sites in an
account or a specific site URL provided as an argument. For each site, it retrieves
query data and processes it to show clicks and impressions in position buckets
(1-3, 4-10, 11-20, 21+).

The data is compiled into a CSV file and an HTML report.
"""

import os
import pandas as pd
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.auth import exceptions
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
    return sites

def get_monthly_query_data(service, site_url, start_date, end_date):
    """Fetches query performance data from GSC for a given date range."""
    all_query_data = []
    try:
        request = {'startDate': start_date, 'endDate': end_date, 'dimensions': ['query'], 'rowLimit': 25000, 'startRow': 0}
        while True:
            response = service.searchanalytics().query(siteUrl=site_url, body=request).execute()
            if 'rows' in response:
                all_query_data.extend(response['rows'])
                if len(response['rows']) < request['rowLimit']:
                    break
                request['startRow'] += request['rowLimit']
            else:
                break
    except HttpError as e:
        if e.resp.status == 403:
            print(f"Warning: Insufficient permission for {site_url}.")
            return "PERMISSION_DENIED"
        print(f"An HTTP error occurred for {site_url}: {e}")
    return all_query_data

def process_query_data_into_position_distribution(query_data):
    """Processes raw query data into aggregated clicks and impressions for position ranges."""
    distribution = {
        'clicks_pos_1_3': 0, 'impressions_pos_1_3': 0,
        'clicks_pos_4_10': 0, 'impressions_pos_4_10': 0,
        'clicks_pos_11_20': 0, 'impressions_pos_11_20': 0,
        'clicks_pos_21_plus': 0, 'impressions_pos_21_plus': 0,
        'total_clicks': 0, 'total_impressions': 0
    }
    for row in query_data:
        clicks, impressions, position = row.get('clicks', 0), row.get('impressions', 0), row.get('position', 0)
        if position >= 1:
            distribution['total_clicks'] += clicks
            distribution['total_impressions'] += impressions
            if 1 <= position <= 3:
                distribution['clicks_pos_1_3'] += clicks
                distribution['impressions_pos_1_3'] += impressions
            elif 4 <= position <= 10:
                distribution['clicks_pos_4_10'] += clicks
                distribution['impressions_pos_4_10'] += impressions
            elif 11 <= position <= 20:
                distribution['clicks_pos_11_20'] += clicks
                distribution['impressions_pos_11_20'] += impressions
            elif position >= 21:
                distribution['clicks_pos_21_plus'] += clicks
                distribution['impressions_pos_21_plus'] += impressions
    return distribution

def create_multi_site_html_report(df, sorted_sites, period_str):
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
<title>Google Organic Query Position Distribution Report</title><link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
<style>body{{padding:2rem;}}.table-responsive{{max-height:800px;}}h1,h2{{border-bottom:2px solid #dee2e6;padding-bottom:.5rem;margin-top:2rem;}}footer{{margin-top:3rem;text-align:center;color:#6c757d;}}</style></head>
<body><div class="container-fluid"><h1 id="top">Google Organic Query Position Distribution Report</h1>
<p class="text-muted">Analysis for the period: {period_str}</p>
<h2>Index</h2>{index_html}{site_sections_html}</div>
<footer><p><a href="https://github.com/liamdelahunty/gsc-exporter" target="_blank">gsc-exporter</a></p></footer></body></html>"""

def create_single_site_html_report(df, report_title, period_str):
    """Generates a simplified HTML report for a single site with charts."""
    # Prepare data for the table
    df_table = df.drop(columns=['site_url']).copy()
    for col in df_table.columns:
        if ('clicks' in col or 'impressions' in col):
            df_table[col] = df_table[col].apply(lambda x: f"{x:,.0f}")
    report_body = df_table.to_html(classes="table table-striped table-hover", index=False, border=0)

    # Prepare data for charts
    chart_data = df.sort_values(by='month').to_json(orient='records')

    return f"""
<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Google Organic Query Position Report for {report_title}</title><link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<style>body{{padding:2rem;}}h1,h2{{border-bottom:2px solid #dee2e6;padding-bottom:.5rem;margin-top:2rem;}}.table thead th {{background-color: #434343;color: #ffffff;text-align: left;}}footer{{margin-top:3rem;text-align:center;color:#6c757d;}}</style></head>
<body><div class="container-fluid"><h1>Google Organic Query Position Report for {report_title}</h1>
<p class="text-muted">Analysis for the period: {period_str}</p>
<div class="row my-4">
    <div class="col-lg-6"><div class="card"><div class="card-header"><h3>Clicks by Position</h3></div><div class="card-body"><canvas id="clicksChart"></canvas></div></div></div>
    <div class="col-lg-6"><div class="card"><div class="card-header"><h3>Impressions by Position</h3></div><div class="card-body"><canvas id="impressionsChart"></canvas></div></div></div>
</div>
<div class="row my-4">
    <div class="col-lg-6"><div class="card"><div class="card-header"><h3>Stacked Clicks by Position</h3></div><div class="card-body"><canvas id="stackedClicksChart"></canvas></div></div></div>
    <div class="col-lg-6"><div class="card"><div class="card-header"><h3>Stacked Impressions by Position</h3></div><div class="card-body"><canvas id="stackedImpressionsChart"></canvas></div></div></div>
</div>
<div class="row my-4">
    <div class="col-lg-6"><div class="card"><div class="card-header"><h3>Total Clicks</h3></div><div class="card-body"><canvas id="totalClicksChart"></canvas></div></div></div>
    <div class="col-lg-6"><div class="card"><div class="card-header"><h3>Total Impressions</h3></div><div class="card-body"><canvas id="totalImpressionsChart"></canvas></div></div></div>
</div>
<h2>Data Table</h2>
<p class="text-muted">
    <strong>Note:</strong> Totals in this table are the sum of a query-level data export. Due to API filtering of anonymised long-tail queries, these totals may be slightly lower than the property-wide totals shown in the Key Performance Metrics report.
</p>
<div class="table-responsive">{report_body}</div></div>
<footer><p><a href="https://github.com/liamdelahunty/gsc-exporter" target="_blank">gsc-exporter</a></p></footer>
<script>
    const data = {chart_data};
    const labels = data.map(row => row.month);
    const chartConfig = {{
        'clicks': {{
            'element': 'clicksChart',
            'datasets': [
                {{'label': 'Clicks Pos 1-3', 'data': data.map(row => row.clicks_pos_1_3), 'borderColor': 'rgba(75, 192, 192, 1)'}},
                {{'label': 'Clicks Pos 4-10', 'data': data.map(row => row.clicks_pos_4_10), 'borderColor': 'rgba(54, 162, 235, 1)'}},
                {{'label': 'Clicks Pos 11-20', 'data': data.map(row => row.clicks_pos_11_20), 'borderColor': 'rgba(255, 206, 86, 1)'}},
                {{'label': 'Clicks Pos 21+', 'data': data.map(row => row.clicks_pos_21_plus), 'borderColor': 'rgba(255, 99, 132, 1)'}}
            ],
            'options': {{ scales: {{ y: {{ beginAtZero: true }} }} }}
        }},
        'impressions': {{
            'element': 'impressionsChart',
            'datasets': [
                {{'label': 'Impressions Pos 1-3', 'data': data.map(row => row.impressions_pos_1_3), 'borderColor': 'rgba(75, 192, 192, 1)'}},
                {{'label': 'Impressions Pos 4-10', 'data': data.map(row => row.impressions_pos_4_10), 'borderColor': 'rgba(54, 162, 235, 1)'}},
                {{'label': 'Impressions Pos 11-20', 'data': data.map(row => row.impressions_pos_11_20), 'borderColor': 'rgba(255, 206, 86, 1)'}},
                {{'label': 'Impressions Pos 21+', 'data': data.map(row => row.impressions_pos_21_plus), 'borderColor': 'rgba(255, 99, 132, 1)'}}
            ],
            'options': {{ scales: {{ y: {{ beginAtZero: true }} }} }}
        }},
        'stacked_clicks': {{
            'element': 'stackedClicksChart',
            'datasets': [
                {{'label': 'Clicks Pos 1-3', 'data': data.map(row => row.clicks_pos_1_3), 'borderColor': 'rgba(75, 192, 192, 1)', 'backgroundColor': 'rgba(75, 192, 192, 0.5)'}},
                {{'label': 'Clicks Pos 4-10', 'data': data.map(row => row.clicks_pos_4_10), 'borderColor': 'rgba(54, 162, 235, 1)', 'backgroundColor': 'rgba(54, 162, 235, 0.5)'}},
                {{'label': 'Clicks Pos 11-20', 'data': data.map(row => row.clicks_pos_11_20), 'borderColor': 'rgba(255, 206, 86, 1)', 'backgroundColor': 'rgba(255, 206, 86, 0.5)'}},
                {{'label': 'Clicks Pos 21+', 'data': data.map(row => row.clicks_pos_21_plus), 'borderColor': 'rgba(255, 99, 132, 1)', 'backgroundColor': 'rgba(255, 99, 132, 0.5)'}}
            ],
            'options': {{ scales: {{ y: {{ stacked: true, beginAtZero: true }} }} }}
        }},
        'stacked_impressions': {{
            'element': 'stackedImpressionsChart',
            'datasets': [
                {{'label': 'Impressions Pos 1-3', 'data': data.map(row => row.impressions_pos_1_3), 'borderColor': 'rgba(75, 192, 192, 1)', 'backgroundColor': 'rgba(75, 192, 192, 0.5)'}},
                {{'label': 'Impressions Pos 4-10', 'data': data.map(row => row.impressions_pos_4_10), 'borderColor': 'rgba(54, 162, 235, 1)', 'backgroundColor': 'rgba(54, 162, 235, 0.5)'}},
                {{'label': 'Impressions Pos 11-20', 'data': data.map(row => row.impressions_pos_11_20), 'borderColor': 'rgba(255, 206, 86, 1)', 'backgroundColor': 'rgba(255, 206, 86, 0.5)'}},
                {{'label': 'Impressions Pos 21+', 'data': data.map(row => row.impressions_pos_21_plus), 'borderColor': 'rgba(255, 99, 132, 1)', 'backgroundColor': 'rgba(255, 99, 132, 0.5)'}}
            ],
            'options': {{ scales: {{ y: {{ stacked: true, beginAtZero: true }} }} }}
        }},
        'total_clicks': {{
            'element': 'totalClicksChart',
            'datasets': [
                {{'label': 'Total Clicks', 'data': data.map(row => row.total_clicks), 'borderColor': 'rgba(153, 102, 255, 1)'}}
            ],
            'options': {{ scales: {{ y: {{ beginAtZero: true }} }} }}
        }},
        'total_impressions': {{
            'element': 'totalImpressionsChart',
            'datasets': [
                {{'label': 'Total Impressions', 'data': data.map(row => row.total_impressions), 'borderColor': 'rgba(255, 159, 64, 1)'}}
            ],
            'options': {{ scales: {{ y: {{ beginAtZero: true }} }} }}
        }}
    }};
    for (const [key, config] of Object.entries(chartConfig)) {{
        const isStacked = key.startsWith('stacked');
        new Chart(document.getElementById(config.element), {{
            type: 'line',
            data: {{
                labels: labels,
                datasets: config.datasets.map(ds => ({{...ds, fill: isStacked, tension: 0.1}}))
            }},
            options: config.options
        }});
    }}
</script>
</body></html>"""

def generate_site_sections(df, sorted_sites):
    """Generates HTML sections for each site, including charts."""
    sections_html = ''
    for i, site in enumerate(sorted_sites):
        anchor = site.replace('https://', '').replace('http://', '').replace(':', '-').replace('/', '-').replace('.', '-')
        sections_html += f'<h2 id="{anchor}" class="mt-5">{site}</h2>'
        site_df = df[df['site_url'] == site].drop(columns=['site_url'])
        
        if not site_df.empty:
            # Chart data
            chart_data_json = site_df.sort_values(by='month').to_json(orient='records')
            
            # Table data
            table_df = site_df.copy()
            for col in table_df.columns:
                if ('clicks' in col or 'impressions' in col):
                    table_df[col] = table_df[col].apply(lambda x: f"{{x:,.0f}}")
            
            table_html = table_df.to_html(classes="table table-striped table-hover", index=False, border=0)

            sections_html += f"""
            <div class="row my-4">
                <div class="col-lg-6"><div class="card"><div class="card-header"><h3>Clicks by Position</h3></div><div class="card-body"><canvas id="clicksChart-{i}"></canvas></div></div></div>
                <div class="col-lg-6"><div class="card"><div class="card-header"><h3>Impressions by Position</h3></div><div class="card-body"><canvas id="impressionsChart-{i}"></canvas></div></div></div>
            </div>
            <div class="row my-4">
                <div class="col-lg-6"><div class="card"><div class="card-header"><h3>Total Clicks</h3></div><div class="card-body"><canvas id="totalClicksChart-{i}"></canvas></div></div></div>
                <div class="col-lg-6"><div class="card"><div class="card-header"><h3>Total Impressions</h3></div><div class="card-body"><canvas id="totalImpressionsChart-{i}"></canvas></div></div></div>
            </div>
            <h2>Data Table for {site}</h2>
            <p class="text-muted">
                <strong>Note:</strong> Totals in this table are the sum of a query-level data export. Due to API filtering of anonymised long-tail queries, these totals may be slightly lower than the property-wide totals shown in the Key Performance Metrics report.
            </p>
            <div class="table-responsive">{table_html}</div>
            <p><a href="#top">Back to Top</a></p>
            <script>
                (function() {{
                    const data = {chart_data_json};
                    const labels = data.map(row => row.month);
                    const chartConfig = {{
                        'clicks': {{
                            'element': 'clicksChart-{i}',
                            'datasets': [
                                {{'label': 'Clicks Pos 1-3', 'data': data.map(row => row.clicks_pos_1_3), 'borderColor': 'rgba(75, 192, 192, 1)'}},
                                {{'label': 'Clicks Pos 4-10', 'data': data.map(row => row.clicks_pos_4_10), 'borderColor': 'rgba(54, 162, 235, 1)'}},
                                {{'label': 'Clicks Pos 11-20', 'data': data.map(row => row.clicks_pos_11_20), 'borderColor': 'rgba(255, 206, 86, 1)'}},
                                {{'label': 'Clicks Pos 21+', 'data': data.map(row => row.clicks_pos_21_plus), 'borderColor': 'rgba(255, 99, 132, 1)'}}
                            ]
                        }},
                        'impressions': {{
                            'element': 'impressionsChart-{i}',
                            'datasets': [
                                {{'label': 'Impressions Pos 1-3', 'data': data.map(row => row.impressions_pos_1_3), 'borderColor': 'rgba(75, 192, 192, 1)'}},
                                {{'label': 'Impressions Pos 4-10', 'data': data.map(row => row.impressions_pos_4_10), 'borderColor': 'rgba(54, 162, 235, 1)'}},
                                {{'label': 'Impressions Pos 11-20', 'data': data.map(row => row.impressions_pos_11_20), 'borderColor': 'rgba(255, 206, 86, 1)'}},
                                {{'label': 'Impressions Pos 21+', 'data': data.map(row => row.impressions_pos_21_plus), 'borderColor': 'rgba(255, 99, 132, 1)'}}
                            ]
                        }},
                        'total_clicks': {{
                            'element': 'totalClicksChart-{i}',
                            'datasets': [
                                {{'label': 'Total Clicks', 'data': data.map(row => row.total_clicks), 'borderColor': 'rgba(153, 102, 255, 1)'}}
                            ]
                        }},
                        'total_impressions': {{
                            'element': 'totalImpressionsChart-{i}',
                            'datasets': [
                                {{'label': 'Total Impressions', 'data': data.map(row => row.total_impressions), 'borderColor': 'rgba(255, 159, 64, 1)'}}
                            ]
                        }}
                    }};
                    for (const [key, config] of Object.entries(chartConfig)) {{
                        new Chart(document.getElementById(config.element), {{
                            type: 'line',
                            data: {{
                                labels: labels,
                                datasets: config.datasets.map(ds => ({{...ds, fill: false, tension: 0.1}}))
                            }},
                            options: {{ scales: {{ y: {{ beginAtZero: true }} }} }}
                        }});
                    }}
                }})();
            </script>
            """
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
    parser = argparse.ArgumentParser(description='Run a query position analysis for a GSC property.')
    parser.add_argument('site_url', nargs='?', default=None, help='The URL of the site to analyse. If not provided, runs for all sites.')
    parser.add_argument('--use-cache', action='store_true', help='Use a cached CSV file from a previous run if it exists.')
    args = parser.parse_args()

    today = date.today()
    most_recent_month = (today.replace(day=1) - timedelta(days=1)).strftime('%Y-%m')

    if args.site_url:
        site = args.site_url
        if site.startswith('sc-domain:'):
            host_plain = site.replace('sc-domain:', '')
        else:
            host_plain = urlparse(site).netloc
        
        host_dir = host_plain.replace('www.', '')
        output_dir = os.path.join('output', host_dir)
        file_prefix = f"query-position-analysis-{host_dir.replace('.', '-')}-{most_recent_month}"
    else:
        output_dir = os.path.join('output', 'account')
        file_prefix = f"query-position-analysis-account-wide-{most_recent_month}"

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
        
        for site_url in sites:
            print(f"\nFetching data for site: {site_url}")
            for i in range(1, 17):
                end_of_month = today.replace(day=1) - relativedelta(months=i - 1) - timedelta(days=1)
                start_of_month = end_of_month.replace(day=1)
                start_date = start_of_month.strftime('%Y-%m-%d')
                end_date = end_of_month.strftime('%Y-%m-%d')

                query_data = get_monthly_query_data(service, site_url, start_date, end_date)
                if query_data == "PERMISSION_DENIED":
                    break
                elif query_data:
                    distribution_data = process_query_data_into_position_distribution(query_data)
                    distribution_data['site_url'] = site_url
                    distribution_data['month'] = start_of_month.strftime('%Y-%m')
                    all_data.append(distribution_data)
        
        if not all_data:
            print("No performance data found.")
            return

        df = pd.DataFrame(all_data)
        csv_column_order = ['site_url', 'month', 'clicks_pos_1_3', 'impressions_pos_1_3', 'clicks_pos_4_10', 
                            'impressions_pos_4_10', 'clicks_pos_11_20', 'impressions_pos_11_20', 
                            'clicks_pos_21_plus', 'impressions_pos_21_plus', 'total_clicks', 'total_impressions']
        df = df.reindex(columns=csv_column_order)

        try:
            df.to_csv(csv_output_path, index=False)
            print(f"\nSuccessfully exported CSV to {csv_output_path}")
            print(f"Hint: To recreate this report from the saved data, use the --use-cache flag.")
        except PermissionError:
            print(f"\nError: Permission denied when writing to the output directory.")
            return
            
    # Proceed with report generation
    try:
        start_month = pd.to_datetime(df['month']).min().strftime('%Y-%m')
        end_month = pd.to_datetime(df['month']).max().strftime('%Y-%m')
        period_str = f"{start_month} to {end_month}"

        if args.site_url:
            df_single = df[df['site_url'] == args.site_url]
            html_output = create_single_site_html_report(df_single, args.site_url, period_str)
        else:
            html_output = create_multi_site_html_report(df, sites, period_str)
        
        with open(html_output_path, 'w', encoding='utf-8') as f:
            f.write(html_output)
        print(f"Successfully created HTML report at {html_output_path}")
    except PermissionError:
        print(f"\nError: Permission denied when writing to the output directory.")

if __name__ == '__main__':
    main()
