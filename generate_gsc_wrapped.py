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
import sys
from jinja2 import Environment, FileSystemLoader

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
                print("Credentials have expired. Attempting to refresh...")
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

def get_gsc_data(service, site_url, start_date, end_date, dimensions, row_limit=25000):
    """Fetches GSC data for a given site, date range, and dimensions."""
    all_data = []
    start_row = 0
    print(f"Fetching GSC data for {site_url} from {start_date} to {end_date} with dimensions {dimensions}...")
    while True:
        try:
            request = {
                'startDate': start_date,
                'endDate': end_date,
                'dimensions': dimensions,
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
    return all_data

def generate_wrapped_narrative(wrapped_data):
    """Generates human-readable narrative strings from the wrapped_data."""
    narratives = {}

    # Overall Summary
    narratives['overall_summary'] = (
        f"In {wrapped_data['year']}, your site received an incredible "
        f"{wrapped_data['total_clicks']:,} clicks from search, generating "
        f"{wrapped_data['total_impressions']:,} impressions across Google Search."
    )

    # Top Page Highlight
    if wrapped_data['top_page'] != "N/A":
        narratives['top_page_highlight'] = (
            f"Your most popular page, '{wrapped_data['top_page']}', drove a massive "
            f"{wrapped_data['top_page_clicks']:,} clicks."
        )
    else:
        narratives['top_page_highlight'] = "No single top page could be identified."

    # Top Query Highlight
    if wrapped_data['top_query'] != "N/A":
        narratives['top_query_highlight'] = (
            f"The keyword that brought you the most attention was '{wrapped_data['top_query']}', accounting for "
            f"{wrapped_data['top_query_clicks']:,} clicks."
        )
    else:
        narratives['top_query_highlight'] = "No single top query could be identified."

    # Reach & Breadth
    narratives['reach_breadth'] = (
        f"Your content appeared for {wrapped_data['unique_queries']:,} different search queries "
        f"across {wrapped_data['unique_pages']:,} unique pages on your site."
    )

    # Busiest Month
    if wrapped_data['most_clicked_month'] != "N/A":
        narratives['busiest_month'] = (
            f"Your busiest month for search clicks was {wrapped_data['most_clicked_month']}, bringing in "
            f"{wrapped_data['most_clicked_month_clicks']:,} clicks."
        )
    else:
        narratives['busiest_month'] = "No busiest month could be identified."
    
    return narratives

def main():
    parser = argparse.ArgumentParser(
        description='Generate a "Spotify Wrapped" style report for Google Search Console data.',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument('site_url', help='The URL of the site to generate the report for.')

    date_group = parser.add_mutually_exclusive_group()
    date_group.add_argument(
        '--year-to-date',
        action='store_true',
        help='(Default) Analyse from Jan 1st of the current year to the end of the last complete month.'
    )
    date_group.add_argument(
        '--last-12-months',
        action='store_true',
        help='Analyse the last 12 complete months.'
    )
    date_group.add_argument(
        '--start-date',
        help='Start date in YYYY-MM-DD format. Must be used with --end-date.'
    )
    parser.add_argument(
        '--end-date',
        help='End date in YYYY-MM-DD format. Used only with --start-date.'
    )
    
    args = parser.parse_args()

    if args.start_date and not args.end_date:
        parser.error("--start-date must be used with --end-date.")

    site_url = args.site_url
    today = date.today()
    date_range_label = ""

    if args.last_12_months:
        end_of_last_month = today.replace(day=1) - timedelta(days=1)
        start_of_12_months_ago = (end_of_last_month - relativedelta(months=11)).replace(day=1)
        start_date = start_of_12_months_ago.strftime('%Y-%m-%d')
        end_date = end_of_last_month.strftime('%Y-%m-%d')
        date_range_label = f"{start_date}_to_{end_date}"
    elif args.start_date and args.end_date:
        start_date = args.start_date
        end_date = args.end_date
        date_range_label = f"{start_date}_to_{end_date}"
    else:  # Default to --year-to-date
        end_of_last_month = today.replace(day=1) - timedelta(days=1)
        start_date = f"{today.year}-01-01"
        end_date = end_of_last_month.strftime('%Y-%m-%d')
        date_range_label = f"{today.year}-YTD"

    service = get_gsc_service()
    if not service:
        return

    # Fetch data for date, query, and page
    raw_data = get_gsc_data(service, site_url, start_date, end_date, dimensions=['date', 'query', 'page'])

    if not raw_data:
        print(f"No data found for the given site and date range ({start_date} to {end_date}).")
        return

    df = pd.DataFrame(raw_data)
    # The 'keys' column contains the dimensions in the order they were requested
    df[['date', 'query', 'page']] = pd.DataFrame(df['keys'].tolist(), index=df.index)
    df.drop(columns=['keys'], inplace=True)

    # Convert date to datetime object
    df['date'] = pd.to_datetime(df['date'])

    # Ensure output directory exists
    if site_url.startswith('sc-domain:'):
        host_plain = site_url.replace('sc-domain:', '')
    else:
        host_plain = urlparse(site_url).netloc
    
    host_dir = host_plain.replace('www.', '')
    output_dir = os.path.join('output', host_dir)
    os.makedirs(output_dir, exist_ok=True)
    host_for_filename = host_dir.replace('.', '-')
    
    # Save raw data to CSV for debugging/re-use
    csv_filename = f"gsc-wrapped-raw-data-{host_for_filename}-{date_range_label}.csv"
    csv_output_path = os.path.join(output_dir, csv_filename)
    
    try:
        df.to_csv(csv_output_path, index=False, encoding='utf-8')
        print(f"\nSuccessfully saved raw GSC data to {csv_output_path}")
    except IOError as e:
        print(f"Error writing CSV to file: {e}")

    print("\nRaw data fetched and saved. Proceeding with analysis...")

    # 1. Total Clicks and Impressions for the year
    total_clicks = df['clicks'].sum()
    total_impressions = df['impressions'].sum()

    # 2. Top Page by Clicks
    top_page_df = df.groupby('page')['clicks'].sum().nlargest(1).reset_index()
    top_page = top_page_df.iloc[0]['page'] if not top_page_df.empty else "N/A"
    top_page_clicks = top_page_df.iloc[0]['clicks'] if not top_page_df.empty else 0

    # 3. Top Query by Clicks
    top_query_df = df.groupby('query')['clicks'].sum().nlargest(1).reset_index()
    top_query = top_query_df.iloc[0]['query'] if not top_query_df.empty else "N/A"
    top_query_clicks = top_query_df.iloc[0]['clicks'] if not top_query_df.empty else 0

    # 4. Total Unique Pages and Queries
    unique_pages = df['page'].nunique()
    unique_queries = df['query'].nunique()

    # 5. Month with Most Clicks
    df['month'] = df['date'].dt.to_period('M')
    monthly_clicks = df.groupby('month')['clicks'].sum().nlargest(1).reset_index()
    most_clicked_month = monthly_clicks.iloc[0]['month'].strftime('%B') if not monthly_clicks.empty else "N/A"
    most_clicked_month_clicks = monthly_clicks.iloc[0]['clicks'] if not monthly_clicks.empty else 0

    wrapped_data = {
        'site_url': site_url,
        'year': date_range_label.replace("_", " "), # Use a descriptive label
        'total_clicks': total_clicks,
        'total_impressions': total_impressions,
        'top_page': top_page,
        'top_page_clicks': top_page_clicks,
        'top_query': top_query,
        'top_query_clicks': top_query_clicks,
        'unique_pages': unique_pages,
        'unique_queries': unique_queries,
        'most_clicked_month': most_clicked_month,
        'most_clicked_month_clicks': most_clicked_month_clicks,
    }

    print("\n--- GSC Wrapped Key Metrics ---")
    for key, value in wrapped_data.items():
        print(f"{key.replace('_', ' ').title()}: {value:,}" if isinstance(value, (int, float)) else f"{key.replace('_', ' ').title()}: {value}")
    
    narratives = generate_wrapped_narrative(wrapped_data)
    print("\n--- Your GSC Wrapped Story ---")
    for key, narrative in narratives.items():
        print(f"- {narrative}")
    
    # Set up Jinja2 environment
    template_loader = FileSystemLoader('templates')
    env = Environment(loader=template_loader)
    template = env.get_template('gsc-wrapped-template.html')

    # Render the template
    html_output = template.render(wrapped_data=wrapped_data, narratives=narratives)

    # Save the rendered HTML to a file
    html_filename = f"gsc-wrapped-report-{host_for_filename}-{date_range_label}.html"
    html_output_path = os.path.join(output_dir, html_filename)

    try:
        with open(html_output_path, 'w', encoding='utf-8') as f:
            f.write(html_output)
        print(f"\nSuccessfully created GSC Wrapped HTML report at {html_output_path}")
    except IOError as e:
        print(f"Error writing HTML report to file: {e}")

if __name__ == '__main__':
    main()
