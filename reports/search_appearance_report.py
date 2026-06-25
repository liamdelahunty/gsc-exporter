"""
Generates a search appearance report for a single property or all properties in the account.
Exposes performance metrics (clicks, impressions, CTR, average position) segmented by Search Appearance.
"""
import os
import sys
import argparse
import pandas as pd
from datetime import datetime
from jinja2 import Environment, FileSystemLoader

# Add parent directory to sys.path to allow importing core
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.naming import get_output_dir, get_filename_slug
from core.cache import fetch_with_cache
from core.client import get_gsc_service, get_available_properties
from core.date_utils import parse_standard_date_args

def create_html_report(df, report_title, date_range_str, site_url=None):
    """Generates the HTML report using the standard template."""
    report_df = df.copy()

    # Format numeric columns
    report_df['clicks'] = pd.to_numeric(report_df['clicks'], errors='coerce').fillna(0)
    report_df['impressions'] = pd.to_numeric(report_df['impressions'], errors='coerce').fillna(0)
    report_df['ctr'] = pd.to_numeric(report_df['ctr'], errors='coerce').fillna(0)
    report_df['position'] = pd.to_numeric(report_df['position'], errors='coerce').fillna(0)

    # Apply formatting for display
    report_df_disp = report_df.copy()
    report_df_disp['clicks'] = report_df_disp['clicks'].apply(lambda x: f"{x:,.0f}")
    report_df_disp['impressions'] = report_df_disp['impressions'].apply(lambda x: f"{x:,.0f}")
    report_df_disp['ctr'] = report_df_disp['ctr'].apply(lambda x: f"{x:.2%}")
    report_df_disp['position'] = report_df_disp['position'].apply(lambda x: f"{x:.2f}")

    # Column renaming for readability
    rename_cols = {
        'searchAppearance': 'Search Appearance',
        'clicks': 'Clicks',
        'impressions': 'Impressions',
        'ctr': 'CTR',
        'position': 'Avg. Position'
    }
    if 'site_url' in report_df_disp.columns:
        rename_cols['site_url'] = 'Property'
        cols_order = ['Property', 'Search Appearance', 'Clicks', 'Impressions', 'CTR', 'Avg. Position']
        numeric_start_idx = 3
    else:
        cols_order = ['Search Appearance', 'Clicks', 'Impressions', 'CTR', 'Avg. Position']
        numeric_start_idx = 2

    report_df_disp = report_df_disp.rename(columns=rename_cols)
    report_df_disp = report_df_disp[cols_order]

    table_html = report_df_disp.to_html(classes="table table-striped table-hover", index=False, border=0)

    # Construct additional summary cards or charts if appropriate
    total_clicks = report_df['clicks'].sum()
    total_impressions = report_df['impressions'].sum()
    overall_ctr = total_clicks / total_impressions if total_impressions > 0 else 0

    summary_html = f"""
    <style>
        .table th, .table td {{
            text-align: left !important;
        }}
        .table th:nth-child(n+{numeric_start_idx}), 
        .table td:nth-child(n+{numeric_start_idx}) {{
            text-align: right !important;
        }}
    </style>
    <div class="row mb-4">
        <div class="col-md-4">
            <div class="card bg-primary text-white">
                <div class="card-body">
                    <h5 class="card-title">Total Clicks (Search Appearance)</h5>
                    <p class="card-text fs-2 fw-bold">{total_clicks:,.0f}</p>
                </div>
            </div>
        </div>
        <div class="col-md-4">
            <div class="card bg-success text-white">
                <div class="card-body">
                    <h5 class="card-title">Total Impressions</h5>
                    <p class="card-text fs-2 fw-bold">{total_impressions:,.0f}</p>
                </div>
            </div>
        </div>
        <div class="col-md-4">
            <div class="card bg-info text-white">
                <div class="card-body">
                    <h5 class="card-title">Overall CTR</h5>
                    <p class="card-text fs-2 fw-bold">{overall_ctr:.2%}</p>
                </div>
            </div>
        </div>
    </div>
    <div class="card mb-4">
        <div class="card-body">
            <h5 class="card-title">About Search Appearance Data</h5>
            <p class="card-text text-muted">
                Search appearance data categorises how your website results are displayed in Google Search. 
                This includes rich results (such as Product markup, FAQs, Videos) and special display features 
                like Translated Results. Note that some appearance types may only show for specific search queries or pages.
            </p>
        </div>
    </div>
    <div class="table-responsive">
        {table_html}
    </div>
    """

    template_loader = FileSystemLoader('resources')
    env = Environment(loader=template_loader)
    template = env.get_template('report-blank.html')

    html_output = template.render(
        title=report_title,
        report_name=report_title,
        domain_name=site_url if site_url else "All Properties",
        date_range=date_range_str,
        main_content=summary_html
    )

    return html_output

def run_report(service, site_url=None, start_date=None, end_date=None, all_properties=False):
    """Executes the Search Appearance report."""
    if all_properties or not site_url:
        print("Fetching all properties in the Google Search Console account...")
        sites = get_available_properties(service)
        if not sites:
            print("No properties found.")
            return None
        print(f"Found {len(sites)} properties. Retrieving search appearance data for each...")
    else:
        sites = [site_url]

    all_data = []

    for site in sites:
        print(f"  - Querying {site}...")
        try:
            # Query for searchAppearance
            df = fetch_with_cache(service, site, start_date, end_date, dimensions=['searchAppearance'])
            if not df.empty:
                df['site_url'] = site
                all_data.append(df)
        except Exception as e:
            print(f"Error querying {site}: {e}")

    if not all_data:
        print("No search appearance data found for any of the properties.")
        return None

    # Combine data from all properties
    combined_df = pd.concat(all_data, ignore_index=True)

    # Setup output destination
    if len(sites) == 1:
        output_dir = get_output_dir(sites[0])
        slug = get_filename_slug(sites[0])
        file_prefix = f"search-appearance-{slug}-{start_date}-to-{end_date}"
        report_title = f"Search Appearance Report for {sites[0]}"
        display_site = sites[0]
        
        # Sort and clean
        combined_df = combined_df.drop(columns=['site_url'])
        combined_df = combined_df.sort_values(by='clicks', ascending=False)
    else:
        output_dir = os.path.join('output', 'account')
        file_prefix = f"search-appearance-all-properties-{start_date}-to-{end_date}"
        report_title = "Account-wide Search Appearance Report"
        display_site = "All Properties"
        
        # Sort by property then clicks
        combined_df = combined_df.sort_values(by=['site_url', 'clicks'], ascending=[True, False])

    os.makedirs(output_dir, exist_ok=True)
    csv_path = os.path.join(output_dir, f"{file_prefix}.csv")
    html_path = os.path.join(output_dir, f"{file_prefix}.html")

    combined_df.to_csv(csv_path, index=False, encoding='utf-8')
    
    html_content = create_html_report(combined_df, report_title, f"{start_date} to {end_date}", display_site)
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(html_content)

    print(f"CSV saved to: {csv_path}")
    print(f"HTML saved to: {html_path}")
    return html_path

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Generate a report of search appearance metrics.')
    parser.add_argument('site_url', nargs='?', help='The URL of the site to analyse.')
    parser.add_argument('--all-properties', action='store_true', help='Retrieve data for all properties in the GSC account.')
    parser.add_argument('--start-date', help='Start date (YYYY-MM-DD).')
    parser.add_argument('--end-date', help='End date (YYYY-MM-DD).')
    parser.add_argument('--last-7-days', action='store_true', help='Run for the last 7 available days.')
    parser.add_argument('--last-month', action='store_true', help='Run for the last calendar month.')

    args = parser.parse_args()

    service = get_gsc_service()
    if service:
        # Determine start and end dates
        # Use first site as anchor if site_url is not provided
        anchor_site = args.site_url
        if not anchor_site:
            available_sites = get_available_properties(service)
            if available_sites:
                anchor_site = available_sites[0]
            else:
                print("No properties found to anchor dates.")
                sys.exit(1)
        
        start_date, end_date = parse_standard_date_args(args, service, anchor_site)
        run_report(service, args.site_url, start_date, end_date, args.all_properties)
