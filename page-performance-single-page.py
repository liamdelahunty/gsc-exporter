"""
Generates a report showing the performance of a single page over the last 16 months.

This script fetches the performance data for a given page for each of the last 16 complete months
to show trends over time.

Usage:
    python page-performance-single-page.py <page_url>
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
import re

# --- Configuration ---
SCOPES = ['https://www.googleapis.com/auth/webmasters.readonly']
CLIENT_SECRET_FILE = 'client_secret.json'
TOKEN_FILE = 'token.json'

def get_gsc_service():
    """Authenticates and returns a Google Search Console service object."""
    creds = None
    if os.path.exists(TOKEN_FILE):
        try:
            creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
        except Exception as e:
            print(f"Could not load credentials from {TOKEN_FILE}. Error: {e}")
            print("Will attempt to re-authenticate.")
            creds = None

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except exceptions.RefreshError as e:
                print(f"Error refreshing token: {e}")
                print("The refresh token is expired or revoked. Deleting it and re-authenticating.")
                if os.path.exists(TOKEN_FILE):
                    os.remove(TOKEN_FILE)
                creds = None
        
        if not creds:
            if not os.path.exists(CLIENT_SECRET_FILE):
                print(f"Error: {CLIENT_SECRET_FILE} not found. Please follow setup instructions in README.md.")
                return None
            
            print("A browser window will open for you to authorize access.")
            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        
        with open(TOKEN_FILE, 'w') as token:
            token.write(creds.to_json())
            print("Authentication successful. Credentials saved.")

    return build('webmasters', 'v3', credentials=creds)

def get_latest_available_gsc_date(service, site_url, max_retries=5):
    """
    Determines the latest date for which GSC data is available by querying
    backwards from today.
    """
    current_date = date.today()
    for i in range(max_retries):
        check_date = current_date - timedelta(days=i)
        check_date_str = check_date.strftime('%Y-%m-%d')
        
        print(f"Checking for GSC data availability on: {check_date_str}...")
        try:
            request = {
                'startDate': check_date_str,
                'endDate': check_date_str,
                'dimensions': ['date'], # Only need to check for any data
                'rowLimit': 1,
                'startRow': 0
            }
            response = service.searchanalytics().query(siteUrl=site_url, body=request).execute()
            
            if 'rows' in response and response['rows']:
                print(f"Latest available GSC data found for: {check_date_str}")
                return check_date
            else:
                print(f"No data for {check_date_str}, checking previous day.")
        except HttpError as e:
            if e.resp.status == 400:
                print(f"No data for {check_date_str}, checking previous day (HTTP 400).")
            else:
                print(f"An HTTP error occurred while checking date {check_date_str}: {e}")
        except Exception as e:
            print(f"An unexpected error occurred while checking date {check_date_str}: {e}")
            
    print(f"Could not determine latest available GSC date within {max_retries} days. Using today's date as a fallback.")
    return current_date

def get_gsc_data(service, site_url, start_date, end_date, dimensions, filters=None):
    """Fetches performance data from GSC for a given date range and dimensions."""
    all_data = []
    start_row = 0
    row_limit = 25000 
    
    print(f"Fetching data for dimensions: {', '.join(dimensions)} from {start_date} to {end_date}...")

    request_body = {
        'startDate': start_date,
        'endDate': end_date,
        'dimensions': dimensions,
        'rowLimit': row_limit,
        'startRow': start_row
    }

    if filters:
        request_body['dimensionFilterGroups'] = [{'filters': filters}]

    while True:
        try:
            request_body['startRow'] = start_row
            response = service.searchanalytics().query(siteUrl=site_url, body=request_body).execute()

            if 'rows' in response:
                rows = response['rows']
                all_data.extend(rows)
                print(f"Retrieved {len(rows)} rows... (Total: {len(all_data)})")
                if len(rows) < row_limit:
                    break 
                start_row += row_limit
            else:
                break
        except HttpError as e:
            print(f"An HTTP error occurred: {e}")
            return None
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
            return None
            
    if not all_data:
        return pd.DataFrame()

    df = pd.DataFrame(all_data)
    # Ensure keys are always returned as a list, even for a single dimension
    if isinstance(df['keys'].iloc[0], list):
        df[dimensions] = pd.DataFrame(df['keys'].tolist(), index=df.index)
    else:
        df[dimensions[0]] = df['keys']
        
    df = df.drop(columns=['keys'])
    
    for col in ['clicks', 'impressions', 'ctr', 'position']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        
    return df

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

def find_covering_site(page_url, all_sites):
    """
    Finds the most appropriate GSC site property that covers the given page_url.
    Prioritizes exact matches, then domain properties, then URL prefixes.
    """
    parsed_page_url = urlparse(page_url)
    page_domain = parsed_page_url.netloc

    # List to store potential matches with their 'score' (longer matches are better)
    potential_matches = []

    for site in all_sites:
        if site.startswith('sc-domain:'):
            site_domain = site.replace('sc-domain:', '')
            if page_domain == site_domain or page_domain.endswith(f".{site_domain}"):
                # Score based on how specific the domain property is (e.g., sc-domain:example.com for www.example.com)
                potential_matches.append((site, len(site_domain), "domain"))
        else: # URL prefix property
            if page_url.startswith(site):
                # Score based on the length of the matching prefix
                potential_matches.append((site, len(site), "prefix"))
            elif page_domain == urlparse(site).netloc: # Fallback to domain match if not a direct prefix
                 potential_matches.append((site, len(urlparse(site).netloc), "domain_fallback"))

    # Sort matches: prefer prefix matches over domain matches, then by length (longer is better)
    # This logic might need fine-tuning based on GSC's exact matching rules for properties
    potential_matches.sort(key=lambda x: (x[2] == "prefix", x[1]), reverse=True)

    if potential_matches:
        best_match_site = potential_matches[0][0]
        print(f"Found GSC property '{best_match_site}' for page '{page_url}'.")
        return best_match_site
    
    print(f"No suitable GSC property found for page '{page_url}'.")
    return None

def create_html_report(page_url, site_url, start_date, end_date, df_combined):
    """Generates an HTML report from the pivoted dataframes with combined table and page link."""

    report_title = f"Page Performance Over Time Report for {page_url}"

    # Prepare data for the chart (use the original unformatted dataframe for numerical values)
    if not df_combined.empty:
        page_data_clicks = df_combined['clicks'].loc[page_url].to_dict()
        page_data_impressions = df_combined['impressions'].loc[page_url].to_dict()
        page_data_ctr = df_combined['ctr'].loc[page_url].to_dict()
        page_data_position = df_combined['position'].loc[page_url].to_dict()

        chart_data_list = []
        for month in sorted(page_data_clicks.keys()):
            chart_data_list.append({
                'month': month,
                'clicks': page_data_clicks.get(month, 0),
                'impressions': page_data_impressions.get(month, 0),
                'ctr': page_data_ctr.get(month, 0.0),
                'position': page_data_position.get(month, 0.0)
            })
        chart_data_json = pd.DataFrame(chart_data_list).to_json(orient='records')
    else:
        chart_data_json = "[]"

    # Create a single combined DataFrame for the HTML table
    # Select data for the specific page_url and unstack to get months as index and metrics as columns
    df_table_data = df_combined.loc[page_url].unstack(level=0)
    df_table_data = df_table_data[['clicks', 'impressions', 'ctr', 'position']] # Ensure order
    df_table_data.index.name = 'Month'
    df_table_data = df_table_data.reset_index()

    # Format numeric columns for display
    df_table_data['clicks'] = df_table_data['clicks'].apply(lambda x: f"{int(x):,}")
    df_table_data['impressions'] = df_table_data['impressions'].apply(lambda x: f"{int(x):,}")
    df_table_data['ctr'] = df_table_data['ctr'].apply(lambda x: f"{x:.2%}")
    df_table_data['position'] = df_table_data['position'].apply(lambda x: f"{x:.2f}")

    combined_table_html = df_table_data.to_html(classes="table table-striped table-hover", index=False, border=0)
    
    return f"""
<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{report_title}</title><link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<style>
body {{ padding-top: 56px; }}
h2 {{ border-bottom: 2px solid #dee2e6; padding-bottom: .5rem; margin-top: 2rem; }}
.table-responsive {{ max-height: 600px; }}
.table thead th {{ text-align: center; }} /* Center align all header cells */
.table thead th:first-child {{ text-align: left; }} /* Left align the first header cell (Page) */
.table tbody td:first-child {{ text-align: left; }} /* Left align the first data cell (Page URL) */

.table-container {{
    max-height: 400px; /* Adjust as needed */
    overflow-y: auto;
    position: relative;
    border: 1px solid #dee2e6;
    border-radius: .25rem;
}}

.table-container table {{
    margin-bottom: 0;
}}

.table-container thead th {{
    position: sticky;
    top: 0;
    background-color: #f8f9fa; /* Bootstrap's default table head background */
    z-index: 10;
    box-shadow: 0 2px 2px -1px rgba(0, 0, 0, 0.1);
}}
.chart-container {{
    position: relative;
    height: 40vh;
    width: 80vw;
    margin: auto;
}}
</style></head>
<body>
    <header class="navbar navbar-expand-lg navbar-light bg-light border-bottom mb-4 fixed-top">
        <div class="container-fluid">
            <div class="d-flex align-items-baseline">
                <h1 class="h3 mb-0 me-4">{report_title}</h1>
                <span class="text-muted me-4">Site: {site_url}</span>
                <span class="text-muted me-4">{start_date} to {end_date}</span>
            </div>
            <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbarNav" aria-controls="navbarNav" aria-expanded="false" aria-label="Toggle navigation">
                <span class="navbar-toggler-icon"></span>
            </button>
            <div class="collapse navbar-collapse" id="navbarNav">
                <ul class="navbar-nav ms-auto">
                    <li class="nav-item">
                        <a class="nav-link" href="../../resources/index.html">Resources</a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link" href="https://github.com/liamdelahunty/gsc-exporter" target="_blank">GitHub</a>
                    </li>
                </ul>
            </div>
        </div>
    </header>
    <main class="container-fluid py-4 flex-grow-1">
        <p class="mb-3"><a href="{page_url}" target="_blank" class="h5">{page_url}</a></p>
        <div class="row my-4">
            <div class="col-lg-12">
                <div class="card">
                    <div class="card-header"><h3>Clicks vs. Impressions</h3></div>
                    <div class="card-body chart-container"><canvas id="clicksImpressionsChart"></canvas></div>
                </div>
            </div>
        </div>
        <div class="row my-4">
            <div class="col-lg-6">
                <div class="card">
                    <div class="card-header"><h3>Average CTR</h3></div>
                    <div class="card-body chart-container"><canvas id="ctrChart"></canvas></div>
                </div>
            </div>
            <div class="col-lg-6">
                <div class="card">
                    <div class="card-header"><h3>Average Position</h3></div>
                    <div class="card-body chart-container"><canvas id="positionChart"></canvas></div>
                </div>
            </div>
        </div>

        <h2 class="mt-5">Performance Data</h2>
        <div class="table-responsive">
            {combined_table_html}
        </div>
    </main>
    <footer class="footer mt-auto py-3 bg-light">
        <div class="container text-center">
            <span class="text-muted">Report generated on {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</span>
        </div>
    </footer>
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"></script>
    <script>
        const data = {chart_data_json};
        const labels = data.map(row => row.month);

        // Clicks vs Impressions Chart
        new Chart(document.getElementById('clicksImpressionsChart'), {{
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
                interaction: {{ mode: 'index', intersect: false }},
                scales: {{
                    yClicks: {{
                        type: 'linear',
                        display: true,
                        position: 'left',
                        title: {{ display: true, text: 'Clicks' }}
                    }},
                    yImpressions: {{
                        type: 'linear',
                        display: true,
                        position: 'right',
                        title: {{ display: true, text: 'Impressions' }},
                        grid: {{ drawOnChartArea: false }}
                    }}
                }}
            }}
        }});

        // CTR Chart
        new Chart(document.getElementById('ctrChart'), {{
            type: 'line',
            data: {{
                labels: labels,
                datasets: [{{
                    label: 'CTR',
                    data: data.map(row => row.ctr * 100),
                    borderColor: 'rgba(75, 192, 192, 1)',
                    fill: false,
                    tension: 0.1
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {{ legend: {{ display: false }} }},
                scales: {{
                    y: {{
                        beginAtZero: true,
                        ticks: {{ callback: value => value + '%' }}
                    }}
                }}
            }}
        }});

        // Position Chart
        new Chart(document.getElementById('positionChart'), {{
            type: 'line',
            data: {{
                labels: labels,
                datasets: [{{
                    label: 'Position',
                    data: data.map(row => row.position),
                    borderColor: 'rgba(255, 159, 64, 1)',
                    fill: false,
                    tension: 0.1
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {{ legend: {{ display: false }} }},
                scales: {{
                    y: {{
                        reverse: true, // Invert y-axis for position
                        beginAtZero: false
                    }}
                }}
            }}
        }});
    </script>
</body></html>
"""

def main():
    """Main function to run the single page performance over time report."""
    parser = argparse.ArgumentParser(
        description='Generate a report on a single page\'s performance over time.',
        epilog='Example usage:\n'
               '  python page-performance-single-page.py https://www.example.com/page-a\n'
               '  python page-performance-single-page.py https://www.example.com/page-a --use-cache\n\n'
               'The --use-cache flag will use a previously downloaded CSV if available, '
               'avoiding re-downloading data from Google Search Console.'
    )
    parser.add_argument('page_url', help='The full URL of the page to analyse.')
    parser.add_argument('--use-cache', action='store_true', help='Use a cached CSV file from a previous run if it exists.')
    
    args = parser.parse_args()
    page_url = args.page_url

    service = get_gsc_service()
    if not service:
        return

    all_sites = get_all_sites(service)
    if not all_sites:
        print("No GSC sites found in your account. Please ensure you have properties set up and authenticated.")
        return

    site_url = find_covering_site(page_url, all_sites)
    if not site_url:
        print(f"Could not find a GSC property that covers the page URL: {page_url}. Please ensure the page belongs to a verified property in your GSC account.")
        return
    
    parsed_site_url = urlparse(site_url)
    host_plain = parsed_site_url.netloc

    # Use page_url hash to make cache and output filenames unique for this specific page
    page_hash = str(abs(hash(page_url)))[:10] # Short hash for the page URL
    host_dir = host_plain.replace('www.', '').replace('sc-domain:', '') # Handle sc-domain: prefix
    output_dir = os.path.join('output', host_dir)
    os.makedirs(output_dir, exist_ok=True)
    host_for_filename = host_dir.replace('.', '-')

    # Define a consistent file prefix for cached data
    cache_file_prefix = f"page-performance-single-page-{host_for_filename}-{page_hash}"
    csv_cache_path = os.path.join(output_dir, f"{cache_file_prefix}-cached.csv")

    df_combined = None
    if args.use_cache and os.path.exists(csv_cache_path):
        print(f"Found cached data at {csv_cache_path}. Using it to generate report.")
        # Load the combined dataframe from cache
        df_combined = pd.read_csv(csv_cache_path, header=[0,1], index_col=0) # Load with multi-index columns and index
        
        # Reconstruct the separate dataframes from the combined one
        df_pivot_clicks = df_combined['clicks']
        df_pivot_impressions = df_combined['impressions']
        df_pivot_ctr = df_combined['ctr']
        df_pivot_position = df_combined['position']

        # Determine the overall_start_date and overall_end_date from the loaded data for report generation
        # Assuming the columns are dates in YYYY-MM format
        if not df_pivot_clicks.empty:
            sorted_months = sorted(df_pivot_clicks.columns)
            overall_start_date = datetime.strptime(sorted_months[0], '%Y-%m').strftime('%Y-%m-%d')
            # The end date will be the last day of the last month in the sorted columns
            last_month_dt = datetime.strptime(sorted_months[-1], '%Y-%m')
            overall_end_date = (last_month_dt + relativedelta(months=1) - timedelta(days=1)).strftime('%Y-%m-%d')
        else:
            overall_start_date = "N/A"
            overall_end_date = "N/A"

    if df_combined is None: # Only fetch if not loaded from cache
        latest_available_date = get_latest_available_gsc_date(service, site_url)
        
        # 1. Determine the date range for the last full calendar month - no longer needed for identifying top pages
        
        all_monthly_data = []
        
        # 3. Fetch data for the last 16 full months for the given page
        for i in range(16):
            # Calculate start and end of each of the past 16 full months
            month_to_fetch_end = (latest_available_date.replace(day=1) - relativedelta(months=i)) - timedelta(days=1)
            month_to_fetch_start = month_to_fetch_end.replace(day=1)

            month_start_str = month_to_fetch_start.strftime('%Y-%m-%d')
            month_end_str = month_to_fetch_end.strftime('%Y-%m-%d')
            
            print(f"Fetching data for month: {month_start_str} to {month_end_str} for page: {page_url}...")
            
            page_filter = {
                'dimension': 'page',
                'operator': 'equals', # Changed to 'equals' for a single page
                'expression': page_url
            }
            
            # Request only 'page', 'date' dimensions for efficiency
            df_month = get_gsc_data(service, site_url, month_start_str, month_end_str, ['page', 'date'], filters=[page_filter])
            
            if df_month is not None and not df_month.empty:
                df_month['month'] = month_to_fetch_start.strftime('%Y-%m')
                all_monthly_data.append(df_month)

        if not all_monthly_data:
            print(f"No historical data found for the page: {page_url}.")
            return

        df_historical = pd.concat(all_monthly_data, ignore_index=True)

        # 4. Pivot the data to have pages as rows and monthly metrics as columns
        # For a single page report, the index will already be the page, but pivot for consistency
        df_pivot_clicks = df_historical.pivot_table(index='page', columns='month', values='clicks', aggfunc='sum').fillna(0)
        df_pivot_impressions = df_historical.pivot_table(index='page', columns='month', values='impressions', aggfunc='sum').fillna(0)
        df_pivot_ctr = df_historical.pivot_table(index='page', columns='month', values='ctr', aggfunc='mean').fillna(0)
        df_pivot_position = df_historical.pivot_table(index='page', columns='month', values='position', aggfunc='mean').fillna(0)

        # Sort columns by month
        df_pivot_clicks = df_pivot_clicks.reindex(sorted(df_pivot_clicks.columns), axis=1) # Sort ascending for correct date range
        df_pivot_impressions = df_pivot_impressions.reindex(sorted(df_pivot_impressions.columns), axis=1)
        df_pivot_ctr = df_pivot_ctr.reindex(sorted(df_pivot_ctr.columns), axis=1)
        df_pivot_position = df_pivot_position.reindex(sorted(df_pivot_position.columns), axis=1)
        
        # Combine into a single dataframe for export and caching
        df_combined = pd.concat([df_pivot_clicks, df_pivot_impressions, df_pivot_ctr, df_pivot_position], keys=['clicks', 'impressions', 'ctr', 'position'], axis=1)
        
        # Determine the overall date range for the report from the fetched data
        if not df_pivot_clicks.empty:
            sorted_months = sorted(df_pivot_clicks.columns)
            overall_start_date = datetime.strptime(sorted_months[0], '%Y-%m').strftime('%Y-%m-%d')
            last_month_dt = datetime.strptime(sorted_months[-1], '%Y-%m')
            overall_end_date = (last_month_dt + relativedelta(months=1) - timedelta(days=1)).strftime('%Y-%m-%d')
        else:
            overall_start_date = "N/A"
            overall_end_date = "N/A"
            
        # Save the combined dataframe to cache
        try:
            df_combined.to_csv(csv_cache_path) # Save with multi-index header
            print(f"Successfully cached data to {csv_cache_path}")
            print(f"Hint: To recreate this report from the saved data, use the --use-cache flag.")
        except PermissionError:
            print(f"\nError: Permission denied when writing to the cache file.")
            
    if df_combined is None:
        print("No data available to generate report (either no data fetched or cache empty).")
        return

    # 5. Save the data to CSV (original output path, not the cache path)
    csv_output_path = os.path.join(output_dir, f"{cache_file_prefix}-{overall_start_date}-to-{overall_end_date}.csv")
    html_output_path = os.path.join(output_dir, f"{cache_file_prefix}-{overall_start_date}-to-{overall_end_date}.html")

    # Ensure the combined dataframe is used for both CSV and HTML generation
    df_combined.to_csv(csv_output_path, index=True)
    print(f"Successfully created CSV report at {csv_output_path}")

    html_output = create_html_report(
        page_url=page_url,
        site_url=site_url,
        start_date=overall_start_date,
        end_date=overall_end_date,
        df_combined=df_combined
    )
    with open(html_output_path, 'w', encoding='utf-8') as f:
        f.write(html_output)
    print(f"Successfully created HTML report at {html_output_path}")

if __name__ == '__main__':
    main()