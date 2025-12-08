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

def get_gsc_data(service, site_url, start_date, end_date, dimensions, row_limit=25000, paginate=True):
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
                
                # Break the loop if we're not paginating or if we've received fewer rows than the limit
                if not paginate or len(rows) < row_limit:
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

import re

def get_root_domain(site_url):
    """Extracts a clean root domain from a GSC site URL."""
    if site_url.startswith('sc-domain:'):
        return site_url.replace('sc-domain:', '')
    
    hostname = urlparse(site_url).hostname
    if not hostname:
        return None
    
    # Use a regex to find the most likely root domain, handling .co.uk, .com, etc.
    match = re.search(r'([\w-]+\.(?:co\.uk|com\.au|co\.nz|co\.za|co\.il|co\.jp|com|org|net|biz|info))\s*$', hostname.lower())
    if match:
        return match.group(1)
    
    # Fallback for other TLDs
    parts = hostname.split('.')
    if len(parts) > 1:
        return '.'.join(parts[-2:])
    return hostname

def get_brand_terms(site_url):
    """
    Automatically extracts a set of likely brand terms from a site URL.

    Args:
        site_url (str): The URL of the site.

    Returns:
        set: A set of guessed brand terms.
    """
    if not site_url or site_url == "Loaded from CSV":
        return set()
        
    hostname = urlparse(site_url).hostname
    if not hostname:
        return set()

    # A list of common public suffixes to remove.
    # This is a simplified approach. A more robust solution might use a library
    # like tldextract, but this avoids adding a new dependency.
    suffixes_to_remove = ['.com', '.co.uk', '.org', '.net', '.gov', '.edu', '.io', '.co']
    
    # Remove 'www.' prefix
    if hostname.startswith('www.'):
        hostname = hostname[4:]
        
    # Iteratively remove suffixes
    for suffix in sorted(suffixes_to_remove, key=len, reverse=True):
        if hostname.endswith(suffix):
            hostname = hostname[:-len(suffix)]
            break # Stop after the first, longest match
            
    if not hostname:
        return set()

    # Generate variations
    terms = {hostname}
    if '-' in hostname:
        terms.add(hostname.replace('-', ' '))
        terms.add(hostname.replace('-', ''))
        
    print(f"Auto-detected brand terms: {terms}")
    return terms

def generate_wrapped_narrative(wrapped_data):
    """Generates human-readable narrative strings from the wrapped_data."""
    narratives = {}

    # Overall Summary
    narratives['overall_summary'] = (
        f"In the period {wrapped_data['report_period']}, your site received an incredible "
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
        f"Your content appeared for {wrapped_data['unique_queries_str']} different search queries "
        f"across {wrapped_data['unique_pages_str']} unique pages on your site."
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
        description='Generate a "Google Organic Wrapped"-style report for Google Search Console data.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='Example Usage:\n'
               '  To download data: python generate_gsc_wrapped.py https://www.example.com --last-12-months\n'
               '  To generate from a csv: python generate_gsc_wrapped.py --csv ./output/example-com/gsc-pages-queries-example-com-2024-01-01-to-2024-12-31.csv --site_url https://www.example.com',
    )
    parser.add_argument('site_url', nargs='?', help='The URL of the site to generate the report for. Required unless --csv is used, but needed for "Busiest Month" calculation.')
    parser.add_argument('--csv', help='Path to a CSV file to generate the report from. The CSV should contain "page", "query", "clicks", and "impressions" columns.')

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

    parser.add_argument('--no-brand-detection', action='store_true', help='Disable automatic brand term detection.')
    parser.add_argument('--brand-terms', nargs='+', help='A list of additional brand terms to include in the analysis.')
    parser.add_argument('--brand-terms-file', help='Path to a text file containing brand terms, one per line.')
    
    args = parser.parse_args()

    if not args.site_url and not args.csv:
        parser.error('`site_url` is required unless --csv is provided.')

    if args.csv and not args.site_url:
        print("Warning: `site_url` not provided with --csv. The 'Busiest Month' calculation will be skipped.")

    if args.start_date and not args.end_date:
        parser.error("--start-date must be used with --end-date.")

    site_url = args.site_url
    today = date.today()
    date_range_label = ""
    start_date = None
    end_date = None

    if args.csv:
        if args.year_to_date or args.last_12_months or args.start_date:
            print("Warning: Date range flags (--year-to-date, etc.) are ignored when --csv is used.")
        try:
            filename = os.path.basename(args.csv)
            parts = re.findall(r'(\d{4}-\d{2}-\d{2})-to-(\d{4}-\d{2}-\d{2})', filename)
            if parts:
                start_date = parts[0][0]
                end_date = parts[0][1]
                date_range_label = f"{start_date}_to_{end_date}"
            else:
                date_range_label = "Custom CSV Data"
        except Exception:
            date_range_label = "Custom CSV Data"
    elif args.last_12_months:
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

    # --- Data Loading and Processing ---
    is_csv_input = bool(args.csv)
    gsc_service = None
    
    if is_csv_input:
        if not os.path.exists(args.csv):
            print(f"Error: CSV file not found at '{args.csv}'")
            return
        print(f"Loading data from CSV: {args.csv}")
        df = pd.read_csv(args.csv)
        
        required_cols = ['page', 'query', 'clicks', 'impressions']
        if not all(col in df.columns for col in required_cols):
            print(f"Error: CSV must contain columns: {', '.join(required_cols)}")
            return
        
        print("Processing data from CSV...")
        total_clicks = df['clicks'].sum()
        total_impressions = df['impressions'].sum()

        top_pages_df = df.groupby('page')['clicks'].sum().nlargest(5).reset_index()
        top_pages = [{'url': row['page'], 'clicks': row['clicks']} for _, row in top_pages_df.iterrows()]

        queries_df = df.groupby('query')[['clicks', 'impressions']].sum().reset_index()
        
        unique_pages = df['page'].nunique()
        unique_queries = df['query'].nunique()
        unique_pages_str = f"{unique_pages:,}"
        unique_queries_str = f"{unique_queries:,}"

    else:
        gsc_service = get_gsc_service()
        if not gsc_service:
            return
        
        print(f"Fetching GSC data for {site_url} from {start_date} to {end_date}...")
        total_agg_data = get_gsc_data(gsc_service, site_url, start_date, end_date, dimensions=[], paginate=False)
        total_clicks = total_agg_data[0]['clicks'] if total_agg_data else 0
        total_impressions = total_agg_data[0]['impressions'] if total_agg_data else 0

        top_pages_data = get_gsc_data(gsc_service, site_url, start_date, end_date, dimensions=['page'], row_limit=5, paginate=False)
        top_pages = [{'url': item['keys'][0], 'clicks': item['clicks']} for item in top_pages_data] if top_pages_data else []

        all_top_queries_data = get_gsc_data(gsc_service, site_url, start_date, end_date, dimensions=['query'], row_limit=500, paginate=False)
        queries_df = pd.DataFrame(all_top_queries_data)
        if not queries_df.empty:
            queries_df['query'] = queries_df['keys'].apply(lambda x: x[0])
            queries_df.drop(columns=['keys'], inplace=True)
        
        page_count_batch = get_gsc_data(gsc_service, site_url, start_date, end_date, dimensions=['page'], row_limit=25000, paginate=False)
        unique_pages = len(page_count_batch) if page_count_batch is not None else 0
        unique_pages_str = "25,000+" if unique_pages == 25000 else f"{unique_pages:,}"
        
        query_count_batch = get_gsc_data(gsc_service, site_url, start_date, end_date, dimensions=['query'], row_limit=25000, paginate=False)
        unique_queries = len(query_count_batch) if query_count_batch is not None else 0
        unique_queries_str = "25,000+" if unique_queries == 25000 else f"{unique_queries:,}"

    # --- Brand Classification (Shared Logic) ---
    top_brand_queries = []
    top_non_brand_queries = []
    brand_terms = set()
    
    if 'query' in queries_df.columns and not queries_df.empty:
        # Priority 1: --brand-terms-file flag
        if args.brand_terms_file:
            if os.path.exists(args.brand_terms_file):
                with open(args.brand_terms_file, 'r') as f: brand_terms.update(line.strip().lower() for line in f if line.strip())
                print(f"Loaded {len(brand_terms)} brand terms from {args.brand_terms_file}")
            else:
                print(f"Warning: Brand terms file not found at '{args.brand_terms_file}'.")
        
        # Priority 2: Automatic file in /config
        elif not args.no_brand_detection and args.site_url:
            root_domain = get_root_domain(args.site_url)
            if root_domain:
                config_file_path = os.path.join('config', f'brand-terms-{root_domain.split(".")[0]}.txt')
                if os.path.exists(config_file_path):
                    with open(config_file_path, 'r') as f: brand_terms.update(line.strip().lower() for line in f if line.strip())
                    print(f"Loaded {len(brand_terms)} brand terms from {config_file_path} (auto-detected).")

        # Priority 3: Auto-detection from URL
        if not args.no_brand_detection and not brand_terms and args.site_url:
            brand_terms.update(get_brand_terms(args.site_url))

        # Priority 4: --brand-terms from command line
        if args.brand_terms:
            brand_terms.update(term.lower() for term in args.brand_terms)

        if brand_terms:
            print(f"Classifying queries with brand terms: {brand_terms}")
            pattern = r'\b(?:' + '|'.join(re.escape(term) for term in brand_terms) + r')\b'
            queries_df['brand_type'] = queries_df['query'].str.contains(pattern, case=False, regex=True).map({True: 'Brand', False: 'Non-Brand'})

            top_brand_queries_df = queries_df[queries_df['brand_type'] == 'Brand'].nlargest(5, 'clicks')
            top_brand_queries = [{'query': r['query'], 'clicks': r['clicks']} for _, r in top_brand_queries_df.iterrows()]
            
            top_non_brand_queries_df = queries_df[queries_df['brand_type'] == 'Non-Brand'].nlargest(5, 'clicks')
            top_non_brand_queries = [{'query': r['query'], 'clicks': r['clicks']} for _, r in top_non_brand_queries_df.iterrows()]
        else:
            print("No brand terms specified or detected; all queries are considered non-brand.")
            top_non_brand_queries_df = queries_df.nlargest(5, 'clicks')
            top_non_brand_queries = [{'query': r['query'], 'clicks': r['clicks']} for _, r in top_non_brand_queries_df.iterrows()]

    top_query = (top_non_brand_queries[0]['query'] if top_non_brand_queries else (top_brand_queries[0]['query'] if top_brand_queries else "N/A"))
    top_query_clicks = (top_non_brand_queries[0]['clicks'] if top_non_brand_queries else (top_brand_queries[0]['clicks'] if top_brand_queries else 0))

    # --- Monthly Performance Calculation ---
    most_clicked_month, most_clicked_month_clicks = "N/A", 0
    most_impressed_month, most_impressed_month_impressions = "N/A", 0
    highest_ctr_month, highest_ctr_month_ctr = "N/A", 0.0
    best_position_month, best_position_month_position = "N/A", 0.0

    if site_url and start_date and end_date:
        if not gsc_service: gsc_service = get_gsc_service() # Authenticate if not already
        
        if gsc_service:
            print("Fetching daily data for monthly performance calculation...")
            daily_data = get_gsc_data(gsc_service, site_url, start_date, end_date, dimensions=['date'], paginate=True)
            if daily_data:
                df_daily = pd.DataFrame(daily_data)
                df_daily['date'] = pd.to_datetime(df_daily['keys'].apply(lambda x: x[0]))
                df_daily['month'] = df_daily['date'].dt.to_period('M')
                
                # Clicks
                monthly_clicks = df_daily.groupby('month')['clicks'].sum().nlargest(1)
                if not monthly_clicks.empty:
                    most_clicked_month = monthly_clicks.index[0].strftime('%B')
                    most_clicked_month_clicks = monthly_clicks.values[0]
                
                # Impressions
                monthly_impressions = df_daily.groupby('month')['impressions'].sum().nlargest(1)
                if not monthly_impressions.empty:
                    most_impressed_month = monthly_impressions.index[0].strftime('%B')
                    most_impressed_month_impressions = monthly_impressions.values[0]

                # CTR
                monthly_agg = df_daily.groupby('month').agg(total_clicks=('clicks', 'sum'), total_impressions=('impressions', 'sum')).reset_index()
                monthly_agg['monthly_ctr'] = monthly_agg['total_clicks'] / monthly_agg['total_impressions']
                highest_ctr_month_series = monthly_agg.loc[monthly_agg['monthly_ctr'].idxmax()]
                highest_ctr_month = highest_ctr_month_series['month'].strftime('%B')
                highest_ctr_month_ctr = highest_ctr_month_series['monthly_ctr']

                # Position
                monthly_position = df_daily.groupby('month')['position'].mean().nsmallest(1) # smaller is better
                if not monthly_position.empty:
                    best_position_month = monthly_position.index[0].strftime('%B')
                    best_position_month_position = monthly_position.values[0]
        else:
            print("Warning: GSC authentication failed. Skipping monthly performance calculation.")
    else:
        print("Warning: Skipping monthly performance calculation (site_url and date range required).")

    # --- Report Generation ---
    if site_url:
        host_plain = urlparse(site_url).netloc if not site_url.startswith('sc-domain:') else site_url.replace('sc-domain:', '')
        host_dir = host_plain.replace('www.', '')
        output_dir = os.path.join('output', host_dir)
        os.makedirs(output_dir, exist_ok=True)
        host_for_filename = host_dir.replace('.', '-')
    else: # Fallback for CSV-only case
        host_plain = "csv-report"
        output_dir = "output"
        os.makedirs(output_dir, exist_ok=True)
        host_for_filename = "csv-report"


    print("\nAnalysis complete.")

    wrapped_data = {
        'site_url': site_url or "CSV Data",
        'hostname': host_plain,
        'report_period': date_range_label.replace("_", " "),
        'start_date': start_date or "N/A",
        'end_date': end_date or "N/A",
        'total_clicks': total_clicks,
        'total_impressions': total_impressions,
        'top_page': top_pages[0]['url'] if top_pages else "N/A",
        'top_page_clicks': top_pages[0]['clicks'] if top_pages else 0,
        'top_query': top_query,
        'top_query_clicks': top_query_clicks,
        'top_pages': top_pages,
        'top_brand_queries': top_brand_queries,
        'top_non_brand_queries': top_non_brand_queries,
        'unique_pages_str': unique_pages_str,
        'unique_queries_str': unique_queries_str,
        'most_clicked_month': most_clicked_month,
        'most_clicked_month_clicks': most_clicked_month_clicks,
        'most_impressed_month': most_impressed_month,
        'most_impressed_month_impressions': most_impressed_month_impressions,
        'highest_ctr_month': highest_ctr_month,
        'highest_ctr_month_ctr': highest_ctr_month_ctr,
        'best_position_month': best_position_month,
        'best_position_month_position': best_position_month_position,
    }

    print("\n--- Google Organic Wrapped Key Metrics ---")
    for key, value in wrapped_data.items():
        print(f"{key.replace('_', ' ').title()}: {value:,}" if isinstance(value, (int, float)) else f"{key.replace('_', ' ').title()}: {value}")
    
    narratives = generate_wrapped_narrative(wrapped_data)
    print("\n--- Your Google Organic Wrapped Story ---")
    for key, narrative in narratives.items():
        print(f"- {narrative}")
    
    # Set up Jinja2 environment
    template_loader = FileSystemLoader('templates')
    env = Environment(loader=template_loader)
    template = env.get_template('gsc-wrapped-template.html')

    # Render the template
    html_output = template.render(wrapped_data=wrapped_data, narratives=narratives)

    # Save the rendered HTML to a file
    html_filename = f"google-organic-wrapped-report-{host_for_filename}-{date_range_label}.html"
    html_output_path = os.path.join(output_dir, html_filename)

    try:
        with open(html_output_path, 'w', encoding='utf-8') as f:
            f.write(html_output)
        print(f"\nSuccessfully created Google Organic Wrapped HTML report at {html_output_path}")
    except IOError as e:
        print(f"Error writing HTML report to file: {e}")


if __name__ == '__main__':
    main()
