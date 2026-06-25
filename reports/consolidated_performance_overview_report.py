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
    """Generates the HTML report with separate tables per property, including totals and anchor links."""
    
    # 1. Format Search Types DataFrame
    df_types_disp = df_types.copy()
    df_types_disp['clicks'] = pd.to_numeric(df_types_disp['clicks'], errors='coerce').fillna(0)
    df_types_disp['impressions'] = pd.to_numeric(df_types_disp['impressions'], errors='coerce').fillna(0)
    df_types_disp['ctr'] = pd.to_numeric(df_types_disp['ctr'], errors='coerce').fillna(0)
    df_types_disp['position'] = pd.to_numeric(df_types_disp['position'], errors='coerce').fillna(0)

    unique_sites_types = sorted(df_types_disp['site_url'].unique())
    types_tables_html = []
    
    for site in unique_sites_types:
        site_df = df_types_disp[df_types_disp['site_url'] == site].copy()
        
        # Calculate totals
        tot_clicks = site_df['clicks'].sum()
        tot_imps = site_df['impressions'].sum()
        tot_ctr = tot_clicks / tot_imps if tot_imps > 0 else 0
        tot_pos = site_df['position'].mean()
        
        # Format the values for display
        site_df_disp = site_df.copy()
        site_df_disp['clicks'] = site_df_disp['clicks'].apply(lambda x: f"{x:,.0f}")
        site_df_disp['impressions'] = site_df_disp['impressions'].apply(lambda x: f"{x:,.0f}")
        site_df_disp['ctr'] = site_df_disp['ctr'].apply(lambda x: f"{x:.2%}")
        site_df_disp['position'] = site_df_disp['position'].apply(lambda x: f"{x:.2f}")
        
        # Drop site_url and rename columns
        site_df_disp = site_df_disp.drop(columns=['site_url'])
        site_df_disp = site_df_disp.rename(columns={
            'search_type': 'Search Type',
            'clicks': 'Clicks',
            'impressions': 'Impressions',
            'ctr': 'CTR',
            'position': 'Avg. Position'
        })
        site_df_disp = site_df_disp[['Search Type', 'Clicks', 'Impressions', 'CTR', 'Avg. Position']]
        
        # Convert all columns to strings to allow HTML tags in pandas output
        for col in site_df_disp.columns:
            site_df_disp[col] = site_df_disp[col].astype(str)
            
        # Append totals row
        total_row_df = pd.DataFrame([{
            'Search Type': '<strong>Total</strong>',
            'Clicks': f"<strong>{tot_clicks:,.0f}</strong>",
            'Impressions': f"<strong>{tot_imps:,.0f}</strong>",
            'CTR': f"<strong>{tot_ctr:.2%}</strong>",
            'Avg. Position': f"<strong>{tot_pos:.2f}</strong>"
        }])
        site_df_disp = pd.concat([site_df_disp, total_row_df], ignore_index=True)
        
        table_html = site_df_disp.to_html(classes="table table-striped table-hover", index=False, border=0, escape=False)
        
        types_tables_html.append(f"""
        <div class="property-block mb-4">
            <h5 class="property-title text-secondary mb-2">{site}</h5>
            {table_html}
        </div>
        """)
        
    types_content = "\n".join(types_tables_html) if types_tables_html else "<p class='text-muted'>No search type data found.</p>"

    # 2. Format Search Appearances DataFrame
    df_apps_disp = df_appearances.copy()
    df_apps_disp['clicks'] = pd.to_numeric(df_apps_disp['clicks'], errors='coerce').fillna(0)
    df_apps_disp['impressions'] = pd.to_numeric(df_apps_disp['impressions'], errors='coerce').fillna(0)
    df_apps_disp['ctr'] = pd.to_numeric(df_apps_disp['ctr'], errors='coerce').fillna(0)
    df_apps_disp['position'] = pd.to_numeric(df_apps_disp['position'], errors='coerce').fillna(0)

    unique_sites_apps = sorted(df_apps_disp['site_url'].unique())
    apps_tables_html = []
    
    for site in unique_sites_apps:
        site_df = df_apps_disp[df_apps_disp['site_url'] == site].copy()
        
        # Calculate totals
        tot_clicks = site_df['clicks'].sum()
        tot_imps = site_df['impressions'].sum()
        tot_ctr = tot_clicks / tot_imps if tot_imps > 0 else 0
        tot_pos = site_df['position'].mean()
        
        # Format the values for display
        site_df_disp = site_df.copy()
        site_df_disp['clicks'] = site_df_disp['clicks'].apply(lambda x: f"{x:,.0f}")
        site_df_disp['impressions'] = site_df_disp['impressions'].apply(lambda x: f"{x:,.0f}")
        site_df_disp['ctr'] = site_df_disp['ctr'].apply(lambda x: f"{x:.2%}")
        site_df_disp['position'] = site_df_disp['position'].apply(lambda x: f"{x:.2f}")
        
        # Drop site_url and rename columns
        site_df_disp = site_df_disp.drop(columns=['site_url'])
        site_df_disp = site_df_disp.rename(columns={
            'searchAppearance': 'Search Appearance',
            'clicks': 'Clicks',
            'impressions': 'Impressions',
            'ctr': 'CTR',
            'position': 'Avg. Position'
        })
        site_df_disp = site_df_disp[['Search Appearance', 'Clicks', 'Impressions', 'CTR', 'Avg. Position']]
        
        # Convert all columns to strings to allow HTML tags in pandas output
        for col in site_df_disp.columns:
            site_df_disp[col] = site_df_disp[col].astype(str)
            
        # Append totals row
        total_row_df = pd.DataFrame([{
            'Search Appearance': '<strong>Total</strong>',
            'Clicks': f"<strong>{tot_clicks:,.0f}</strong>",
            'Impressions': f"<strong>{tot_imps:,.0f}</strong>",
            'CTR': f"<strong>{tot_ctr:.2%}</strong>",
            'Avg. Position': f"<strong>{tot_pos:.2f}</strong>"
        }])
        site_df_disp = pd.concat([site_df_disp, total_row_df], ignore_index=True)
        
        table_html = site_df_disp.to_html(classes="table table-striped table-hover", index=False, border=0, escape=False)
        
        apps_tables_html.append(f"""
        <div class="property-block mb-4">
            <h5 class="property-title text-secondary mb-2">{site}</h5>
            {table_html}
        </div>
        """)
        
    apps_content = "\n".join(apps_tables_html) if apps_tables_html else "<p class='text-muted'>No search appearance data found.</p>"

    # 3. Create main content with explanation
    main_html = f"""
    <style>
        .table th, .table td {{
            text-align: left !important;
        }}
        .table th:nth-child(n+2), 
        .table td:nth-child(n+2) {{
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
        .property-block {{
            background-color: #ffffff;
            border: 1px solid #e3e6f0;
            border-radius: 4px;
            padding: 1.5rem;
            margin-bottom: 2rem;
            box-shadow: 0 0.15rem 1.75rem 0 rgba(58, 59, 69, 0.05);
        }}
        .property-title {{
            font-size: 1.1rem;
            font-weight: 700;
            border-bottom: 1px solid #eaecf4;
            padding-bottom: 0.5rem;
        }}
        .quick-nav {{
            background-color: #eaecf4;
            border-radius: 4px;
            padding: 0.75rem;
            margin-bottom: 2rem;
        }}
    </style>

    <div class="quick-nav d-flex justify-content-center">
        <a href="#search-types-section" class="btn btn-primary btn-sm me-3">Jump to Search Types</a>
        <a href="#search-appearances-section" class="btn btn-primary btn-sm">Jump to Search Appearances</a>
    </div>

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

    <h2 id="search-types-section">1. Search Type Performance by Property</h2>
    <p class="text-muted mb-4">Displays performance across Google search channels (Web, Discover, News, Image, Video, Google News) with a total for each property.</p>
    <div class="mb-5">
        {types_content}
    </div>

    <h2 id="search-appearances-section">2. Search Appearance Performance by Property</h2>
    <p class="text-muted mb-4">Displays performance for enhanced search features (such as product markup or translation features) with a total for each property.</p>
    <div>
        {apps_content}
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
