"""
Generates a consolidated Google Search Console performance report.

This script fetches performance data (clicks, impressions, CTR) for web, discover,
and Google News search types for a given site over a specified number of months.
It then generates a CSV file and a comprehensive HTML report with charts and
summary tables.

Usage:
    python consolidated-traffic-report.py <site_url> [--months <num_months>]

Example:
    python consolidated-traffic-report.py sc-domain:example.com
    python consolidated-traffic-report.py sc-domain:example.com --months 12
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

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Google Search Performance Report (Web, Discover & News) for {{ site_url }}</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body { padding-top: 56px; } /* Offset for fixed header */
        h1 { padding-bottom: .5rem; }
        h2 { border-bottom: 2px solid #dee2e6; padding-bottom: .5rem; margin-top: 2rem; }
        .table thead th { background-color: #434343; color: #ffffff; text-align: left; }
        footer { margin-top: 3rem; text-align: center; color: #6c757d; }
    </style>
</head>
<body>
    <header class="navbar navbar-expand-lg navbar-light bg-light border-bottom mb-4 fixed-top">
        <div class="container-fluid">
            <h1 class="h3 mb-0">Google Search Performance Report (Web, Discover & News) for {{ site_url }}</h1>
        </div>
    </header>
    <main class="container-fluid py-4 flex-grow-1">
        <p class="text-muted">Analysis for the period: Monthly breakdown from {{ start_month }} to {{ end_month }}</p>
        <div class="card my-4">
            <div class="card-header"><h3>Total Clicks vs. Total Impressions</h3></div>
            <div class="card-body"><canvas id="performanceChart"></canvas></div>
        </div>
        <div class="card my-4">
            <div class="card-header"><h3>Clicks</h3></div>
            <div class="card-body"><canvas id="clicksChart"></canvas></div>
        </div>
        <div class="card my-4">
            <div class="card-header"><h3>Impressions</h3></div>
            <div class="card-body"><canvas id="impressionsChart"></canvas></div>
        </div>
        
        <h2 class="mt-5">Overall Summary Tables</h2>
        <div class="row">
            <div class="col-xl-6">
                <div class="card mb-4">
                    <div class="card-header"><h3>Clicks</h3></div>
                    <div class="card-body">
                        {{ clicks_summary_table|safe }}
                    </div>
                </div>
            </div>
            <div class="col-xl-6">
                <div class="card mb-4">
                    <div class="card-header"><h3>Impressions</h3></div>
                    <div class="card-body">
                        {{ impressions_summary_table|safe }}
                    </div>
                </div>
            </div>
        </div>

        <h2 class="mt-5">Monthly Breakdown Tables</h2>
        <div class="row">
            <div class="col-xl-6">
                <div class="card mb-4">
                    <div class="card-header"><h3>Monthly Clicks Breakdown</h3></div>
                    <div class="card-body">
                        {{ monthly_clicks_table|safe }}
                    </div>
                </div>
            </div>
            <div class="col-xl-6">
                <div class="card mb-4">
                    <div class="card-header"><h3>Monthly Impressions Breakdown</h3></div>
                    <div class="card-body">
                        {{ monthly_impressions_table|safe }}
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
        const data = {{ chart_data|safe }};
        const labels = data.map(row => row.month);

        new Chart(document.getElementById('performanceChart'), {
            type: 'line',
            data: {
                labels: labels,
                datasets: [
                    {
                        label: 'Total Clicks',
                        data: data.map(row => row.total_clicks),
                        borderColor: 'rgba(54, 162, 235, 1)',
                        backgroundColor: 'rgba(54, 162, 235, 0.2)',
                        yAxisID: 'yClicks',
                        fill: false,
                        tension: 0.1
                    },
                    {
                        label: 'Total Impressions',
                        data: data.map(row => row.total_impressions),
                        borderColor: 'rgba(255, 99, 132, 1)',
                        backgroundColor: 'rgba(255, 99, 132, 0.2)',
                        yAxisID: 'yImpressions',
                        fill: false,
                        tension: 0.1
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: {
                    mode: 'index',
                    intersect: false,
                },
                scales: {
                    yClicks: {
                        type: 'linear',
                        display: true,
                        position: 'left',
                        title: {
                            display: true,
                            text: 'Total Clicks'
                        }
                    },
                    yImpressions: {
                        type: 'linear',
                        display: true,
                        position: 'right',
                        title: {
                            display: true,
                            text: 'Total Impressions'
                        },
                        grid: {
                            drawOnChartArea: false, // only draw grid for the first Y axis
                        }
                    }
                }
            }
        });

        new Chart(document.getElementById('clicksChart'), {
            type: 'line',
            data: {
                labels: labels,
                datasets: [
                    {
                        label: 'Discover Clicks',
                        data: data.map(row => row.discover_clicks),
                        borderColor: 'rgba(75, 192, 192, 1)',
                        backgroundColor: 'rgba(75, 192, 192, 0.2)',
                        fill: false,
                        tension: 0.1
                    },
                    {
                        label: 'Web Clicks',
                        data: data.map(row => row.web_clicks),
                        borderColor: 'rgba(153, 102, 255, 1)',
                        backgroundColor: 'rgba(153, 102, 255, 0.2)',
                        fill: false,
                        tension: 0.1
                    },
                    {
                        label: 'News Clicks',
                        data: data.map(row => row.news_clicks),
                        borderColor: 'rgba(255, 159, 64, 1)',
                        backgroundColor: 'rgba(255, 159, 64, 0.2)',
                        fill: false,
                        tension: 0.1
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: {
                    mode: 'index',
                    intersect: false,
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: 'Clicks'
                        }
                    }
                }
            }
        });

        new Chart(document.getElementById('impressionsChart'), {
            type: 'line',
            data: {
                labels: labels,
                datasets: [
                    {
                        label: 'Discover Impressions',
                        data: data.map(row => row.discover_impressions),
                        borderColor: 'rgba(255, 159, 64, 1)',
                        backgroundColor: 'rgba(255, 159, 64, 0.2)',
                        fill: false,
                        tension: 0.1
                    },
                    {
                        label: 'Web Impressions',
                        data: data.map(row => row.web_impressions),
                        borderColor: 'rgba(201, 203, 207, 1)',
                        backgroundColor: 'rgba(201, 203, 207, 0.2)',
                        fill: false,
                        tension: 0.1
                    },
                    {
                        label: 'News Impressions',
                        data: data.map(row => row.news_impressions),
                        borderColor: 'rgba(75, 192, 192, 1)',
                        backgroundColor: 'rgba(75, 192, 192, 0.2)',
                        fill: false,
                        tension: 0.1
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: {
                    mode: 'index',
                    intersect: false,
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: 'Impressions'
                        }
                    }
                }
            }
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
            'aggregationType': 'byPage' # monthly data not directly supported, so we fetch daily and aggregate
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
        return pd.DataFrame()
    
    df = pd.DataFrame(rows)
    df['date'] = pd.to_datetime(df['keys'].apply(lambda x: x[0]))
    df['month'] = df['date'].dt.strftime('%Y-%m')
    
    df.rename(columns={
        'clicks': f'{search_type}_clicks',
        'impressions': f'{search_type}_impressions',
    }, inplace=True)
    
    monthly_df = df.groupby('month').agg({
        f'{search_type}_clicks': 'sum',
        f'{search_type}_impressions': 'sum'
    }).reset_index()
    
    monthly_df[f'{search_type}_ctr'] = monthly_df[f'{search_type}_clicks'] / monthly_df[f'{search_type}_impressions']
    
    return monthly_df

def generate_html_report(df, site_url, html_output_path):
    # Prepare data for the template
    start_month = df['month'].min()
    end_month = df['month'].max()

    # Right-align all data cells
    styles = [
        dict(selector="td", props=[("text-align", "right")]),
    ]

    # Overall Summary Tables
    summary_clicks_data = {
        'Web Clicks': df['web_clicks'].sum(),
        'Discover Clicks': df['discover_clicks'].sum(),
        'News Clicks': df['news_clicks'].sum(),
    }
    total_clicks = sum(summary_clicks_data.values())
    summary_clicks_data['Total Clicks'] = total_clicks

    summary_clicks_rows = [
        {'Metric': 'Total', **{k: f"{v:,.0f}" for k, v in summary_clicks_data.items()}},
        {'Metric': 'Percentage',
         'Web Clicks': f"{(summary_clicks_data['Web Clicks'] / total_clicks * 100):.2f}%" if total_clicks else '0.00%',
         'Discover Clicks': f"{(summary_clicks_data['Discover Clicks'] / total_clicks * 100):.2f}%" if total_clicks else '0.00%',
         'News Clicks': f"{(summary_clicks_data['News Clicks'] / total_clicks * 100):.2f}%" if total_clicks else '0.00%',
         'Total Clicks': '100.00%'}
    ]
    clicks_summary_df = pd.DataFrame(summary_clicks_rows)
    clicks_summary_styler = clicks_summary_df.style.set_table_attributes('class="table table-bordered table-sm"').set_table_styles(styles).hide(axis='index')
    clicks_summary_table = clicks_summary_styler.to_html()


    summary_impressions_data = {
        'Web Impressions': df['web_impressions'].sum(),
        'Discover Impressions': df['discover_impressions'].sum(),
        'News Impressions': df['news_impressions'].sum(),
    }
    total_impressions = sum(summary_impressions_data.values())
    summary_impressions_data['Total Impressions'] = total_impressions
    
    summary_impressions_rows = [
        {'Metric': 'Total', **{k: f"{v:,.0f}" for k, v in summary_impressions_data.items()}},
        {'Metric': 'Percentage',
            'Web Impressions': f"{(summary_impressions_data['Web Impressions'] / total_impressions * 100):.2f}%" if total_impressions else '0.00%',
            'Discover Impressions': f"{(summary_impressions_data['Discover Impressions'] / total_impressions * 100):.2f}%" if total_impressions else '0.00%',
            'News Impressions': f"{(summary_impressions_data['News Impressions'] / total_impressions * 100):.2f}%" if total_impressions else '0.00%',
            'Total Impressions': '100.00%'}
    ]
    impressions_summary_df = pd.DataFrame(summary_impressions_rows)
    impressions_summary_styler = impressions_summary_df.style.set_table_attributes('class="table table-bordered table-sm"').set_table_styles(styles).hide(axis='index')
    impressions_summary_table = impressions_summary_styler.to_html()

    # Monthly breakdown tables
    monthly_clicks = df[['month', 'web_clicks', 'discover_clicks', 'news_clicks', 'total_clicks']].copy()
    monthly_clicks['Web %'] = (monthly_clicks['web_clicks'] / monthly_clicks['total_clicks'] * 100).map('{:.2f}%'.format) if monthly_clicks['total_clicks'].sum() > 0 else '0.00%'
    monthly_clicks['Discover %'] = (monthly_clicks['discover_clicks'] / monthly_clicks['total_clicks'] * 100).map('{:.2f}%'.format) if monthly_clicks['total_clicks'].sum() > 0 else '0.00%'
    monthly_clicks['News %'] = (monthly_clicks['news_clicks'] / monthly_clicks['total_clicks'] * 100).map('{:.2f}%'.format) if monthly_clicks['total_clicks'].sum() > 0 else '0.00%'
    monthly_clicks.rename(columns={'month': 'Month', 'web_clicks': 'Web Clicks', 'discover_clicks': 'Discover Clicks', 'news_clicks': 'News Clicks', 'total_clicks': 'Total'}, inplace=True)
    
    monthly_impressions = df[['month', 'web_impressions', 'discover_impressions', 'news_impressions', 'total_impressions']].copy()
    monthly_impressions['Web %'] = (monthly_impressions['web_impressions'] / monthly_impressions['total_impressions'] * 100).map('{:.2f}%'.format) if monthly_impressions['total_impressions'].sum() > 0 else '0.00%'
    monthly_impressions['Discover %'] = (monthly_impressions['discover_impressions'] / monthly_impressions['total_impressions'] * 100).map('{:.2f}%'.format) if monthly_impressions['total_impressions'].sum() > 0 else '0.00%'
    monthly_impressions['News %'] = (monthly_impressions['news_impressions'] / monthly_impressions['total_impressions'] * 100).map('{:.2f}%'.format) if monthly_impressions['total_impressions'].sum() > 0 else '0.00%'
    monthly_impressions.rename(columns={'month': 'Month', 'web_impressions': 'Web Impressions', 'discover_impressions': 'Discover Impressions', 'news_impressions': 'News Impressions', 'total_impressions': 'Total'}, inplace=True)

    formatters = {col: '{:,.0f}'.format for col in monthly_clicks.columns if 'Clicks' in col or 'Total' in col}
    monthly_clicks_styler = monthly_clicks.style.set_table_attributes('class="table table-bordered table-sm"').set_table_styles(styles).format(formatters).hide(axis='index')
    monthly_clicks_table = monthly_clicks_styler.to_html()
    
    formatters = {col: '{:,.0f}'.format for col in monthly_impressions.columns if 'Impressions' in col or 'Total' in col}
    monthly_impressions_styler = monthly_impressions.style.set_table_attributes('class="table table-bordered table-sm"').set_table_styles(styles).format(formatters).hide(axis='index')
    monthly_impressions_table = monthly_impressions_styler.to_html()

    # Main data table
    data_table_df = df.drop('site_url', axis=1).copy()
    for col in data_table_df.columns:
        if '_ctr' in col:
            data_table_df[col] = (data_table_df[col] * 100).map('{:.2f}%'.format)
    formatters = {col: '{:,.0f}'.format for col in data_table_df.columns if 'clicks' in col or 'impressions' in col}
    data_table_styler = data_table_df.style.set_table_attributes('class="dataframe table table-striped table-hover"').set_table_styles(styles).format(formatters).hide(axis='index')
    data_table = data_table_styler.to_html()
    
    # Chart data
    chart_df = df.sort_values('month').copy()
    chart_df.fillna(0, inplace=True)
    chart_data = chart_df.to_json(orient='records')
    
    # Render template
    template = Environment().from_string(HTML_TEMPLATE)
    
    html_content = template.render(
        site_url=site_url,
        start_month=start_month,
        end_month=end_month,
        clicks_summary_table=clicks_summary_table,
        impressions_summary_table=impressions_summary_table,
        monthly_clicks_table=monthly_clicks_table,
        monthly_impressions_table=monthly_impressions_table,
        data_table=data_table,
        chart_data=chart_data,
        generation_date=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    )
    
    with open(html_output_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    print(f"Successfully created HTML report at {html_output_path}")

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
            # GSC returns 400 if date range is too recent (no data yet)
            if e.resp.status == 400:
                print(f"No data for {check_date_str}, checking previous day (HTTP 400).")
            else:
                print(f"An HTTP error occurred while checking date {check_date_str}: {e}")
                print("Continuing to check previous days.")
        except Exception as e:
            print(f"An unexpected error occurred while checking date {check_date_str}: {e}")
            print("Continuing to check previous days.")
            
    print(f"Could not determine latest available GSC date within {max_retries} days. Using today's date as a fallback.")
    return current_date # Fallback to today if no data found after retries

def create_daily_df(rows):
    if not rows:
        return pd.DataFrame(columns=['date', 'clicks', 'impressions'])
    df = pd.DataFrame(rows)
    df['date'] = pd.to_datetime(df['keys'].apply(lambda x: x[0]))
    return df[['date', 'clicks', 'impressions']]

def main():
    parser = argparse.ArgumentParser(description='Generate a consolidated performance report from Google Search Console.')
    parser.add_argument('site_url', help='The URL of the site to process (e.g., sc-domain:example.com).')
    parser.add_argument('--months', type=int, default=16, help='Number of past months to include in the report.')
    
    args = parser.parse_args()
    site_url = args.site_url
    num_months = args.months

    service = get_gsc_service()
    if not service:
        print("Failed to get GSC service.")
        return

    latest_available_date = get_latest_available_gsc_date(service, site_url)
    
    # Calculate end date: end of the last complete month
    end_date = latest_available_date.replace(day=1) - timedelta(days=1)
    
    # Calculate start date: beginning of the month `num_months` ago
    start_date = (end_date.replace(day=1) - relativedelta(months=num_months))
    
    end_date_str = end_date.strftime('%Y-%m-%d')
    start_date_str = start_date.strftime('%Y-%m-%d')

    # Fetch data for all search types
    web_data = fetch_gsc_data(service, site_url, start_date_str, end_date_str, 'web')
    discover_data = fetch_gsc_data(service, site_url, start_date_str, end_date_str, 'discover')
    news_data = fetch_gsc_data(service, site_url, start_date_str, end_date_str, 'googleNews')
    
    # Check for incomplete starting month
    web_daily_df = create_daily_df(web_data)
    discover_daily_df = create_daily_df(discover_data)
    news_daily_df = create_daily_df(news_data)
    
    all_daily_data = pd.concat([web_daily_df, discover_daily_df, news_daily_df])
    
    month_to_exclude = None
    if not all_daily_data.empty:
        earliest_date = all_daily_data['date'].min()
        if earliest_date.day != 1:
            month_to_exclude = earliest_date.strftime('%Y-%m')
            print(f"Excluding incomplete starting month: {month_to_exclude}")

    # Process data
    web_df = process_data(web_data, 'web')
    discover_df = process_data(discover_data, 'discover')
    news_df = process_data(news_data, 'news')

    # Merge dataframes
    merged_df = pd.DataFrame(columns=['month'])
    if not web_df.empty:
        merged_df = pd.merge(merged_df, web_df, on='month', how='outer')
    if not discover_df.empty:
        merged_df = pd.merge(merged_df, discover_df, on='month', how='outer')
    if not news_df.empty:
        merged_df = pd.merge(merged_df, news_df, on='month', how='outer')

    merged_df.fillna(0, inplace=True)

    if month_to_exclude:
        merged_df = merged_df[merged_df['month'] != month_to_exclude]

    if merged_df.empty:
        print("No complete months of data to report. Exiting.")
        return
        
    # Calculate totals
    for col_type in ['clicks', 'impressions']:
        cols_to_sum = [f'{st}_{col_type}' for st in ['web', 'discover', 'news'] if f'{st}_{col_type}' in merged_df.columns]
        merged_df[f'total_{col_type}'] = merged_df[cols_to_sum].sum(axis=1)

    merged_df['total_ctr'] = merged_df['total_clicks'] / merged_df['total_impressions']
    
    # Add site_url column
    merged_df.insert(0, 'site_url', site_url)
    
    # Sort by month
    merged_df = merged_df.sort_values('month', ascending=False)
    
    # Define output paths
    if site_url.startswith('sc-domain:'):
        host_plain = site_url.replace('sc-domain:', '')
    else:
        host_plain = urlparse(site_url).netloc
    
    host_dir = host_plain.replace('www.', '')
    output_dir = os.path.join('output', host_dir)
    os.makedirs(output_dir, exist_ok=True)
    host_for_filename = host_dir.replace('.', '-')
    
    run_date_str = end_date.strftime('%Y-%m')
    csv_file_name = f"consolidated-performance-{host_for_filename}-{run_date_str}.csv"
    csv_output_path = os.path.join(output_dir, csv_file_name)
    
    html_file_name = f"consolidated-performance-{host_for_filename}-{run_date_str}.html"
    html_output_path = os.path.join(output_dir, html_file_name)

    # Save CSV
    merged_df.to_csv(csv_output_path, index=False)
    print(f"Successfully exported CSV to {csv_output_path}")

    # Generate HTML report
    if not merged_df.empty:
        generate_html_report(merged_df, site_url, html_output_path)



if __name__ == '__main__':
    main()
