"""
Generates a consolidated performance overview report across all properties in the GSC account.
Consolidates both Search Type performance and Search Appearance performance, highlighting overlaps and structural differences.
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

SEARCH_TYPES = ['web', 'image', 'video', 'news', 'discover', 'googleNews']

def create_consolidated_html(df_types, df_appearances, date_range_str):
    """Generates the HTML report with two tables and an explanation of the data overlap."""
    
    # 1. Format Search Types DataFrame
    df_types_disp = df_types.copy()
    df_types_disp['clicks'] = pd.to_numeric(df_types_disp['clicks'], errors='coerce').fillna(0)
    df_types_disp['impressions'] = pd.to_numeric(df_types_disp['impressions'], errors='coerce').fillna(0)
    df_types_disp['ctr'] = pd.to_numeric(df_types_disp['ctr'], errors='coerce').fillna(0)
    df_types_disp['position'] = pd.to_numeric(df_types_disp['position'], errors='coerce').fillna(0)

    df_types_disp_formatted = df_types_disp.copy()
    df_types_disp_formatted['clicks'] = df_types_disp_formatted['clicks'].apply(lambda x: f"{x:,.0f}")
    df_types_disp_formatted['impressions'] = df_types_disp_formatted['impressions'].apply(lambda x: f"{x:,.0f}")
    df_types_disp_formatted['ctr'] = df_types_disp_formatted['ctr'].apply(lambda x: f"{x:.2%}")
    df_types_disp_formatted['position'] = df_types_disp_formatted['position'].apply(lambda x: f"{x:.2f}")

    df_types_disp_formatted = df_types_disp_formatted.rename(columns={
        'site_url': 'Property',
        'search_type': 'Search Type',
        'clicks': 'Clicks',
        'impressions': 'Impressions',
        'ctr': 'CTR',
        'position': 'Avg. Position'
    })
    df_types_disp_formatted = df_types_disp_formatted[['Property', 'Search Type', 'Clicks', 'Impressions', 'CTR', 'Avg. Position']]
    types_table_html = df_types_disp_formatted.to_html(classes="table table-striped table-hover", index=False, border=0)

    # 2. Format Search Appearances DataFrame
    df_apps_disp = df_appearances.copy()
    df_apps_disp['clicks'] = pd.to_numeric(df_apps_disp['clicks'], errors='coerce').fillna(0)
    df_apps_disp['impressions'] = pd.to_numeric(df_apps_disp['impressions'], errors='coerce').fillna(0)
    df_apps_disp['ctr'] = pd.to_numeric(df_apps_disp['ctr'], errors='coerce').fillna(0)
    df_apps_disp['position'] = pd.to_numeric(df_apps_disp['position'], errors='coerce').fillna(0)

    df_apps_disp_formatted = df_apps_disp.copy()
    df_apps_disp_formatted['clicks'] = df_apps_disp_formatted['clicks'].apply(lambda x: f"{x:,.0f}")
    df_apps_disp_formatted['impressions'] = df_apps_disp_formatted['impressions'].apply(lambda x: f"{x:,.0f}")
    df_apps_disp_formatted['ctr'] = df_apps_disp_formatted['ctr'].apply(lambda x: f"{x:.2%}")
    df_apps_disp_formatted['position'] = df_apps_disp_formatted['position'].apply(lambda x: f"{x:.2f}")

    df_apps_disp_formatted = df_apps_disp_formatted.rename(columns={
        'site_url': 'Property',
        'searchAppearance': 'Search Appearance',
        'clicks': 'Clicks',
        'impressions': 'Impressions',
        'ctr': 'CTR',
        'position': 'Avg. Position'
    })
    df_apps_disp_formatted = df_apps_disp_formatted[['Property', 'Search Appearance', 'Clicks', 'Impressions', 'CTR', 'Avg. Position']]
    apps_table_html = df_apps_disp_formatted.to_html(classes="table table-striped table-hover", index=False, border=0)

    # 3. Create main content with explanation
    main_html = f"""
    <style>
        .table th, .table td {{
            text-align: left !important;
        }}
        .table th:nth-child(n+3), 
        .table td:nth-child(n+3) {{
            text-align: right !important;
        }}
        .explanation-card {{
            background-color: #f8f9fa;
            border-left: 5px solid #0d6efd;
            border-radius: 4px;
            padding: 1.5rem;
            margin-bottom: 2.5rem;
        }}
        h2 {{
            margin-top: 2rem;
            margin-bottom: 1rem;
            border-bottom: 2px solid #dee2e6;
            padding-bottom: 0.5rem;
        }}
    </style>

    <div class="explanation-card shadow-sm">
        <h4 class="text-primary mb-3">Understanding the Data Structures and Overlap</h4>
        <p>This consolidated report displays Search Console metrics categorised by both <strong>Search Type</strong> and <strong>Search Appearance</strong>. It is important to note how these datasets relate to each other:</p>
        <ul>
            <li>
                <strong>Search Type (Table 1):</strong> Segments traffic based on Google's search surfaces (Web, News, Discover, etc.). These represent distinct user journeys and are largely mutually exclusive. The sum of clicks in this table represents your overall search performance.
            </li>
            <li>
                <strong>Search Appearance (Table 2):</strong> Segments traffic by visual enhancements on Google Search (such as rich snippets, translated results, or product schema). These represent subset tags applied to search results.
            </li>
            <li>
                <strong>The Overlap:</strong> Search Appearance metrics exist <em>within</em> Search Type traffic (mainly within Web search). A single search click can trigger multiple Search Appearance tags (e.g., a page displaying both Product Snippets and Review Stars), leading to double-counting within the Search Appearance table. Consequently, summing Table 2 will not equal your total search traffic, and the two tables should always be analysed separately.
            </li>
        </ul>
    </div>

    <h2>1. Search Type Performance Overview</h2>
    <p class="text-muted">Displays performance across Google search channels (Web, Discover, News, Image, Video, Google News).</p>
    <div class="table-responsive mb-5">
        {types_table_html}
    </div>

    <h2>2. Search Appearance Performance Overview</h2>
    <p class="text-muted">Displays performance for enhanced search features (such as product markup or translation features).</p>
    <div class="table-responsive">
        {apps_table_html}
    </div>
    """

    template_loader = FileSystemLoader('resources')
    env = Environment(loader=template_loader)
    template = env.get_template('report-blank.html')

    html_output = template.render(
        title="Consolidated Performance Overview",
        report_name="Consolidated Performance Overview",
        domain_name="All Properties",
        date_range=date_range_str,
        main_content=main_html
    )

    return html_output

def run_report(service, start_date, end_date):
    """Retrieves and generates the consolidated report."""
    print("Fetching all properties in the Google Search Console account...")
    sites = get_available_properties(service)
    if not sites:
        print("No properties found.")
        return None
    print(f"Found {len(sites)} properties. Processing performance data...")

    search_types_data = []
    search_appearance_data = []

    for site in sites:
        print(f"  - Querying {site}...")
        
        # 1. Query Search Types
        for st in SEARCH_TYPES:
            try:
                df = fetch_with_cache(service, site, start_date, end_date, dimensions=[], search_type=st)
                if not df.empty:
                    df['site_url'] = site
                    df['search_type'] = st
                    search_types_data.append(df)
            except Exception as e:
                print(f"    Error querying search type '{st}' for {site}: {e}")

        # 2. Query Search Appearances (under the default 'web' search type)
        try:
            df_app = fetch_with_cache(service, site, start_date, end_date, dimensions=['searchAppearance'])
            if not df_app.empty:
                df_app['site_url'] = site
                search_appearance_data.append(df_app)
        except Exception as e:
            print(f"    Error querying search appearance for {site}: {e}")

    # Process Search Types
    if search_types_data:
        df_types_combined = pd.concat(search_types_data, ignore_index=True)
        df_types_combined = df_types_combined.sort_values(by=['site_url', 'clicks'], ascending=[True, False])
    else:
        df_types_combined = pd.DataFrame(columns=['site_url', 'search_type', 'clicks', 'impressions', 'ctr', 'position'])

    # Process Search Appearances
    if search_appearance_data:
        df_apps_combined = pd.concat(search_appearance_data, ignore_index=True)
        df_apps_combined = df_apps_combined.sort_values(by=['site_url', 'clicks'], ascending=[True, False])
    else:
        df_apps_combined = pd.DataFrame(columns=['site_url', 'searchAppearance', 'clicks', 'impressions', 'ctr', 'position'])

    # Setup output destination
    output_dir = os.path.join('output', 'account')
    os.makedirs(output_dir, exist_ok=True)
    
    file_prefix = f"consolidated-performance-overview-{start_date}-to-{end_date}"
    
    csv_types_path = os.path.join(output_dir, f"{file_prefix}-search-types.csv")
    csv_apps_path = os.path.join(output_dir, f"{file_prefix}-search-appearances.csv")
    html_path = os.path.join(output_dir, f"{file_prefix}.html")

    # Save CSVs
    df_types_combined.to_csv(csv_types_path, index=False, encoding='utf-8')
    df_apps_combined.to_csv(csv_apps_path, index=False, encoding='utf-8')

    # Save HTML
    html_content = create_consolidated_html(df_types_combined, df_apps_combined, f"{start_date} to {end_date}")
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(html_content)

    print(f"\nCSV (Search Types) saved to: {csv_types_path}")
    print(f"CSV (Search Appearances) saved to: {csv_apps_path}")
    print(f"HTML Overview saved to: {html_path}")
    return html_path

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Generate a consolidated performance overview report by search type and appearance.')
    parser.add_argument('site_url', nargs='?', help='Anchor URL of the site to parse dates (optional).')
    parser.add_argument('--start-date', help='Start date (YYYY-MM-DD).')
    parser.add_argument('--end-date', help='End date (YYYY-MM-DD).')
    parser.add_argument('--last-7-days', action='store_true', help='Run for the last 7 available days.')
    parser.add_argument('--last-month', action='store_true', help='Run for the last calendar month.')

    args = parser.parse_args()

    service = get_gsc_service()
    if service:
        # Determine start and end dates
        anchor_site = args.site_url
        if not anchor_site:
            available_sites = get_available_properties(service)
            if available_sites:
                anchor_site = available_sites[0]
            else:
                print("No properties found to anchor dates.")
                sys.exit(1)
        
        start_date, end_date = parse_standard_date_args(args, service, anchor_site)
        run_report(service, start_date, end_date)
