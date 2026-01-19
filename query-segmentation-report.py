"""
Generates a report that segments top queries by their ranking position buckets.

This script fetches query performance data for a specified date range, categorizes
each query into a position bucket (1-3, 4-10, 11-20, 21+), and then exports a
report showing the top 50 queries for each segment, complemented by summary charts.

Usage:
    python query-segmentation-report.py <site_url> [date_range_flag]

Example:
    python query-segmentation-report.py https://www.example.com --last-28-days
"""

import os
import pandas as pd
import json
import numpy as np
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

def get_gsc_data(service, site_url, start_date, end_date, dimensions, search_type='web'):
    """Fetches performance data from GSC for a given date range and dimensions."""
    all_data = []
    start_row = 0
    row_limit = 25000 
    
    print(f"Fetching {search_type} data for dimensions: {', '.join(dimensions)}...")

    while True:
        try:
            request = {
                'startDate': start_date,
                'endDate': end_date,
                'dimensions': dimensions,
                'searchType': search_type,
                'rowLimit': row_limit,
                'startRow': start_row
            }
            response = service.searchanalytics().query(siteUrl=site_url, body=request).execute()

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
    df[dimensions] = pd.DataFrame(df['keys'].tolist(), index=df.index)
    df = df.drop(columns=['keys'])
    
    for col in ['clicks', 'impressions', 'ctr', 'position']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        
    return df

def prepare_chart_data(df_all_queries, segments_config):
    """Aggregates data for generating charts."""
    chart_data = {
        'segment_names': list(segments_config.keys()),
        'clicks': [],
        'impressions': [],
        'avg_ctr': [],
        'query_count': []
    }
    
    for name, condition in segments_config.items():
        segment_df = df_all_queries[condition]
        
        total_clicks = int(segment_df['clicks'].sum())
        total_impressions = int(segment_df['impressions'].sum())
        
        # Calculate weighted average CTR
        if total_impressions > 0:
            avg_ctr = (segment_df['clicks'].sum() / segment_df['impressions'].sum()) * 100
        else:
            avg_ctr = 0
            
        num_queries = int(len(segment_df))
        
        chart_data['clicks'].append(total_clicks)
        chart_data['impressions'].append(total_impressions)
        chart_data['avg_ctr'].append(avg_ctr)
        chart_data['query_count'].append(num_queries)
        
    return chart_data

def create_html_report(segments, report_title, period_str, chart_data_json):
    """Generates an HTML report with charts from the segmented DataFrames."""
    
    report_body = ""
    for segment_name, df_segment in segments.items():
        report_body += f"<h2 class='mt-5'>{segment_name}</h2>"
        if df_segment.empty:
            report_body += "<p>No queries found in this segment.</p>"
            continue

        df_html = df_segment.copy()
        df_html = df_html.reset_index(drop=True)
        df_html.insert(0, 'Row #', df_html.index + 1)
        
        cols = ['Row #', 'query', 'clicks', 'impressions', 'ctr', 'position']
        df_html = df_html[cols]

        df_html['clicks'] = df_html['clicks'].apply(lambda x: f"{int(x):,}")
        df_html['impressions'] = df_html['impressions'].apply(lambda x: f"{int(x):,}")
        df_html['ctr'] = df_html['ctr'].apply(lambda x: f"{x:.2%}")
        df_html['position'] = df_html['position'].apply(lambda x: f"{x:.2f}")
        
        report_body += df_html.to_html(classes="table table-striped table-hover", index=False, border=0)

    return f"""
<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{report_title}</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<style>
body{{padding:2rem;}}
h1,h2{{border-bottom:2px solid #dee2e6;padding-bottom:.5rem;margin-top:2rem;}}
.table thead th {{background-color: #434343;color: #ffffff;text-align: left;}}
footer{{margin-top:3rem;text-align:center;color:#6c757d;}}
.card{{margin-bottom: 1.5rem;}}
</style>
</head>
<body><div class="container-fluid">
<h1>{report_title}</h1><p class="text-muted">Analysis for the period: {period_str}</p>

<div class="row">
    <div class="col-lg-4"><div class="card"><div class="card-header"><h3>Clicks by Segment</h3></div><div class="card-body"><canvas id="clicksPieChart"></canvas></div></div></div>
    <div class="col-lg-4"><div class="card"><div class="card-header"><h3>Impressions by Segment</h3></div><div class="card-body"><canvas id="impressionsPieChart"></canvas></div></div></div>
    <div class="col-lg-4"><div class="card"><div class="card-header"><h3>Query Count by Segment</h3></div><div class="card-body"><canvas id="queryCountChart"></canvas></div></div></div>
</div>
<div class="row">
    <div class="col-lg-12"><div class="card"><div class="card-header"><h3>Average CTR by Segment</h3></div><div class="card-body"><canvas id="ctrBarChart"></canvas></div></div></div>
</div>

<div class="table-responsive">{report_body}</div>
</div>
<footer><p><a href="https://github.com/liamdelahunty/gsc-exporter" target="_blank">gsc-exporter</a></p></footer>
<script>
    const chartData = {chart_data_json};
    const labels = chartData.segment_names;
    const colors = ['rgba(75, 192, 192, 0.7)', 'rgba(54, 162, 235, 0.7)', 'rgba(255, 206, 86, 0.7)', 'rgba(255, 99, 132, 0.7)'];
    const borderColors = ['rgba(75, 192, 192, 1)', 'rgba(54, 162, 235, 1)', 'rgba(255, 206, 86, 1)', 'rgba(255, 99, 132, 1)'];

    // Clicks Pie Chart
    new Chart(document.getElementById('clicksPieChart'), {{
        type: 'pie',
        data: {{
            labels: labels,
            datasets: [{{
                label: 'Total Clicks',
                data: chartData.clicks,
                backgroundColor: colors,
                borderColor: borderColors,
                borderWidth: 1
            }}]
        }},
        options: {{ responsive: true, maintainAspectRatio: false }}
    }});

    // Impressions Pie Chart
    new Chart(document.getElementById('impressionsPieChart'), {{
        type: 'pie',
        data: {{
            labels: labels,
            datasets: [{{
                label: 'Total Impressions',
                data: chartData.impressions,
                backgroundColor: colors,
                borderColor: borderColors,
                borderWidth: 1
            }}]
        }},
        options: {{ responsive: true, maintainAspectRatio: false }}
    }});

    // Query Count Bar Chart
    new Chart(document.getElementById('queryCountChart'), {{
        type: 'bar',
        data: {{
            labels: labels,
            datasets: [{{
                label: 'Number of Unique Queries',
                data: chartData.query_count,
                backgroundColor: colors,
                borderColor: borderColors,
                borderWidth: 1
            }}]
        }},
        options: {{
            responsive: true,
            maintainAspectRatio: false,
            scales: {{ y: {{ beginAtZero: true }} }},
            plugins: {{ legend: {{ display: false }} }}
        }}
    }});

    // CTR Bar Chart
    new Chart(document.getElementById('ctrBarChart'), {{
        type: 'bar',
        data: {{
            labels: labels,
            datasets: [{{
                label: 'Average CTR (%)',
                data: chartData.avg_ctr,
                backgroundColor: colors,
                borderColor: borderColors,
                borderWidth: 1
            }}]
        }},
        options: {{
            responsive: true,
            maintainAspectRatio: false,
            scales: {{ y: {{ beginAtZero: true, ticks: {{ callback: value => value + '%' }} }} }},
            plugins: {{ legend: {{ display: false }} }}
        }}
    }});
</script>
</body></html>"""


def main():
    """Main function to run the query segmentation report."""
    parser = argparse.ArgumentParser(description='Generate a report of top queries segmented by position.')
    parser.add_argument('site_url', help='The URL of the site to analyse. Use sc-domain: for a domain property.')
    parser.add_argument('--search-type', default='web', choices=['web', 'image', 'video', 'news', 'discover', 'googleNews'], help='The search type to query. Defaults to "web".')
    parser.add_argument('--use-cache', action='store_true', help='Use a cached CSV file from a previous run if it exists.')

    date_group = parser.add_mutually_exclusive_group()
    date_group.add_argument('--start-date', help='Start date in YYYY-MM-DD format.')
    date_group.add_argument('--end-date', help='End date in YYYY-MM-DD format. Used only with --start-date.')
    date_group.add_argument('--last-month', action='store_true', help='Use the last calendar month for the report. (Default)')
    
    args = parser.parse_args()
    site_url = args.site_url

    if not args.start_date:
        args.last_month = True

    today = date.today()
    
    if args.start_date and args.end_date:
        start_date = args.start_date
        end_date = args.end_date
        period_label = "custom-period"
    elif args.last_month:
        first_day_of_current_month = today.replace(day=1)
        last_day_of_previous_month = first_day_of_current_month - timedelta(days=1)
        start_date = last_day_of_previous_month.replace(day=1).strftime('%Y-%m-%d')
        end_date = last_day_of_previous_month.strftime('%Y-%m-%d')
        period_label = "last-month"
    
    # --- Output Generation ---
    if site_url.startswith('sc-domain:'):
        host_plain = site_url.replace('sc-domain:', '')
    else:
        host_plain = urlparse(site_url).netloc
    
    host_dir = host_plain.replace('www.', '')
    output_dir = os.path.join('output', host_dir)
    os.makedirs(output_dir, exist_ok=True)
    host_for_filename = host_dir.replace('.', '-')

    file_prefix = f"query-segmentation-report-{host_for_filename}-{period_label}-{start_date}-to-{end_date}"
    csv_output_path = os.path.join(output_dir, f"{file_prefix}.csv")
    html_output_path = os.path.join(output_dir, f"{file_prefix}.html")

    df_queries = None

    # Define position segments config first
    segments_config = {
        "Positions 1-3": (1, 3),
        "Positions 4-10": (4, 10),
        "Positions 11-20": (11, 20),
        "Positions 21+": (21, float('inf'))
    }

    if args.use_cache and os.path.exists(csv_output_path):
        print(f"Found cached data at {csv_output_path}. Using it to generate report.")
        df_queries = pd.read_csv(csv_output_path, keep_default_na=False, na_values=[''])
    else:
        print(f"Using date range: {start_date} to {end_date}")

        service = get_gsc_service()
        if not service:
            return

        df_queries = get_gsc_data(service, site_url, start_date, end_date, ['query'], args.search_type)

        if df_queries is None or df_queries.empty:
            print("No query data found for the specified period. Exiting.")
            return

        # Add position_segment column to the entire DataFrame
        conditions = [
            (df_queries['position'] >= lower) & (df_queries['position'] <= upper)
            for name, (lower, upper) in segments_config.items()
        ]
        choices = list(segments_config.keys())
        df_queries['position_segment'] = pd.Series(np.select(conditions, choices, default='Uncategorized'), dtype="category")
        
        # Save the full, segmented data for caching
        df_queries.to_csv(csv_output_path, index=False, encoding='utf-8')
        print(f"\nSuccessfully exported full query data to {csv_output_path}")
        print(f"Hint: To recreate this report from the saved data, use the --use-cache flag.")

    # --- Chart and Table Generation (using the full df_queries) ---

    # Create segment conditions from the loaded DataFrame for consistency
    segment_conditions_for_charts = {
        name: (df_queries['position_segment'] == name)
        for name in segments_config.keys()
    }
    
    # Prepare data for charts using the full dataset
    chart_data = prepare_chart_data(df_queries, segment_conditions_for_charts)
    chart_data_json = json.dumps(chart_data)

    # Prepare data for top-N tables
    segmented_dfs = {}
    for name in segments_config.keys():
        # Filter by segment, then sort and get top 50 for the tables
        segment_df = df_queries[df_queries['position_segment'] == name]
        segmented_dfs[name] = segment_df.sort_values(by='clicks', ascending=False).head(50)

    try:
        # Generate and save HTML report
        html_output = create_html_report(
            segments=segmented_dfs,
            report_title=f"Query Segmentation Report for {host_dir}",
            period_str=f"{start_date} to {end_date}",
            chart_data_json=chart_data_json
        )
        with open(html_output_path, 'w', encoding='utf-8') as f:
            f.write(html_output)
        print(f"Successfully created HTML report at {html_output_path}")

    except Exception as e:
        print(f"An error occurred during file generation: {e}")

if __name__ == '__main__':
    main()