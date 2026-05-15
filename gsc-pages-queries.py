"""
Exports a report of queries and their corresponding pages from a Google 
Search Console property.

This script authenticates with the GSC API, fetches performance data, and then
generates both a CSV and an interactive HTML report.

Usage:
    python gsc-pages-queries.py <site_url> [--start-date <start_date>] [--end-date <end_date>]
"""
import os
import pandas as pd
import time
import socket
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.auth import exceptions
from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta
from urllib.parse import urlparse
import sys
import html
import re
import argparse

# Set global timeout for API requests
socket.setdefaulttimeout(300)

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
            print(f"Could not load credentials: {e}")
            creds = None

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except exceptions.RefreshError:
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

def get_latest_available_gsc_date(service, site_url, max_retries=5):
    """Determines the latest available GSC date."""
    current_date = date.today()
    for i in range(max_retries):
        check_date = current_date - timedelta(days=i)
        check_date_str = check_date.strftime('%Y-%m-%d')
        try:
            request = {'startDate': check_date_str, 'endDate': check_date_str, 'dimensions': ['date'], 'rowLimit': 1}
            response = service.searchanalytics().query(siteUrl=site_url, body=request).execute()
            if 'rows' in response and response['rows']:
                return check_date
        except Exception:
            continue
    return current_date 

def get_pages_queries_data(service, site_url, start_date, end_date):
    """Fetches pages and queries data with retries."""
    all_data = []
    start_row = 0
    row_limit = 10000 
    
    while True:
        success = False
        for attempt in range(3):
            try:
                request = {
                    'startDate': start_date,
                    'endDate': end_date,
                    'dimensions': ['query', 'page'],
                    'rowLimit': row_limit,
                    'startRow': start_row
                }
                response = service.searchanalytics().query(siteUrl=site_url, body=request).execute()
                if 'rows' in response:
                    all_data.extend(response['rows'])
                    if len(response['rows']) < row_limit: break
                    start_row += row_limit
                else: break
                success = True
                break
            except (socket.timeout, TimeoutError):
                time.sleep(5 * (attempt + 1))
            except HttpError: break
        
        if not success or 'rows' not in response or len(response['rows']) < row_limit: break
    return all_data

def create_html_report(data_df, site_url, start_date, end_date, report_limit, sub_table_limit, command, brand_terms):
    """Generates the interactive HTML report with link refinements."""
    
    brand_terms_str = ", ".join(sorted(list(brand_terms))) if brand_terms else "None"
    query_count = data_df['query'].nunique()
    page_count = data_df['page'].nunique()

    html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Google Organic Pages & Queries Report: {site_url}</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"></script>
    <style>
        body {{ padding: 2rem; background-color: #f8f9fa; }}
        h1 {{ border-bottom: 2px solid #dee2e6; padding-bottom: .5rem; }}
        .table td {{ word-wrap: break-word; max-width: 500px; }}
        .text-break {{ word-break: break-all !all; }}
        .accordion-button:not(.collapsed) {{ background-color: #e7f1ff; }}
        .badge-bg-primary {{ background-color: #0076AF; }}
        .badge-bg-secondary {{ background-color: #712784; }}
    </style>
</head>
<body>
    <div class="container-fluid">
        <h1>Google Organic Pages & Queries Report</h1>
        <p class="lead">{site_url} ({start_date} to {end_date})</p>

        <ul class="nav nav-tabs" id="myTab" role="tablist">
            <li class="nav-item">
                <button class="nav-link active" id="queries-tab" data-bs-toggle="tab" data-bs-target="#queries" type="button">Queries to Pages</button>
            </li>
            <li class="nav-item">
                <button class="nav-link" id="pages-tab" data-bs-toggle="tab" data-bs-target="#pages" type="button">Pages to Queries</button>
            </li>
        </ul>

        <div class="tab-content" id="myTabContent">
            <div class="tab-pane fade show active" id="queries" role="tabpanel">
                {generate_accordion_html(data_df, 'query', 'page', report_limit, sub_table_limit)}
            </div>
            <div class="tab-pane fade" id="pages" role="tabpanel">
                {generate_accordion_html(data_df, 'page', 'query', report_limit, sub_table_limit)}
            </div>
        </div>
    </div>
</body>
</html>
    """
    return html_content

def generate_accordion_html(df, primary_dim, secondary_dim, report_limit, sub_table_limit):
    accordion_id = f"accordion-{primary_dim}"
    html = f'<div class="accordion mt-3" id="{accordion_id}">'

    primary_totals = df.groupby(primary_dim).agg(
        total_clicks=('clicks', 'sum'),
        total_impressions=('impressions', 'sum')
    ).sort_values(by='total_clicks', ascending=False).head(report_limit).reset_index()

    for i, row in primary_totals.iterrows():
        primary_val = row[primary_dim]
        display_val = primary_val
        
        # If primary is a page, make it clickable in the header
        if primary_dim == 'page':
            display_val = f'<a href="{primary_val}" target="_blank" class="text-white text-break">{primary_val}</a>'

        sub_df = df[df[primary_dim] == primary_val].head(sub_table_limit).copy()
        
        # If secondary is a page, make it clickable in the table
        if secondary_dim == 'page':
            sub_df['page'] = sub_df['page'].apply(lambda x: f'<a href="{x}" target="_blank" class="text-break">{x}</a>')

        table_html = sub_df[[secondary_dim, 'clicks', 'impressions', 'ctr', 'position']].to_html(
            classes="table table-sm table-striped", index=False, border=0, escape=False
        )

        html += f"""
        <div class="accordion-item">
            <h2 class="accordion-header">
                <button class="accordion-button collapsed" type="button" data-bs-toggle="collapse" data-bs-target="#collapse-{primary_dim}-{i}">
                    <div class="d-flex w-100 align-items-center">
                        <span class="text-truncate" style="max-width: 70%;">{primary_val}</span>
                        <div class="ms-auto">
                            <span class="badge badge-bg-primary me-2">Clicks: {row['total_clicks']:,}</span>
                            <span class="badge badge-bg-secondary">Impr: {row['total_impressions']:,}</span>
                        </div>
                    </div>
                </button>
            </h2>
            <div id="collapse-{primary_dim}-{i}" class="accordion-collapse collapse" data-bs-parent="#{accordion_id}">
                <div class="accordion-body">
                    {table_html}
                </div>
            </div>
        </div>
        """
    return html + '</div>'

def main():
    parser = argparse.ArgumentParser(description='Export GSC pages and queries.')
    parser.add_argument('site_url', help='The site URL.')
    parser.add_argument('--use-cache', action='store_true')
    parser.add_argument('--report-limit', type=int, default=250)
    parser.add_argument('--sub-table-limit', type=int, default=100)
    args = parser.parse_args()

    service = get_gsc_service()
    if not service: return
    
    latest_date = get_latest_available_gsc_date(service, args.site_url)
    end_date_dt = latest_date.replace(day=1) - timedelta(days=1)
    start_date_dt = end_date_dt.replace(day=1)
    start_str, end_str = start_date_dt.strftime('%Y-%m-%d'), end_date_dt.strftime('%Y-%m-%d')

    host_plain = args.site_url.replace('sc-domain:', '') if args.site_url.startswith('sc-domain:') else urlparse(args.site_url).netloc
    host_dir = host_plain.replace('www.', '')
    output_dir = os.path.join('output', host_dir)
    os.makedirs(output_dir, exist_ok=True)
    
    file_prefix = f"gsc-pages-queries-{host_dir.replace('.', '-')}-{start_str}-to-{end_str}"
    csv_path = os.path.join(output_dir, f"{file_prefix}.csv")
    html_path = os.path.join(output_dir, f"{file_prefix}.html")

    if args.use_cache and os.path.exists(csv_path):
        df = pd.read_csv(csv_path)
    else:
        raw_data = get_pages_queries_data(service, args.site_url, start_str, end_str)
        if not raw_data: return
        df = pd.DataFrame(raw_data)
        df[['query', 'page']] = pd.DataFrame(df['keys'].tolist(), index=df.index)
        df.to_csv(csv_path, index=False)

    html_report = create_html_report(df, args.site_url, start_str, end_str, args.report_limit, args.sub_table_limit, "", set())
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(html_report)
    print(f"Generated HTML report: {html_path}")

if __name__ == '__main__':
    main()
