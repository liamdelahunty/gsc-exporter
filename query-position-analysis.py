"""
Performs an account-wide analysis of Google Search Console data, gathering key
performance metrics for each complete calendar month for every property in the account.

This script authenticates with the Google Search Console API, fetches a list of all
sites associated with the account, and then, for each site, retrieves the clicks,
impressions, CTR, and average position for each full calendar month over the last
16 months.

The aggregated data is then compiled into a single CSV file and a single HTML report,
providing a comprehensive overview of the account's performance over time.
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

def get_monthly_query_data(service, site_url, start_date, end_date):
    """Fetches query performance data from GSC for a given date range."""
    try:
        request = {
            'startDate': start_date,
            'endDate': end_date,
            'dimensions': ['query'], # Request data by query
            'rowLimit': 25000, # Max row limit for detailed query data
            'startRow': 0
        }
        # The API may return more than rowLimit. We need to paginate.
        all_query_data = []
        while True:
            response = service.searchanalytics().query(siteUrl=site_url, body=request).execute()
            if 'rows' in response:
                all_query_data.extend(response['rows'])
                if len(response['rows']) < request['rowLimit']:
                    break # All data fetched
                request['startRow'] += request['rowLimit']
            else:
                break
        return all_query_data
    except HttpError as e:
        if e.resp.status == 403:
            print(f"Warning: Insufficient permission for site {site_url}. Skipping further monthly data for this property.")
            return "PERMISSION_DENIED" # Special indicator
        print(f"An HTTP error occurred for site {site_url} from {start_date} to {end_date}: {e}")
    except Exception as e:
        print(f"An unexpected error occurred for site {site_url} from {start_date} to {end_date}: {e}")
    return [] # Return an empty list if no data or error

def process_query_data_into_position_distribution(query_data):
    """
    Processes raw query data into aggregated clicks and impressions for predefined position ranges.
    Position ranges: 1-3, 4-10, 11-20, 21+
    """
    distribution = {
        'clicks_pos_1_3': 0, 'impressions_pos_1_3': 0,
        'clicks_pos_4_10': 0, 'impressions_pos_4_10': 0,
        'clicks_pos_11_20': 0, 'impressions_pos_11_20': 0,
        'clicks_pos_21_plus': 0, 'impressions_pos_21_plus': 0,
        'total_clicks': 0, 'total_impressions': 0
    }

    for row in query_data:
        clicks = row.get('clicks', 0)
        impressions = row.get('impressions', 0)
        position = row.get('position', 0)

        # Only sum to total_clicks/impressions if position is within a defined bucket (1 or greater)
        # This will ensure total_clicks equals the sum of the buckets.
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

def create_html_report(df, sorted_sites):
    """Generates an HTML report from the analysis dataframe."""
    
    # Generate the index of sites
    index_html = '<ul>'
    current_root_domain = None
    for site in sorted_sites:
        root_domain, order, subdomain = get_sort_key(site)
        
        # Determine if we need a new root domain heading
        if root_domain != current_root_domain:
            if current_root_domain is not None:
                index_html += '</ul></li>' # Close previous root domain's ul and li
            index_html += f'<li><strong>{root_domain}</strong><ul>' # Open new root domain's li and ul
            current_root_domain = root_domain

        # Create a URL-friendly anchor link
        anchor = site.replace('https://', '').replace('http://', '').replace(':', '-').replace('/', '-').replace('.', '-')
        
        if order == 0 or order == 1: # sc-domain or www
            # These are top-level within their root domain group
            index_html += f'<li><a href="#{anchor}">{site}</a></li>'
        else:
            # Other subdomains are indented
            index_html += f'<li>&nbsp;&nbsp;&nbsp;&nbsp;<a href="#{anchor}">{site}</a></li>'
            
    if current_root_domain is not None:
        index_html += '</ul></li>' # Close the last root domain's ul and li
    index_html += '</ul>'

    # Generate the individual site sections
    site_sections_html = generate_site_sections(df, sorted_sites)

    html_template = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Query Position Distribution Report</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body {{ padding: 2rem; }}
        .table-responsive {{ max-height: 800px; overflow-y: auto; }}
        h1, h2, h3 {{ border-bottom: 2px solid #dee2e6; padding-bottom: 0.5rem; margin-top: 2rem; }}
        footer {{ margin-top: 3rem; text-align: center; color: #6c757d; }}
        .table thead th {{ text-align: center; }}
    </style>
</head>
<body>
    <div class="container-fluid">
        <h1 class="mb-3" id="top">Query Position Distribution Report</h1>
        <h2>Index</h2>
        {index_html}
        {site_sections_html}
    </div>
    <footer>
        <p>
            <a href="https://github.com/liamdelahunty/gsc-exporter" target="_blank">gsc-exporter</a> | 
            <a href="../resources/how-to-read-the-query-position-report.html" target="_blank">How to Read this Report</a>
        </p>
    </footer>
</body>
</html>
"""
    return html_template

def generate_site_sections(df, sorted_sites):
    """Generates HTML sections for each site, displaying query position distribution."""
    sections_html = ''
    for site in sorted_sites:
        anchor = site.replace('https://', '').replace('http://', '').replace(':', '-').replace('/', '-').replace('.', '-')
        sections_html += f'<h2 id="{anchor}" class="mt-5">{site}</h2>'
        
        site_df = df[df['site_url'] == site].drop(columns=['site_url'])
        
        if not site_df.empty:
            # Format numbers for readability
            for col in site_df.columns:
                if ('clicks' in col or 'impressions' in col) and col in site_df.columns:
                    site_df[col] = site_df[col].apply(lambda x: f"{x:,.0f}")

            sections_html += '<div class="table-responsive">'
            sections_html += site_df.to_html(classes="table table-striped table-hover", index=False, border=0)
            sections_html += '</div>'
            sections_html += '<p><a href="#top">Back to Top</a></p>'
        else:
            sections_html += '<p>No data available for this site.</p>'
            sections_html += '<p><a href="#top">Back to Top</a></p>'
            
    return sections_html

def get_sort_key(site_url):
    """Creates a sort key for a site URL based on the specified sorting rules."""
    
    # Rule 1: Extract root domain for primary sorting
    if site_url.startswith('sc-domain:'):
        root_domain = site_url.replace('sc-domain:', '')
    else:
        netloc = urlparse(site_url).netloc
        parts = netloc.split('.')
        if len(parts) > 2 and parts[-2] in ['co', 'com', 'org', 'net', 'gov', 'edu'] and len(parts[-3]) > 2:
            root_domain = '.'.join(parts[-3:])
        elif len(parts) > 2:
            root_domain = '.'.join(parts[-2:])
        else:
            root_domain = netloc

    # Rule 2 & 3: Prioritise sc-domain and www
    if site_url.startswith('sc-domain:'):
        order = 0
        subdomain = ''
    elif urlparse(site_url).netloc.startswith('www.'):
        order = 1
        subdomain = ''
    else:
        order = 2
        subdomain = urlparse(site_url).netloc.split('.')[0]
        
    return (root_domain, order, subdomain)
    
def main():
    """Main function to run the account-wide analysis."""
    service = get_gsc_service()
    if not service:
        return

    sites = get_all_sites(service)
    if not sites:
        print("No sites found in your account.")
        return

    sites.sort(key=get_sort_key)

    all_data = []
    today = date.today()
    
    for site_url in sites: # Iterate through the sorted list of sites
        print(f"\nFetching data for site: {site_url}")
        for i in range(1, 17): # Last 16 months
            end_of_month = today.replace(day=1) - relativedelta(months=i-1) - timedelta(days=1)
            start_of_month = end_of_month.replace(day=1)
            
            start_date = start_of_month.strftime('%Y-%m-%d')
            end_date = end_of_month.strftime('%Y-%m-%d')

            query_data = get_monthly_query_data(service, site_url, start_date, end_date)
            
            if query_data == "PERMISSION_DENIED":
                break # Stop processing months for this site
            elif query_data: # If we got query data
                distribution_data = process_query_data_into_position_distribution(query_data)
                
                # Add site_url and month to the distribution data
                distribution_data['site_url'] = site_url
                distribution_data['month'] = start_of_month.strftime('%Y-%m')
                
                all_data.append(distribution_data)
    
    if not all_data:
        print("No performance data found for any site.")
        return
        
    df = pd.DataFrame(all_data)

    # Define the desired column order for CSV
    csv_column_order = [
        'site_url', 'month',
        'clicks_pos_1_3', 'impressions_pos_1_3',
        'clicks_pos_4_10', 'impressions_pos_4_10',
        'clicks_pos_11_20', 'impressions_pos_11_20',
        'clicks_pos_21_plus', 'impressions_pos_21_plus',
        'total_clicks', 'total_impressions'
    ]
    # Reindex the DataFrame to ensure the desired column order for CSV
    df = df.reindex(columns=csv_column_order)
    
    output_dir = 'output'
    os.makedirs(output_dir, exist_ok=True)
    
    most_recent_month = (today.replace(day=1) - timedelta(days=1)).strftime('%Y-%m')

    csv_file_name = f'query-position-performance-{most_recent_month}.csv'
    csv_output_path = os.path.join(output_dir, csv_file_name)

    html_file_name = f'query-position-performance-{most_recent_month}.html'
    html_output_path = os.path.join(output_dir, html_file_name)
    
    try:
        # Save the raw data to CSV before formatting for HTML
        df.to_csv(csv_output_path, index=False)
        print(f"\nSuccessfully exported CSV to {csv_output_path}")

        # Create a deep copy for HTML formatting
        html_df = df.copy()

        # Generate and save HTML report
        html_output = create_html_report(html_df, sites)
        with open(html_output_path, 'w', encoding='utf-8') as f:
            f.write(html_output)
        print(f"Successfully created HTML report at {html_output_path}")
    except PermissionError:
        print(f"\nError: Permission denied when trying to write to the output directory.")
        print(f"Please make sure you have write permissions for the directory: {output_dir}")
        print(f"Also, check if the file is already open in another program: {csv_file_name} or {html_file_name}")

if __name__ == '__main__':
    main()