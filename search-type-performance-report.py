"""
Generates a Google Search Console performance report by search type.

This script fetches performance data (clicks, impressions, CTR) for all available
search types (web, discover, Google News, image, video, news) for a given site over a
specified period. It defaults to the last complete month but supports other date ranges.
It then generates a comprehensive HTML report with charts and summary tables.

Usage:
    python search-type-performance-report.py <site_url> [--start-date <start_date>] [--end-date <end_date>]

Example:
    python search-type-performance-report.py sc-domain:example.com
    python search-type-performance-report.py sc-domain:example.com --last-3-months
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
import json
from jinja2 import Environment

# --- Configuration ---
SCOPES = ['https://www.googleapis.com/auth/webmasters.readonly']
CLIENT_SECRET_FILE = 'client_secret.json'
TOKEN_FILE = 'token.json'
SEARCH_TYPES = ['web', 'image', 'video', 'news', 'discover', 'googleNews']

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Search Type Performance Report for {{ site_url }}</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body { padding-top: 56px; }
        h1, h2, h3 { padding-bottom: .5rem; }
        h2 { border-bottom: 2px solid #dee2e6; padding-bottom: .5rem; margin-top: 2rem; }
        .table thead th { background-color: #434343; color: #ffffff; text-align: left; }
        footer { margin-top: 3rem; text-align: center; color: #6c757d; }
    </style>
</head>
<body>
    <header class="navbar navbar-expand-lg navbar-light bg-light border-bottom mb-4 fixed-top">
        <div class="container-fluid">
            <h1 class="h3 mb-0">Search Type Performance Report for {{ site_url }}</h1>
        </div>
    </header>
    <main class="container-fluid py-4 flex-grow-1">
        <p class="text-muted">Analysis for the period: {{ start_date }} to {{ end_date }}</p>

        <div class="row">
            <div class="col-xl-6">
                <div class="card my-4">
                    <div class="card-header"><h3>Total Clicks by Search Type</h3></div>
                    <div class="card-body"><canvas id="clicksBarChart"></canvas></div>
                </div>
            </div>
            <div class="col-xl-6">
                <div class="card my-4">
                    <div class="card-header"><h3>Total Impressions by Search Type</h3></div>
                    <div class="card-body"><canvas id="impressionsBarChart"></canvas></div>
                </div>
            </div>
        </div>

        <div class="card my-4">
            <div class="card-header"><h3>Total Clicks Over Time (Stacked)</h3></div>
            <div class="card-body"><canvas id="clicksStackedChart"></canvas></div>
        </div>
        <div class="card my-4">
            <div class="card-header"><h3>Total Impressions Over Time (Stacked)</h3></div>
            <div class="card-body"><canvas id="impressionsStackedChart"></canvas></div>
        </div>
        <div class="card my-4">
            <div class="card-header"><h3>Clicks by Search Type Over Time</h3></div>
            <div class="card-body"><canvas id="clicksLineChart"></canvas></div>
        </div>
        <div class="card my-4">
            <div class="card-header"><h3>Impressions by Search Type Over Time</h3></div>
            <div class="card-body"><canvas id="impressionsLineChart"></canvas></div>
        </div>
        
        <h2 class="mt-5">Overall Summary Tables</h2>
        <div class="row">
            <div class="col-xl-12">
                <div class="card mb-4 mx-auto col-lg-6">
                    <div class="card-header"><h3>Performance Overview</h3></div>
                    <div class="card-body">
                        {{ ctr_summary_table|safe }}
                    </div>
                </div>
            </div>
            <div class="col-xl-6">
                <div class="card mb-4">
                    <div class="card-header"><h3>Clicks Breakdown</h3></div>
                    <div class="card-body">
                        {{ clicks_summary_table|safe }}
                    </div>
                </div>
            </div>
            <div class="col-xl-6">
                <div class="card mb-4">
                    <div class="card-header"><h3>Impressions Breakdown</h3></div>
                    <div class="card-body">
                        {{ impressions_summary_table|safe }}
                    </div>
                </div>
            </div>
        </div>

        <h2>Data Table</h2>
        <div class="table-responsive">{{ data_table|safe }}</div>
    </main>
    <footer class="footer mt-auto py-3 bg-light">
        <div class="container text-center">
            <span class="text-muted">Report generated on {{ generation_date }}. <a href="https://github.com/liamdelahunty/gsc-exporter" target="_blank">gsc-exporter</a></span>
        </div>
    </footer>
    <script>
        const chartData = {{ chart_data|safe }};
        const summaryData = {{ summary_data|safe }};
        const labels = chartData.map(row => row.date);
        const searchTypes = {{ search_types|safe }};
        const colors = [
            'rgba(54, 162, 235, 1)', 'rgba(255, 99, 132, 1)', 'rgba(75, 192, 192, 1)',
            'rgba(153, 102, 255, 1)', 'rgba(255, 159, 64, 1)', 'rgba(255, 205, 86, 1)'
        ];

        // Bar charts for totals
        new Chart(document.getElementById('clicksBarChart'), {
            type: 'bar',
            data: {
                labels: searchTypes,
                datasets: [{
                    label: 'Total Clicks',
                    data: searchTypes.map(st => summaryData[st + '_clicks']),
                    backgroundColor: colors,
                }]
            },
            options: { responsive: true, maintainAspectRatio: false }
        });

        new Chart(document.getElementById('impressionsBarChart'), {
            type: 'bar',
            data: {
                labels: searchTypes,
                datasets: [{
                    label: 'Total Impressions',
                    data: searchTypes.map(st => summaryData[st + '_impressions']),
                    backgroundColor: colors,
                }]
            },
            options: { responsive: true, maintainAspectRatio: false }
        });

        // Stacked area charts for time series
        const stackedClicksDatasets = searchTypes.map((st, index) => ({
            label: st + ' Clicks',
            data: chartData.map(row => row[st + '_clicks'] || 0),
            borderColor: colors[index % colors.length],
            backgroundColor: colors[index % colors.length],
            fill: true,
            tension: 0.1
        }));

        new Chart(document.getElementById('clicksStackedChart'), {
            type: 'line',
            data: { labels: labels, datasets: stackedClicksDatasets },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: { mode: 'index', intersect: false },
                scales: {
                    y: {
                        stacked: true,
                        beginAtZero: true
                    }
                }
            }
        });

        const stackedImpressionsDatasets = searchTypes.map((st, index) => ({
            label: st + ' Impressions',
            data: chartData.map(row => row[st + '_impressions'] || 0),
            borderColor: colors[index % colors.length],
            backgroundColor: colors[index % colors.length],
            fill: true,
            tension: 0.1
        }));

        new Chart(document.getElementById('impressionsStackedChart'), {
            type: 'line',
            data: { labels: labels, datasets: stackedImpressionsDatasets },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: { mode: 'index', intersect: false },
                scales: {
                    y: {
                        stacked: true,
                        beginAtZero: true
                    }
                }
            }
        });

        // Non-stacked line charts for time series
        const lineClicksDatasets = searchTypes.map((st, index) => ({
            label: st + ' Clicks',
            data: chartData.map(row => row[st + '_clicks'] || 0),
            borderColor: colors[index % colors.length],
            fill: false,
            tension: 0.1
        }));

        new Chart(document.getElementById('clicksLineChart'), {
            type: 'line',
            data: { labels: labels, datasets: lineClicksDatasets },
            options: { responsive: true, maintainAspectRatio: false, interaction: { mode: 'index', intersect: false } }
        });

        const lineImpressionsDatasets = searchTypes.map((st, index) => ({
            label: st + ' Impressions',
            data: chartData.map(row => row[st + '_impressions'] || 0),
            borderColor: colors[index % colors.length],
            fill: false,
            tension: 0.1
        }));

        new Chart(document.getElementById('impressionsLineChart'), {
            type: 'line',
            data: { labels: labels, datasets: lineImpressionsDatasets },
            options: { responsive: true, maintainAspectRatio: false, interaction: { mode: 'index', intersect: false } }
        });
    </script>
</body>
</html>
"""

def get_gsc_service():
    """Authenticates and returns a Google Search Console service object."""
    creds = None
    if os.path.exists(TOKEN_FILE):
        try:
            creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
        except Exception as e:
            print(f"Could not load credentials from {TOKEN_FILE}. Error: {e}")
            creds = None

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except exceptions.RefreshError as e:
                print(f"Error refreshing token: {e}")
                if os.path.exists(TOKEN_FILE):
                    os.remove(TOKEN_FILE)
                creds = None
        
        if not creds:
            if not os.path.exists(CLIENT_SECRET_FILE):
                print(f"Error: {CLIENT_SECRET_FILE} not found.")
                return None
            
            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        
        with open(TOKEN_FILE, 'w') as token:
            token.write(creds.to_json())

    return build('webmasters', 'v3', credentials=creds)

def fetch_gsc_data(service, site_url, start_date, end_date, search_type):
    """Fetches GSC data for a given search type and date range."""
    print(f"Fetching {search_type} data for {site_url} from {start_date} to {end_date}...")
    try:
        request = {
            'startDate': start_date,
            'endDate': end_date,
            'dimensions': ['date'],
            'searchType': search_type,
            'rowLimit': 25000
        }
        response = service.searchanalytics().query(siteUrl=site_url, body=request).execute()
        return response.get('rows', [])
    except HttpError as e:
        print(f"An HTTP error occurred for {search_type} data: {e}")
        return []
    except Exception as e:
        print(f"An unexpected error occurred for {search_type} data: {e}")
        return []

def process_data(rows, search_type):
    """Processes the raw API data into a pandas DataFrame."""
    if not rows:
        # Return an empty df with just a date column for merging
        return pd.DataFrame({'date': pd.Series(dtype='datetime64[ns]')})

    df = pd.DataFrame(rows)
    df['date'] = pd.to_datetime(df['keys'].apply(lambda x: x[0]))
    
    rename_dict = {}
    cols_to_keep = ['date']

    if 'clicks' in df.columns:
        cols_to_keep.append('clicks')
        rename_dict['clicks'] = f'{search_type}_clicks'
    
    if 'impressions' in df.columns:
        cols_to_keep.append('impressions')
        rename_dict['impressions'] = f'{search_type}_impressions'

    if 'ctr' in df.columns:
        cols_to_keep.append('ctr')
        rename_dict['ctr'] = f'{search_type}_ctr'

    if 'position' in df.columns:
        cols_to_keep.append('position')
        rename_dict['position'] = f'{search_type}_position'
        
    df = df[cols_to_keep]
    df.rename(columns=rename_dict, inplace=True)
    
    return df

def generate_html_report(df, site_url, start_date, end_date, html_output_path):
    """Generates the HTML report."""
    df.fillna(0, inplace=True)
    
    # Prepare data for the template
    styles = [dict(selector="td", props=[("text-align", "right")])]

    # Overall Summary Tables
    summary_data = {}
    for st in SEARCH_TYPES:
        clicks_col = f'{st}_clicks'
        impressions_col = f'{st}_impressions'
        summary_data[clicks_col] = df[clicks_col].sum() if clicks_col in df.columns else 0
        summary_data[impressions_col] = df[impressions_col].sum() if impressions_col in df.columns else 0

    # Clicks Summary Table
    total_clicks_by_type = {st: summary_data.get(f'{st}_clicks', 0) for st in SEARCH_TYPES}
    grand_total_clicks = sum(total_clicks_by_type.values())
    
    clicks_total_row_data = {st: f"{total:,.0f}" for st, total in total_clicks_by_type.items()}
    clicks_total_row_data['Total'] = f"{grand_total_clicks:,.0f}"
    clicks_total_row_data['Metric'] = 'Total'

    clicks_percentage_row_data = {st: f"{(total / grand_total_clicks * 100):.2f}%" if grand_total_clicks else '0.00%' for st, total in total_clicks_by_type.items()}
    clicks_percentage_row_data['Total'] = '100.00%'
    clicks_percentage_row_data['Metric'] = 'Percentage'

    clicks_summary_df = pd.DataFrame([clicks_total_row_data, clicks_percentage_row_data])
    clicks_summary_df = clicks_summary_df[['Metric'] + SEARCH_TYPES + ['Total']] # Enforce column order
    clicks_summary_table = clicks_summary_df.style.set_table_attributes('class="table table-bordered table-sm"').set_table_styles(styles).hide(axis='index').to_html()

    # Impressions Summary Table
    total_impressions_by_type = {st: summary_data.get(f'{st}_impressions', 0) for st in SEARCH_TYPES}
    grand_total_impressions = sum(total_impressions_by_type.values())
    
    impressions_total_row_data = {st: f"{total:,.0f}" for st, total in total_impressions_by_type.items()}
    impressions_total_row_data['Total'] = f"{grand_total_impressions:,.0f}"
    impressions_total_row_data['Metric'] = 'Total'

    impressions_percentage_row_data = {st: f"{(total / grand_total_impressions * 100):.2f}%" if grand_total_impressions else '0.00%' for st, total in total_impressions_by_type.items()}
    impressions_percentage_row_data['Total'] = '100.00%'
    impressions_percentage_row_data['Metric'] = 'Percentage'

    impressions_summary_df = pd.DataFrame([impressions_total_row_data, impressions_percentage_row_data])
    impressions_summary_df = impressions_summary_df[['Metric'] + SEARCH_TYPES + ['Total']] # Enforce column order
    impressions_summary_table = impressions_summary_df.style.set_table_attributes('class="table table-bordered table-sm"').set_table_styles(styles).hide(axis='index').to_html()

    # CTR Summary Table
    ctr_summary_data = []
    for st in SEARCH_TYPES:
        clicks = summary_data.get(f'{st}_clicks', 0)
        impressions = summary_data.get(f'{st}_impressions', 0)
        ctr = (clicks / impressions * 100) if impressions else 0
        ctr_summary_data.append({
            'Metric': st,
            'Clicks': f"{clicks:,.0f}",
            'Impressions': f"{impressions:,.0f}",
            'CTR': f"{ctr:.2f}%"
        })
    
    total_ctr = (grand_total_clicks / grand_total_impressions * 100) if grand_total_impressions else 0
    ctr_summary_data.append({
        'Metric': 'Total',
        'Clicks': f"{grand_total_clicks:,.0f}",
        'Impressions': f"{grand_total_impressions:,.0f}",
        'CTR': f"{total_ctr:.2f}%"
    })
    
    ctr_summary_df = pd.DataFrame(ctr_summary_data)
    ctr_summary_table = ctr_summary_df.style.set_table_attributes('class="table table-bordered table-sm"').set_table_styles(styles).hide(axis='index').to_html()

    # Main data table
    data_table_df = df.copy()
    for col in data_table_df.columns:
        if '_ctr' in col:
            data_table_df[col] = (data_table_df[col] * 100).map('{:.2f}%'.format)
        if '_position' in col:
            # Check if the column contains non-zero values before formatting
            if data_table_df[col].any():
                data_table_df[col] = data_table_df[col].map('{:.2f}'.format)
            else:
                data_table_df[col] = ''

    formatters = {col: '{:,.0f}'.format for col in data_table_df.columns if 'clicks' in col or 'impressions' in col}
    data_table = data_table_df.style.set_table_attributes('class="dataframe table table-striped table-hover"').format(formatters).hide(axis='index').to_html()
    
    # Chart data
    chart_df = df.sort_values('date').copy()
    chart_df['date'] = chart_df['date'].dt.strftime('%Y-%m-%d')
    chart_data = chart_df.to_json(orient='records')

    # Convert numpy types to native Python types for JSON serialization
    summary_data_for_json = {k: int(v) for k, v in summary_data.items()}
    
    # Render template
    template = Environment().from_string(HTML_TEMPLATE)
    html_content = template.render(
        site_url=site_url,
        start_date=start_date,
        end_date=end_date,
        clicks_summary_table=clicks_summary_table,
        impressions_summary_table=impressions_summary_table,
        ctr_summary_table=ctr_summary_table,
        data_table=data_table,
        chart_data=chart_data,
        summary_data=json.dumps(summary_data_for_json),
        search_types=json.dumps(SEARCH_TYPES),
        generation_date=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    )
    
    with open(html_output_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    print(f"Successfully created HTML report at {html_output_path}")

def get_latest_available_gsc_date(service, site_url, max_retries=5):
    """Determines the latest date for which GSC data is available."""
    current_date = date.today()
    for i in range(max_retries):
        check_date = current_date - timedelta(days=i + 2) # GSC data is usually delayed by 2 days
        check_date_str = check_date.strftime('%Y-%m-%d')
        print(f"Checking for GSC data availability on: {check_date_str}...")
        try:
            request = {'startDate': check_date_str, 'endDate': check_date_str, 'dimensions': ['date'], 'rowLimit': 1}
            response = service.searchanalytics().query(siteUrl=site_url, body=request).execute()
            if 'rows' in response and response['rows']:
                print(f"Latest available GSC data found for: {check_date_str}")
                return check_date
        except HttpError as e:
            if e.resp.status == 400:
                print(f"No data for {check_date_str}, checking previous day (HTTP 400).")
            else:
                print(f"An HTTP error occurred while checking date {check_date_str}: {e}")
    print(f"Could not determine latest available GSC date. Using two days ago as fallback.")
    return current_date - timedelta(days=2)

def main():
    parser = argparse.ArgumentParser(description='Generate a performance report by search type from Google Search Console.')
    parser.add_argument('site_url', help='The URL of the site to process (e.g., sc-domain:example.com).')
    
    date_group = parser.add_mutually_exclusive_group()
    date_group.add_argument('--start-date', help='Start date in YYYY-MM-DD format.')
    date_group.add_argument('--last-7-days', action='store_true', help='Set date range to the last 7 days.')
    date_group.add_argument('--last-28-days', action='store_true', help='Set date range to the last 28 days.')
    date_group.add_argument('--last-month', action='store_true', help='Set date range to the last calendar month.')
    date_group.add_argument('--last-3-months', action='store_true', help='Set date range to the last 3 months.')
    date_group.add_argument('--last-6-months', action='store_true', help='Set date range to the last 6 months.')
    date_group.add_argument('--last-12-months', action='store_true', help='Set date range to the last 12 months.')
    
    parser.add_argument('--end-date', help='End date in YYYY-MM-DD format. Used only with --start-date.')
    
    args = parser.parse_args()

    service = get_gsc_service()
    if not service:
        print("Failed to get GSC service.")
        return

    latest_available_date = get_latest_available_gsc_date(service, args.site_url)

    # Set default date range if none is chosen
    if not any([
        args.start_date, args.last_7_days, args.last_28_days,
        args.last_month, args.last_3_months, args.last_6_months, args.last_12_months
    ]):
        args.last_month = True

    if args.start_date and args.end_date:
        start_date = args.start_date
        end_date = args.end_date
    elif args.last_7_days:
        start_date = (latest_available_date - timedelta(days=6)).strftime('%Y-%m-%d')
        end_date = latest_available_date.strftime('%Y-%m-%d')
    elif args.last_28_days:
        start_date = (latest_available_date - timedelta(days=27)).strftime('%Y-%m-%d')
        end_date = latest_available_date.strftime('%Y-%m-%d')
    elif args.last_month:
        end_date_dt = latest_available_date.replace(day=1) - timedelta(days=1)
        start_date_dt = end_date_dt.replace(day=1)
        start_date = start_date_dt.strftime('%Y-%m-%d')
        end_date = end_date_dt.strftime('%Y-%m-%d')
    elif args.last_3_months:
        start_date = (latest_available_date - relativedelta(months=3) + timedelta(days=1)).strftime('%Y-%m-%d')
        end_date = latest_available_date.strftime('%Y-%m-%d')
    elif args.last_6_months:
        start_date = (latest_available_date - relativedelta(months=6) + timedelta(days=1)).strftime('%Y-%m-%d')
        end_date = latest_available_date.strftime('%Y-%m-%d')
    elif args.last_12_months:
        start_date = (latest_available_date - relativedelta(months=12) + timedelta(days=1)).strftime('%Y-%m-%d')
        end_date = latest_available_date.strftime('%Y-%m-%d')
    else: # Default to last month if no flag is set
        end_date_dt = latest_available_date.replace(day=1) - timedelta(days=1)
        start_date_dt = end_date_dt.replace(day=1)
        start_date = start_date_dt.strftime('%Y-%m-%d')
        end_date = end_date_dt.strftime('%Y-%m-%d')

    all_data_dfs = []
    for st in SEARCH_TYPES:
        data = fetch_gsc_data(service, args.site_url, start_date, end_date, st)
        df = process_data(data, st)
        if not df.empty:
            all_data_dfs.append(df)
    
    if not all_data_dfs:
        print("No data found for any search type in the given period.")
        return

    # Merge all dataframes on date
    from functools import reduce
    merged_df = reduce(lambda left, right: pd.merge(left, right, on='date', how='outer'), all_data_dfs)


    merged_df.fillna(0, inplace=True)
    merged_df = merged_df.sort_values('date', ascending=False)
    
    # Define output paths
    if args.site_url.startswith('sc-domain:'):
        host_plain = args.site_url.replace('sc-domain:', '')
    else:
        host_plain = urlparse(args.site_url).netloc
    
    host_dir = host_plain.replace('www.', '')
    output_dir = os.path.join('output', host_dir)
    os.makedirs(output_dir, exist_ok=True)
    host_for_filename = host_dir.replace('.', '-')
    
    # CSV output
    csv_file_name = f"search-type-performance-{host_for_filename}-{start_date}-to-{end_date}.csv"
    csv_output_path = os.path.join(output_dir, csv_file_name)
    merged_df.to_csv(csv_output_path, index=False)
    print(f"Successfully exported CSV to {csv_output_path}")

    # HTML output
    html_file_name = f"search-type-performance-{host_for_filename}-{start_date}-to-{end_date}.html"
    html_output_path = os.path.join(output_dir, html_file_name)

    generate_html_report(merged_df, args.site_url, start_date, end_date, html_output_path)

if __name__ == '__main__':
    main()
