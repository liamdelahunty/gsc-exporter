"""
Report script to compare GSC Page-Level (Unfiltered) and Query-Level (Filtered) data for a site.
Helps detect organic traffic data loss due to GSC privacy thresholds and inspects directory structure.
"""
import os
import sys
import pandas as pd
import argparse
import html
from datetime import datetime
from urllib.parse import urlparse

# Add parent directory to sys.path to allow importing core
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.naming import get_output_dir, get_filename_slug
from core.cache import fetch_with_cache
from core.client import get_gsc_service
from core.date_utils import parse_standard_date_args

# Dictionary of educated guesses for directory purposes (both Drupal legacy and new Dato structures)
FOLDER_PURPOSES = {
    'root': 'Homepage / Main portal landing page.',
    'features': 'New DatoCMS structure housing current news updates, editorial commentaries, and deep-dive articles on topical HR developments.',
    'guides': 'New DatoCMS structure for comprehensive handbooks, step-by-step guides, and detailed explanations of international labour laws.',
    'resources': 'New DatoCMS structure containing standard forms, downloadable template files (such as payslips), and contract agreements.',
    'employment-rights-act': 'New DatoCMS structure dedicated to resources, policy summaries, and updates regarding the UK Employment Rights Act.',
    'policies': 'New DatoCMS structure containing standard company policy drafts, employee handbooks, and workplace regulation templates.',
    'employment_law': 'Legacy Drupal directory that previously housed international labour law pages, now superseded by the /guides/ folder.',
    'comment-and-analysis': 'Legacy Drupal directory used for news updates and webinars, now consolidated into /features/.',
    'news-article': 'Legacy Drupal directory containing news and tribunal/supreme court case summaries, now consolidated into /features/.',
    'node': 'Legacy Drupal database entity paths representing old raw articles or documents, now mapped to structured Dato URLs.',
    'templates-and-tools': 'Legacy Drupal directory for downloadable contract templates and letters, now replaced by /resources/.',
    'system': 'Legacy Drupal system folder containing downloadable DOCX/PDF files, now replaced by structured web resources.',
}

def get_first_folder(url):
    """Extracts the first path segment from a URL."""
    try:
        parsed = urlparse(url)
        path = parsed.path.strip('/')
        if not path:
            return 'root'
        return path.split('/')[0]
    except Exception:
        return 'unknown'

def classify_platform(folder):
    """Determines whether a folder belongs to the old Drupal or new Dato setup."""
    dato_folders = {'features', 'guides', 'resources', 'employment-rights-act', 'policies', 'root'}
    
    if folder in dato_folders:
        return '<span class="badge bg-success">DatoCMS (New)</span>'
    elif folder == 'Unique page folder':
        return '<span class="badge bg-secondary">Various</span>'
    else:
        return '<span class="badge bg-purple" style="background-color: #6f42c1;">Drupal (Old)</span>'

def build_html_report(site_url, start_date, end_date, stats, df_folders, df_pages):
    """Renders the HTML report dashboard comparing GSC datasets."""
    slug = get_filename_slug(site_url)
    
    # Navigation Links
    nav_html = f"""
    <div class="d-flex flex-wrap gap-2 justify-content-center mb-4 pb-3 border-bottom">
        <a href="dato-drupal-index-{slug}-{start_date}-to-{end_date}.html" class="btn btn-outline-primary px-4">Migration Index</a>
        <a href="drupal-dato-migration-analysis-{slug}-{start_date}-to-{end_date}.html" class="btn btn-outline-primary px-4">Breakdown Dashboard (Query-Level)</a>
        <a href="drupal-dato-migration-page-level-report-{slug}-{start_date}-to-{end_date}.html" class="btn btn-outline-primary px-4">Page-Level Report (All Clicks)</a>
        <a href="drupal-dato-migration-prioritisation-report-{slug}-{start_date}-to-{end_date}.html" class="btn btn-outline-primary px-4">Top 50 Prioritisation Report</a>
        <a href="dato-suggested-urls-alphabetical-{slug}-{start_date}-to-{end_date}.html" class="btn btn-outline-primary px-4">Proposed Dato URLs (Alphabetical)</a>
        <a href="gsc-data-comparison-{slug}-{start_date}-to-{end_date}.html" class="btn btn-primary active px-4">GSC Data Comparison</a>
        <a href="dato-pages-performance-report-{slug}-{start_date}-to-{end_date}.html" class="btn btn-outline-primary px-4">Dato Pages Performance</a>
    </div>
    """

    # Folders rows
    folder_rows = []
    for _, row in df_folders.iterrows():
        folder = row['folder']
        p_clicks = int(row['page_clicks'])
        q_clicks = int(row['query_clicks'])
        p_count = int(row['page_count'])
        platform = classify_platform(folder)
        
        if folder == 'Unique page folder':
            folder_display = "Unique page folders (Collated)"
            purpose = "Collated summary of single-page directories across the legacy and new site structures."
        else:
            folder_display = f"/{folder}/"
            purpose = FOLDER_PURPOSES.get(folder, f"Bespoke legacy Drupal directory for /{folder}/ content.")
            
        folder_rows.append(f"""
        <tr>
            <td><code>{html.escape(folder_display)}</code></td>
            <td class="text-end fw-bold">{p_clicks:,}</td>
            <td class="text-end">{q_clicks:,}</td>
            <td class="text-end">{p_count:,}</td>
            <td class="text-center">{platform}</td>
            <td>{purpose}</td>
        </tr>
        """)
    folder_rows_html = "\n".join(folder_rows)

    # Pages rows
    page_rows = []
    for i, row in df_pages.iterrows():
        url = row['page']
        p_clicks = int(row['clicks'])
        q_clicks = int(row['query_clicks'])
        delta = int(row['clicks_delta'])
        status = row['dataset_status']
        
        # Format status badge
        if status == 'Unique to Page-Level':
            status_badge = '<span class="badge bg-warning text-dark">Unique to Page-Level (Unfiltered)</span>'
        elif status == 'Unique to Query-Level':
            status_badge = '<span class="badge bg-info text-dark">Unique to Query-Level</span>'
        else:
            status_badge = '<span class="badge bg-light text-dark">Present in Both</span>'
            
        page_rows.append(f"""
        <tr class="url-row">
            <td class="text-center">{i + 1}</td>
            <td class="text-break"><a href="{url}" target="_blank">{html.escape(url)}</a></td>
            <td class="text-end fw-bold">{p_clicks:,}</td>
            <td class="text-end">{q_clicks:,}</td>
            <td class="text-end text-danger fw-bold">{delta:,}</td>
            <td class="text-center">{status_badge}</td>
        </tr>
        """)
    page_rows_html = "\n".join(page_rows)

    # Compile the final template
    html_content = f"""<!DOCTYPE html>
<html lang="en-GB">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>GSC Data Comparison &amp; Folder Audit: {html.escape(site_url)}</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body {{
            background-color: #f8f9fa;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            color: #333;
            padding-bottom: 4rem;
        }}
        h1, h2, h3, h4 {{
            font-weight: 700;
            color: #2c3e50;
        }}
        .metric-card {{
            border: none;
            border-radius: 12px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.05);
            background-color: #fff;
        }}
        .table-responsive {{
            border-radius: 12px;
            overflow: hidden;
            box-shadow: 0 4px 12px rgba(0,0,0,0.05);
            background-color: #fff;
            margin-top: 1.5rem;
            margin-bottom: 2.5rem;
        }}
        .badge-delta {{
            font-size: 0.85rem;
            padding: 0.4rem 0.6rem;
            border-radius: 6px;
        }}
    </style>
</head>
<body>

<div class="container-fluid py-4">
    <!-- Header -->
    <div class="d-flex align-items-center justify-content-between border-bottom pb-3 mb-4">
        <div>
            <h1 class="h3 mb-1 fw-bold text-dark">GSC Data Comparison &amp; Directory Audit</h1>
            <p class="text-muted mb-0">Property: <strong>{html.escape(site_url)}</strong> | Reporting Period: <strong>{start_date} to {end_date}</strong></p>
        </div>
        <div class="text-end">
            <span class="badge bg-secondary p-2">Generated on {datetime.now().strftime('%Y-%m-%d')}</span>
        </div>
    </div>

    {nav_html}

    <!-- High-Level KPI Comparison Cards -->
    <div class="row g-4 mb-4">
        <!-- Clicks comparison -->
        <div class="col-md-4">
            <div class="card metric-card p-4 border-start border-primary border-4">
                <h6 class="text-muted text-uppercase fw-bold mb-2">Total Organic Clicks</h6>
                <div class="d-flex align-items-baseline justify-content-between">
                    <div>
                        <span class="h3 fw-bold text-dark">{stats['page_clicks']:,}</span>
                        <small class="text-muted d-block" style="font-size: 0.8rem;">Page-Level (Unfiltered)</small>
                    </div>
                    <div>
                        <span class="h4 fw-semibold text-secondary">{stats['query_clicks']:,}</span>
                        <small class="text-muted d-block" style="font-size: 0.8rem;">Query-Level (Filtered)</small>
                    </div>
                </div>
                <div class="mt-3">
                    <span class="badge bg-danger badge-delta">
                        -{stats['clicks_diff']:,} (-{stats['clicks_diff_pct']:.1%}) lost to GSC privacy thresholds
                    </span>
                </div>
            </div>
        </div>

        <!-- Impressions comparison -->
        <div class="col-md-4">
            <div class="card metric-card p-4 border-start border-info border-4">
                <h6 class="text-muted text-uppercase fw-bold mb-2">Total Organic Impressions</h6>
                <div class="d-flex align-items-baseline justify-content-between">
                    <div>
                        <span class="h3 fw-bold text-dark">{stats['page_impressions']:,}</span>
                        <small class="text-muted d-block" style="font-size: 0.8rem;">Page-Level (Unfiltered)</small>
                    </div>
                    <div>
                        <span class="h4 fw-semibold text-secondary">{stats['query_impressions']:,}</span>
                        <small class="text-muted d-block" style="font-size: 0.8rem;">Query-Level (Filtered)</small>
                    </div>
                </div>
                <div class="mt-3">
                    <span class="badge bg-danger badge-delta">
                        -{stats['impressions_diff']:,} (-{stats['impressions_diff_pct']:.1%}) lost to privacy thresholds
                    </span>
                </div>
            </div>
        </div>

        <!-- Pages comparison -->
        <div class="col-md-4">
            <div class="card metric-card p-4 border-start border-warning border-4">
                <h6 class="text-muted text-uppercase fw-bold mb-2">Landing Pages with Traffic</h6>
                <div class="d-flex align-items-baseline justify-content-between">
                    <div>
                        <span class="h3 fw-bold text-dark">{stats['page_pages']:,}</span>
                        <small class="text-muted d-block" style="font-size: 0.8rem;">Page-Level (Unfiltered)</small>
                    </div>
                    <div>
                        <span class="h4 fw-semibold text-secondary">{stats['query_pages']:,}</span>
                        <small class="text-muted d-block" style="font-size: 0.8rem;">Query-Level (Filtered)</small>
                    </div>
                </div>
                <div class="mt-3">
                    <span class="badge bg-danger badge-delta">
                        -{stats['pages_diff']:,} (-{stats['pages_diff_pct']:.1%}) below query threshold
                    </span>
                </div>
            </div>
        </div>
    </div>

    <!-- Directory Analysis Table -->
    <h3 class="fw-bold mt-5 mb-3 text-secondary">Directory Structure &amp; Folder Purpose Audit</h3>
    <p class="text-muted">Below is an inventory of all first-level directories found in the GSC performance logs, showing aggregated metrics and an educated guess as to the core purpose of each directory on the platform.</p>
    
    <div class="table-responsive">
        <table class="table table-hover table-striped align-middle mb-0">
            <thead class="table-dark">
                <tr>
                    <th style="width: 200px;">Directory Path</th>
                    <th class="text-end" style="width: 150px;">Clicks (Page-Level)</th>
                    <th class="text-end" style="width: 150px;">Clicks (Query-Level)</th>
                    <th class="text-end" style="width: 130px;">Pages Count</th>
                    <th class="text-center" style="width: 200px;">Platform Type</th>
                    <th>Educated Guess of Core Purpose</th>
                </tr>
            </thead>
            <tbody>
                {folder_rows_html}
            </tbody>
        </table>
    </div>

    <!-- Granular URL Comparison Table -->
    <div class="d-flex align-items-center justify-content-between mb-3 mt-5">
        <div>
            <h3 class="fw-bold text-dark mb-1">GSC Page-Level vs Query-Level URL Registry</h3>
            <p class="text-muted mb-0">Compares metrics side-by-side. Unfiltered landing pages unique to Page-Level represent organic traffic lost to GSC privacy thresholds.</p>
        </div>
        <div style="width: 350px;">
            <input type="text" id="urlSearch" class="form-control" placeholder="Search URLs or status...">
        </div>
    </div>

    <div class="table-responsive">
        <table id="comparisonTable" class="table table-hover table-striped align-middle mb-0">
            <thead class="table-dark">
                <tr>
                    <th class="text-center" style="width: 60px;">Rank</th>
                    <th>Landing Page URL</th>
                    <th class="text-end" style="width: 150px;">Clicks (Page-Level)</th>
                    <th class="text-end" style="width: 150px;">Clicks (Query-Level)</th>
                    <th class="text-end" style="width: 150px;">Delta (Privacy Loss)</th>
                    <th class="text-center" style="width: 250px;">Dataset Status</th>
                </tr>
            </thead>
            <tbody>
                {page_rows_html}
            </tbody>
        </table>
    </div>
</div>

<script>
    // Live search function
    document.getElementById('urlSearch').addEventListener('keyup', function() {{
        var filter = this.value.toLowerCase();
        var rows = document.querySelectorAll('#comparisonTable tbody .url-row');
        
        rows.forEach(function(row) {{
            var urlText = row.textContent.toLowerCase();
            if (urlText.indexOf(filter) > -1) {{
                row.style.display = '';
            }} else {{
                row.style.display = 'none';
            }}
        }});
    }});
</script>
</body>
</html>
"""
    return html_content

def run_report(service, site_url, start_date, end_date):
    """Fetches data and compiles the GSC comparison and folder audit report."""
    print(f"Running GSC dataset comparison report for {site_url}...")
    print(f"Reporting period: {start_date} to {end_date}")
    
    # 1. Fetch Query-level data (dimensions: query, page)
    print("Fetching query-level GSC data...")
    df_query = fetch_with_cache(service, site_url, start_date, end_date, ['query', 'page'])
    
    # 2. Fetch Page-level data (dimensions: page)
    print("Fetching page-level GSC data...")
    df_page = fetch_with_cache(service, site_url, start_date, end_date, ['page'])
    
    if df_page.empty:
        print("Error: No page-level data found. Cannot perform comparison.")
        return None
        
    print(f"Retrieved {len(df_page):,} unique page-level URLs.")
    print(f"Retrieved {len(df_query):,} query-page combination rows.")
    
    # 3. Aggregate datasets
    # Page-level stats
    df_p_grouped = df_page.groupby('page').agg({
        'clicks': 'sum',
        'impressions': 'sum',
        'position': 'mean'
    }).reset_index()
    
    # Query-level stats
    if not df_query.empty:
        df_q_grouped = df_query.groupby('page').agg({
            'clicks': 'sum',
            'impressions': 'sum',
            'position': 'mean'
        }).reset_index().rename(columns={'clicks': 'query_clicks', 'impressions': 'query_impressions', 'position': 'query_position'})
    else:
        df_q_grouped = pd.DataFrame(columns=['page', 'query_clicks', 'query_impressions', 'query_position'])
        
    # Merge datasets
    df_merged = pd.merge(df_p_grouped, df_q_grouped, on='page', how='outer')
    df_merged.fillna(0, inplace=True)
    
    # Convert numerical columns to correct types
    df_merged['clicks'] = df_merged['clicks'].astype(int)
    df_merged['impressions'] = df_merged['impressions'].astype(int)
    df_merged['query_clicks'] = df_merged['query_clicks'].astype(int)
    df_merged['query_impressions'] = df_merged['query_impressions'].astype(int)
    
    # Compute Deltas (Page-level vs Query-level)
    df_merged['clicks_delta'] = df_merged['clicks'] - df_merged['query_clicks']
    df_merged['impressions_delta'] = df_merged['impressions'] - df_merged['query_impressions']
    
    # Classify Dataset Status
    def get_status(row):
        in_p = row['clicks'] > 0 or row['impressions'] > 0
        in_q = row['query_clicks'] > 0 or row['query_impressions'] > 0
        if in_p and not in_q:
            return 'Unique to Page-Level'
        elif in_q and not in_p:
            return 'Unique to Query-Level'
        else:
            return 'Present in Both'
            
    df_merged['dataset_status'] = df_merged.apply(get_status, axis=1)
    
    # Sort by page-level clicks descending
    df_merged = df_merged.sort_values(by='clicks', ascending=False).reset_index(drop=True)
    
    # 4. Generate folder-level aggregation (calculated on full dataset)
    df_merged['folder'] = df_merged['page'].apply(get_first_folder)
    
    df_folders_raw = df_merged.groupby('folder').agg({
        'clicks': 'sum',
        'query_clicks': 'sum',
        'page': 'count'
    }).reset_index().rename(columns={
        'clicks': 'page_clicks',
        'query_clicks': 'query_clicks',
        'page': 'page_count'
    })
    
    # Group directories with only one page under 'Unique page folder'
    df_single = df_folders_raw[df_folders_raw['page_count'] == 1]
    df_multi = df_folders_raw[df_folders_raw['page_count'] > 1]
    
    if not df_single.empty:
        collated_row = pd.DataFrame([{
            'folder': 'Unique page folder',
            'page_clicks': df_single['page_clicks'].sum(),
            'query_clicks': df_single['query_clicks'].sum(),
            'page_count': df_single['page_count'].sum()
        }])
        df_multi_sorted = df_multi.sort_values(by='page_clicks', ascending=False)
        df_folders = pd.concat([df_multi_sorted, collated_row], ignore_index=True)
    else:
        df_folders = df_multi.sort_values(by='page_clicks', ascending=False).reset_index(drop=True)
        
    # Restrict comparison to top 50 pages only
    df_merged = df_merged.head(50)
    
    # 5. High-level comparative statistics
    p_clicks = int(df_p_grouped['clicks'].sum())
    q_clicks = int(df_q_grouped['query_clicks'].sum()) if not df_q_grouped.empty else 0
    clicks_diff = p_clicks - q_clicks
    clicks_diff_pct = clicks_diff / p_clicks if p_clicks > 0 else 0
    
    p_impressions = int(df_p_grouped['impressions'].sum())
    q_impressions = int(df_q_grouped['query_impressions'].sum()) if not df_q_grouped.empty else 0
    impressions_diff = p_impressions - q_impressions
    impressions_diff_pct = impressions_diff / p_impressions if p_impressions > 0 else 0
    
    p_pages = int(df_p_grouped['page'].nunique())
    q_pages = int(df_q_grouped['page'].nunique()) if not df_q_grouped.empty else 0
    pages_diff = p_pages - q_pages
    pages_diff_pct = pages_diff / p_pages if p_pages > 0 else 0
    
    stats = {
        'page_clicks': p_clicks,
        'query_clicks': q_clicks,
        'clicks_diff': clicks_diff,
        'clicks_diff_pct': clicks_diff_pct,
        'page_impressions': p_impressions,
        'query_impressions': q_impressions,
        'impressions_diff': impressions_diff,
        'impressions_diff_pct': impressions_diff_pct,
        'page_pages': p_pages,
        'query_pages': q_pages,
        'pages_diff': pages_diff,
        'pages_diff_pct': pages_diff_pct
    }
    
    # 6. Save files
    output_dir = get_output_dir(site_url)
    os.makedirs(output_dir, exist_ok=True)
    slug = get_filename_slug(site_url)
    
    # File naming matching expected navigation routing
    html_path = os.path.join(output_dir, f"gsc-data-comparison-{slug}-{start_date}-to-{end_date}.html")
    csv_path = os.path.join(output_dir, f"gsc-data-comparison-{slug}-{start_date}-to-{end_date}.csv")
    
    # Write CSV
    df_merged.to_csv(csv_path, index=False, encoding='utf-8')
    
    # Write HTML
    html_content = build_html_report(site_url, start_date, end_date, stats, df_folders, df_merged)
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
        
    print("\n" + "="*60)
    print(f"GSC Data Comparison Report generated successfully.")
    print(f"CSV Report:  {csv_path}")
    print(f"HTML Report: {html_path}")
    print("="*60 + "\n")
    
    return csv_path, html_path

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Run GSC Page-Level vs Query-Level dataset comparison report.')
    parser.add_argument('site_url', nargs='?', default='https://www.hr-inform.co.uk', help='The site URL or GSC property.')
    parser.add_argument('--start-date', help='Start date (YYYY-MM-DD).')
    parser.add_argument('--end-date', help='End date (YYYY-MM-DD).')
    parser.add_argument('--last-7-days', action='store_true', help='Run for the last 7 available days.')
    parser.add_argument('--last-month', action='store_true', help='Run for the last complete calendar month.')
    
    args = parser.parse_args()
    
    service = get_gsc_service()
    if service:
        start_date, end_date = parse_standard_date_args(args, service, args.site_url)
        run_report(service, args.site_url, start_date, end_date)
