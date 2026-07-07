"""
Report script to analyse GSC performance data for www.hr-inform.co.uk.
Classifies pages into Drupal (Old / Purple) and Dato (New) platforms to assist with content prioritisation, migration, and redirection.
"""
import os
import sys
import pandas as pd
import numpy as np
import argparse
import html
from datetime import datetime, date, timedelta
from urllib.parse import urlparse
from dateutil.relativedelta import relativedelta

# Add parent directory to sys.path to allow importing core
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.naming import get_output_dir, get_filename_slug
from core.cache import fetch_with_cache
from core.client import get_gsc_service
from core.date_utils import parse_standard_date_args

def clean_url(url):
    """Normalises URLs by stripping whitespace, converting to lowercase, and removing trailing slashes."""
    if not isinstance(url, str):
        return ""
    return url.strip().lower().rstrip('/')

def load_dato_urls(slug):
    """
    Loads Dato (new platform) URLs from a configuration file.
    Falls back to a default hardcoded list if the configuration file is not found.
    """
    dato_urls = set()
    # Try slug first (e.g., config/dato-urls-hr-inform-co-uk.txt)
    config_path = os.path.join('config', f"dato-urls-{slug}.txt")
    if not os.path.exists(config_path):
        # Fall back to general config name
        config_path = os.path.join('config', "dato-urls-hr-inform.txt")
        
    if os.path.exists(config_path):
        with open(config_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    dato_urls.add(line)
        print(f"Loaded {len(dato_urls)} Dato URLs from {config_path}")
    else:
        # Fallback to the user's provided list in case the file is missing
        default_list = [
            "https://www.hr-inform.co.uk/",
            "https://www.hr-inform.co.uk/employment-rights-act",
            "https://www.hr-inform.co.uk/employment-rights-act/absences-and-leave-overview",
            "https://www.hr-inform.co.uk/employment-rights-act/bereavement-leave",
            "https://www.hr-inform.co.uk/employment-rights-act/fair-work-agency",
            "https://www.hr-inform.co.uk/employment-rights-act/fire-and-rehire",
            "https://www.hr-inform.co.uk/employment-rights-act/flexible-working",
            "https://www.hr-inform.co.uk/employment-rights-act/large-employers",
            "https://www.hr-inform.co.uk/employment-rights-act/parental-leave",
            "https://www.hr-inform.co.uk/employment-rights-act/parental-vs-paternity-leave-explained",
            "https://www.hr-inform.co.uk/employment-rights-act/paternity-leave",
            "https://www.hr-inform.co.uk/employment-rights-act/probation-periods",
            "https://www.hr-inform.co.uk/employment-rights-act/redundancy-consultation",
            "https://www.hr-inform.co.uk/employment-rights-act/sexual-harassment",
            "https://www.hr-inform.co.uk/employment-rights-act/sick-pay",
            "https://www.hr-inform.co.uk/employment-rights-act/unfair-dismissal",
            "https://www.hr-inform.co.uk/employment-rights-act/union-access",
            "https://www.hr-inform.co.uk/employment-rights-act/zero-hour-contract",
            "https://www.hr-inform.co.uk/features",
            "https://www.hr-inform.co.uk/features/working-during-heatwave",
            "https://www.hr-inform.co.uk/policies",
            "https://www.hr-inform.co.uk/policies/major-sporting-events-template",
            "https://www.hr-inform.co.uk/resources",
            "https://www.hr-inform.co.uk/resources/free-payslip-template"
        ]
        dato_urls.update(default_list)
        print(f"Config file not found. Using default hardcoded list of {len(dato_urls)} Dato URLs.")
        
    return {clean_url(u) for u in dato_urls}

def create_html_report(df_drupal_grouped, df_drupal_detail, start_date, end_date, site_url, stats, limit=100, queries_limit=5):
    """Generates a styled, interactive HTML report with a migration progress dashboard."""
    slug = get_filename_slug(site_url)
    
    # Extract stats
    dato_clicks = stats['dato_clicks']
    dato_impressions = stats['dato_impressions']
    dato_pages = stats['dato_pages']
    dato_ctr = stats['dato_ctr']
    
    drupal_clicks = stats['drupal_clicks']
    drupal_impressions = stats['drupal_impressions']
    drupal_pages = stats['drupal_pages']
    drupal_ctr = stats['drupal_ctr']
    
    total_clicks = stats['total_clicks']
    total_impressions = stats['total_impressions']
    total_pages = stats['total_pages']
    overall_ctr = stats['overall_ctr']
    
    # Progress percentages
    clicks_progress = (dato_clicks / total_clicks * 100) if total_clicks > 0 else 0
    pages_progress = (dato_pages / total_pages * 100) if total_pages > 0 else 0
    
    # Formatted stats
    clicks_prog_str = f"{clicks_progress:.1f}%"
    pages_prog_str = f"{pages_progress:.1f}%"
    
    # Generate HTML rows for the Drupal pages table
    table_rows = []
    
    for i, row in df_drupal_grouped.head(limit).reset_index(drop=True).iterrows():
        page_url = row['page']
        clicks = int(row['clicks'])
        impressions = int(row['impressions'])
        ctr = float(row['ctr'])
        position = float(row['position'])
        unique_queries = int(row['unique_queries'])
        
        # Get top queries for this page
        page_queries = df_drupal_detail[df_drupal_detail['page'] == page_url].head(queries_limit)
        queries_list = page_queries['query'].tolist()
        queries_str_attr = html.escape(", ".join(queries_list))
        
        # Build nested sub-table for top queries
        sub_table_header = """
        <table class="table table-sm table-bordered mt-2 mb-0">
            <thead class="table-secondary">
                <tr>
                    <th>Search Query</th>
                    <th class="text-end" style="width: 120px;">Clicks</th>
                    <th class="text-end" style="width: 150px;">Impressions</th>
                    <th class="text-end" style="width: 100px;">CTR</th>
                    <th class="text-end" style="width: 100px;">Avg. Position</th>
                </tr>
            </thead>
            <tbody>
        """
        sub_table_body = ""
        for _, q_row in page_queries.iterrows():
            q_ctr = float(q_row['ctr'])
            q_pos = float(q_row['position'])
            sub_table_body += f"""
                <tr>
                    <td><code>{html.escape(q_row['query'])}</code></td>
                    <td class="text-end">{int(q_row['clicks']):,}</td>
                    <td class="text-end">{int(q_row['impressions']):,}</td>
                    <td class="text-end">{q_ctr:.2%}</td>
                    <td class="text-end">{q_pos:.2f}</td>
                </tr>
            """
        sub_table_footer = "</tbody></table>"
        sub_table_html = sub_table_header + sub_table_body + sub_table_footer
        
        collapse_id = f"collapse-page-{i}"
        
        row_html = f"""
        <tr class="main-row" data-bs-toggle="collapse" data-bs-target="#{collapse_id}" style="cursor: pointer;" data-queries="{queries_str_attr}" data-collapse-target="{collapse_id}">
            <td class="text-center fw-bold">{i + 1}</td>
            <td class="page-url-cell"><a href="{page_url}" target="_blank" onclick="event.stopPropagation();" class="text-break">{html.escape(page_url)}</a></td>
            <td class="text-end fw-bold">{clicks:,}</td>
            <td class="text-end">{impressions:,}</td>
            <td class="text-end">{ctr:.2%}</td>
            <td class="text-end">{position:.2f}</td>
            <td class="text-end">{unique_queries:,}</td>
            <td class="text-center">
                <button class="btn btn-xs btn-outline-primary py-0 px-2" style="font-size: 0.75rem;">Show Queries</button>
            </td>
        </tr>
        <tr class="collapse-row">
            <td colspan="8" class="p-0 border-0">
                <div id="{collapse_id}" class="collapse">
                    <div class="p-3 bg-light border-start border-primary border-4">
                        <div class="d-flex align-items-center mb-2">
                            <h6 class="mb-0 text-primary fw-bold">Top Queries driving traffic to this page:</h6>
                            <span class="text-muted ms-3" style="font-size: 0.85rem;">Showing top {len(page_queries)} of {unique_queries} total queries</span>
                        </div>
                        {sub_table_html}
                    </div>
                </div>
            </td>
        </tr>
        """
        table_rows.append(row_html)
        
    table_rows_html = "\n".join(table_rows)
    
    # Build complete HTML report page
    html_content = f"""<!DOCTYPE html>
<html lang="en-GB">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Drupal to Dato Migration Analysis: {site_url}</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body {{
            background-color: #f8f9fa;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            color: #333;
        }}
        .navbar-brand-custom {{
            font-weight: 700;
            color: #1a73e8 !important;
        }}
        .metric-card {{
            border: none;
            border-radius: 12px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.05);
            transition: transform 0.2s;
        }}
        .metric-card:hover {{
            transform: translateY(-2px);
        }}
        .progress-bar-custom {{
            height: 10px;
            border-radius: 5px;
            background-color: #e9ecef;
            overflow: hidden;
        }}
        .progress-fill-dato {{
            background: linear-gradient(90deg, #1a73e8, #34a853);
            height: 100%;
        }}
        .collapse-row td {{
            background-color: #fcfcfc;
        }}
        .btn-xs {{
            padding: 1px 5px;
            font-size: 0.75rem;
            line-height: 1.5;
            border-radius: 3px;
        }}
        .page-url-cell a {{
            color: #1a73e8;
            text-decoration: none;
        }}
        .page-url-cell a:hover {{
            text-decoration: underline;
        }}
        .table-responsive {{
            border-radius: 12px;
            overflow: hidden;
            box-shadow: 0 4px 12px rgba(0,0,0,0.05);
            background-color: #fff;
        }}
    </style>
</head>
<body>

<div class="container-fluid py-4">
    <!-- Header -->
    <div class="d-flex align-items-center justify-content-between border-bottom pb-3 mb-4">
        <div>
            <h1 class="h3 mb-1 fw-bold text-dark">Drupal to Dato Migration Analysis</h1>
            <p class="text-muted mb-0">Property: <strong>{html.escape(site_url)}</strong> | Reporting Period: <strong>{start_date} to {end_date}</strong></p>
        </div>
        <div class="text-end">
            <span class="badge bg-secondary p-2">Report generated on {datetime.now().strftime("%Y-%m-%d")}</span>
        </div>
    </div>

    <!-- Navigation Menu -->
    <div class="d-flex flex-wrap gap-2 justify-content-center mb-4 pb-3 border-bottom">
        <a href="dato-drupal-index-{slug}-{start_date}-to-{end_date}.html" class="btn btn-outline-primary px-4">Migration Index</a>
        <a href="drupal-dato-migration-analysis-{slug}-{start_date}-to-{end_date}.html" class="btn btn-primary active px-4">Breakdown Dashboard (Query-Level)</a>
        <a href="drupal-dato-migration-prioritisation-report-{slug}-{start_date}-to-{end_date}.html" class="btn btn-outline-primary px-4">Top 50 Prioritisation Report</a>
        <a href="drupal-dato-migration-page-level-report-{slug}-{start_date}-to-{end_date}.html" class="btn btn-outline-primary px-4">Page-Level Report (All Clicks)</a>
        <a href="dato-suggested-urls-alphabetical-{slug}-{start_date}-to-{end_date}.html" class="btn btn-outline-primary px-4">Proposed Dato URLs (Alphabetical)</a>
        <a href="gsc-data-comparison-{slug}-{start_date}-to-{end_date}.html" class="btn btn-outline-primary px-4">GSC Data Comparison</a>
    </div>

    <!-- Platform Breakdown Dashboard -->
    <h4 class="fw-bold mb-3 text-secondary">Platform Breakdown Summary</h4>
    <div class="row g-4 mb-4">
        <!-- Progress Bars Card -->
        <div class="col-xl-4 col-md-12">
            <div class="card h-100 metric-card p-4">
                <h5 class="card-title fw-bold text-muted mb-4">Platform Distribution</h5>
                
                <div class="mb-3">
                    <div class="d-flex justify-content-between mb-1">
                        <span class="fw-semibold">Dato Clicks (New Content)</span>
                        <span class="fw-bold text-success">{clicks_prog_str}</span>
                    </div>
                    <div class="progress-bar-custom">
                        <div class="progress-fill-dato" style="width: {clicks_progress}%;"></div>
                    </div>
                    <small class="text-muted">{dato_clicks:,} / {total_clicks:,} total clicks</small>
                </div>
                
                <div>
                    <div class="d-flex justify-content-between mb-1">
                        <span class="fw-semibold">Dato Pages (New Content)</span>
                        <span class="fw-bold text-success">{pages_prog_str}</span>
                    </div>
                    <div class="progress-bar-custom">
                        <div class="progress-fill-dato" style="width: {pages_progress}%;"></div>
                    </div>
                    <small class="text-muted">{dato_pages:,} / {total_pages:,} total organic landing pages</small>
                </div>
            </div>
        </div>

        <!-- Drupal Card -->
        <div class="col-xl-4 col-md-6">
            <div class="card h-100 metric-card p-4 border-start border-danger border-4">
                <h5 class="card-title fw-bold text-danger mb-3">Drupal (Old Platform / "Purple")</h5>
                <div class="row">
                    <div class="col-6 mb-3">
                        <small class="text-muted d-block">Organic Clicks</small>
                        <span class="h3 fw-bold text-dark">{drupal_clicks:,}</span>
                    </div>
                    <div class="col-6 mb-3">
                        <small class="text-muted d-block">Impressions</small>
                        <span class="h3 fw-bold text-dark">{drupal_impressions:,}</span>
                    </div>
                    <div class="col-6">
                        <small class="text-muted d-block">Average CTR</small>
                        <span class="h4 fw-bold text-dark">{drupal_ctr:.2%}</span>
                    </div>
                    <div class="col-6">
                        <small class="text-muted d-block">Remaining Pages</small>
                        <span class="h4 fw-bold text-dark">{drupal_pages:,}</span>
                    </div>
                </div>
            </div>
        </div>

        <!-- Dato Card -->
        <div class="col-xl-4 col-md-6">
            <div class="card h-100 metric-card p-4 border-start border-success border-4">
                <h5 class="card-title fw-bold text-success mb-3">DatoCMS (New Platform)</h5>
                <div class="row">
                    <div class="col-6 mb-3">
                        <small class="text-muted d-block">Organic Clicks</small>
                        <span class="h3 fw-bold text-dark">{dato_clicks:,}</span>
                    </div>
                    <div class="col-6 mb-3">
                        <small class="text-muted d-block">Impressions</small>
                        <span class="h3 fw-bold text-dark">{dato_impressions:,}</span>
                    </div>
                    <div class="col-6">
                        <small class="text-muted d-block">Average CTR</small>
                        <span class="h4 fw-bold text-dark">{dato_ctr:.2%}</span>
                    </div>
                    <div class="col-6">
                        <small class="text-muted d-block">Active Pages</small>
                        <span class="h4 fw-bold text-dark">{dato_pages:,}</span>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <!-- Prioritised Pages List -->
    <div class="d-flex align-items-center justify-content-between mb-3 mt-5">
        <div>
            <h4 class="fw-bold text-dark mb-1">Prioritised Drupal Pages to Migrate &amp; Redirect</h4>
            <p class="text-muted mb-0">Sorted by organic clicks. Click any row to view the top search queries driving traffic to that page.</p>
        </div>
        <div style="width: 350px;">
            <input type="text" id="pageSearch" class="form-control" placeholder="Search pages or search queries...">
        </div>
    </div>

    <div class="table-responsive mb-5">
        <table id="drupalPagesTable" class="table table-hover align-middle mb-0">
            <thead class="table-dark">
                <tr>
                    <th class="text-center" style="width: 60px;">Rank</th>
                    <th>Drupal Page URL (Old Structure)</th>
                    <th class="text-end" style="width: 120px;">Clicks</th>
                    <th class="text-end" style="width: 150px;">Impressions</th>
                    <th class="text-end" style="width: 100px;">CTR</th>
                    <th class="text-end" style="width: 120px;">Avg. Position</th>
                    <th class="text-end" style="width: 130px;">Unique Queries</th>
                    <th class="text-center" style="width: 120px;">Queries</th>
                </tr>
            </thead>
            <tbody>
                {table_rows_html}
            </tbody>
        </table>
    </div>

</div>

<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"></script>
<script>
    // Search function that filters rows based on page URL or their search queries
    document.getElementById('pageSearch').addEventListener('keyup', function() {{
        var filter = this.value.toLowerCase();
        var rows = document.querySelectorAll('#drupalPagesTable tbody .main-row');
        
        rows.forEach(function(row) {{
            var pageText = row.querySelector('.page-url-cell').textContent.toLowerCase();
            var queriesText = row.getAttribute('data-queries') || '';
            
            if (pageText.indexOf(filter) > -1 || queriesText.toLowerCase().indexOf(filter) > -1) {{
                row.style.display = '';
            }} else {{
                row.style.display = 'none';
                
                // Hide corresponding collapsed detail row if open
                var collapseId = row.getAttribute('data-collapse-target');
                var collapseEl = document.getElementById(collapseId);
                if (collapseEl && collapseEl.classList.contains('show')) {{
                    var bsCollapse = bootstrap.Collapse.getInstance(collapseEl);
                    if (bsCollapse) {{
                        bsCollapse.hide();
                    }} else {{
                        collapseEl.classList.remove('show');
                    }}
                }}
            }}
        }});
    }});

    // Make the entire row clickable to toggle collapse except when clicking the actual link
    document.querySelectorAll('#drupalPagesTable tbody .main-row').forEach(function(row) {{
        row.addEventListener('click', function(e) {{
            if (e.target.tagName !== 'A') {{
                var collapseId = row.getAttribute('data-collapse-target');
                var collapseEl = document.getElementById(collapseId);
                var bsCollapse = bootstrap.Collapse.getOrCreateInstance(collapseEl);
                bsCollapse.toggle();
                
                // Toggle button text
                var button = row.querySelector('button');
                if (button) {{
                    setTimeout(function() {{
                        if (collapseEl.classList.contains('show')) {{
                            button.textContent = 'Hide Queries';
                            button.classList.replace('btn-outline-primary', 'btn-primary');
                        }} else {{
                            button.textContent = 'Show Queries';
                            button.classList.replace('btn-primary', 'btn-outline-primary');
                        }}
                    }}, 350);
                }}
            }}
        }});
    }});
</script>

</body>
</html>
"""
    return html_content

def run_report(service, site_url, start_date, end_date, limit=100, queries_limit=5):
    """Executes the Drupal to Dato migration analysis report."""
    print(f"Running Drupal to Dato migration analysis for {site_url}...")
    print(f"Period: {start_date} to {end_date}")
    
    # 1. Load Dato URLs configuration
    slug = get_filename_slug(site_url)
    dato_clean_urls = load_dato_urls(slug)
    
    # 2. Fetch data (dimensions: query, page)
    df = fetch_with_cache(service, site_url, start_date, end_date, ['query', 'page'])
    if df.empty:
        print("Error: No data found in the cache or API for this period.")
        return None
        
    print(f"Retrieved {len(df):,} granular page-query rows.")
    
    # 3. Classify pages into platforms
    df['is_dato'] = df['page'].apply(lambda u: clean_url(u) in dato_clean_urls)
    
    # Separate dataframes
    df_dato = df[df['is_dato']]
    df_drupal = df[~df['is_dato']]
    
    # Calculate stats
    total_clicks = int(df['clicks'].sum())
    total_impressions = int(df['impressions'].sum())
    total_pages = int(df['page'].nunique())
    overall_ctr = total_clicks / total_impressions if total_impressions > 0 else 0
    
    dato_clicks = int(df_dato['clicks'].sum())
    dato_impressions = int(df_dato['impressions'].sum())
    dato_pages = int(df_dato['page'].nunique())
    dato_ctr = dato_clicks / dato_impressions if dato_impressions > 0 else 0
    
    drupal_clicks = int(df_drupal['clicks'].sum())
    drupal_impressions = int(df_drupal['impressions'].sum())
    drupal_pages = int(df_drupal['page'].nunique())
    drupal_ctr = drupal_clicks / drupal_impressions if drupal_impressions > 0 else 0
    
    stats = {
        'total_clicks': total_clicks,
        'total_impressions': total_impressions,
        'total_pages': total_pages,
        'overall_ctr': overall_ctr,
        'dato_clicks': dato_clicks,
        'dato_impressions': dato_impressions,
        'dato_pages': dato_pages,
        'dato_ctr': dato_ctr,
        'drupal_clicks': drupal_clicks,
        'drupal_impressions': drupal_impressions,
        'drupal_pages': drupal_pages,
        'drupal_ctr': drupal_ctr
    }
    
    print("\n--- Platform Performance Overview ---")
    print(f"Drupal (Old): Clicks: {drupal_clicks:,} | Impressions: {drupal_impressions:,} | Pages: {drupal_pages:,} | CTR: {drupal_ctr:.2%}")
    print(f"Dato (New):   Clicks: {dato_clicks:,} | Impressions: {dato_impressions:,} | Pages: {dato_pages:,} | CTR: {dato_ctr:.2%}")
    print(f"Total Site:   Clicks: {total_clicks:,} | Impressions: {total_impressions:,} | Pages: {total_pages:,} | CTR: {overall_ctr:.2%}")
    if total_clicks > 0:
        print(f"Dato share of Clicks: {dato_clicks / total_clicks:.2%}")
    if total_pages > 0:
        print(f"Dato share of Pages:  {dato_pages / total_pages:.2%}")
        
    # 4. Group Drupal pages by performance
    # Average position is weighted by impressions for accuracy
    # Unique queries count is unique query values per page
    df_drupal_grouped = df_drupal.groupby('page').apply(
        lambda group: pd.Series({
            'clicks': group['clicks'].sum(),
            'impressions': group['impressions'].sum(),
            'position': (group['position'] * group['impressions']).sum() / group['impressions'].sum() if group['impressions'].sum() > 0 else group['position'].mean(),
            'unique_queries': group['query'].nunique()
        })
    ).reset_index()
    
    df_drupal_grouped['ctr'] = df_drupal_grouped['clicks'] / df_drupal_grouped['impressions']
    df_drupal_grouped = df_drupal_grouped.sort_values(by='clicks', ascending=False)
    
    # 5. Get top queries list per page sorted by clicks
    df_drupal_sorted = df_drupal.sort_values(by=['page', 'clicks'], ascending=[True, False])
    
    # 6. Save CSV
    output_dir = get_output_dir(site_url)
    os.makedirs(output_dir, exist_ok=True)
    file_prefix = f"drupal-dato-migration-analysis-{slug}-{start_date}-to-{end_date}"
    csv_path = os.path.join(output_dir, f"{file_prefix}.csv")
    html_path = os.path.join(output_dir, f"{file_prefix}.html")
    
    # Construct rows for the prioritised CSV export
    csv_rows = []
    for _, row in df_drupal_grouped.iterrows():
        page_url = row['page']
        page_queries = df_drupal_sorted[df_drupal_sorted['page'] == page_url].head(5)
        
        row_dict = {
            'page': page_url,
            'clicks': int(row['clicks']),
            'impressions': int(row['impressions']),
            'ctr': float(row['ctr']),
            'position': float(row['position']),
            'unique_queries': int(row['unique_queries'])
        }
        
        # Add top 5 queries columns
        for i in range(5):
            query_val = ""
            query_clicks = ""
            query_impressions = ""
            query_ctr = ""
            query_position = ""
            if i < len(page_queries):
                q_row = page_queries.iloc[i]
                query_val = q_row['query']
                query_clicks = int(q_row['clicks'])
                query_impressions = int(q_row['impressions'])
                query_ctr = float(q_row['ctr'])
                query_position = float(q_row['position'])
                
            row_dict[f'top_query_{i+1}'] = query_val
            row_dict[f'top_query_{i+1}_clicks'] = query_clicks
            row_dict[f'top_query_{i+1}_impressions'] = query_impressions
            row_dict[f'top_query_{i+1}_ctr'] = query_ctr
            row_dict[f'top_query_{i+1}_position'] = query_position
            
        csv_rows.append(row_dict)
        
    df_csv = pd.DataFrame(csv_rows)
    df_csv.to_csv(csv_path, index=False, encoding='utf-8')
    
    # 7. Generate and save HTML
    html_content = create_html_report(
        df_drupal_grouped,
        df_drupal_sorted,
        start_date,
        end_date,
        site_url,
        stats,
        limit=limit,
        queries_limit=queries_limit
    )
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
        
    print(f"\nCSV saved to: {csv_path}")
    print(f"HTML saved to: {html_path}")
    
    return csv_path, html_path

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Run Drupal to Dato migration analysis.')
    parser.add_argument('site_url', nargs='?', default='sc-domain:hr-inform.co.uk', help='The site URL or property.')
    parser.add_argument('--start-date', help='Start date (YYYY-MM-DD).')
    parser.add_argument('--end-date', help='End date (YYYY-MM-DD).')
    parser.add_argument('--last-7-days', action='store_true', help='Run for the last 7 available days.')
    parser.add_argument('--last-month', action='store_true', help='Run for the last calendar month.')
    parser.add_argument('--limit', type=int, default=100, help='Maximum number of Drupal pages to display in HTML.')
    parser.add_argument('--queries-limit', type=int, default=5, help='Number of top search queries to display per page.')
    
    args = parser.parse_args()
    
    service = get_gsc_service()
    if service:
        start_date, end_date = parse_standard_date_args(args, service, args.site_url)
        # Default date range logic has run, now run the analysis
        run_report(service, args.site_url, start_date, end_date, args.limit, args.queries_limit)
