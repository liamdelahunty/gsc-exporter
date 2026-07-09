"""
Report script to generate the Library to Marketing Migration Analysis.
Queries Google Search Console data for library.croneri.co.uk, maps deep technical reference
articles to proposed marketing URLs on www.croneri.co.uk, and displays an interactive table
showing top keywords driving traffic to each URL.
"""
import os
import sys
import pandas as pd
import numpy as np
import argparse
import html
import re
import urllib.parse
from datetime import datetime, date, timedelta
from urllib.parse import urlparse

# Add parent directory to sys.path to allow importing core
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.naming import get_output_dir, get_filename_slug
from core.cache import fetch_with_cache
from core.client import get_gsc_service
from core.date_utils import parse_standard_date_args

# Specific manual overrides for suggested URLs to align them with search intent (if needed)
URL_OVERRIDES = {
    # Example: "https://library.croneri.co.uk/cch_uk/some-page": "https://www.croneri.co.uk/some-override"
}

SEO_STOP_WORDS = {
    'a', 'an', 'the', 'and', 'or', 'but', 'so', 'if', 'of', 'in', 'on', 'at', 'by', 
    'to', 'for', 'with', 'from', 'about', 'between', 'against', 'during', 'without', 
    'before', 'after', 'over', 'under', 'through', 'into', 'is', 'are', 'was', 'were', 
    'be', 'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'whats', 'what', 
    'how', 'why', 'who', 'led', 'than', 'then', 'else', 'when', 'where', 'those', 'these', 
    'that', 'this', 'url', 'page', 'site', 'website'
}

BRAND_WORDS = {'croneri', 'croner', 'co', 'uk', 'library'}

def clean_url(url):
    """Normalises URLs by stripping whitespace, converting to lowercase, and removing trailing slashes."""
    if not isinstance(url, str):
        return ""
    return url.strip().lower().rstrip('/')

def clean_and_shorten_slug(text):
    """Cleans a URL slug by stripping punctuation and stop words, and formatting with hyphens."""
    if not isinstance(text, str) or not text:
        return ""
    text = text.lower().strip()
    text = re.sub(r'[^a-z0-9\s\-]', '', text)
    words = re.split(r'[\s\-]+', text)
    words = [w for w in words if w and w not in SEO_STOP_WORDS]
    if not words:
        words = [w for w in re.split(r'[\s\-]+', text) if w]
    # Remove standalone copy/version numbers from the end of the slug
    if len(words) > 1 and words[-1].isdigit() and len(words[-1]) == 1:
        words.pop()
    return "-".join(words)

def clean_keyword_slug(text):
    """Cleans a GSC query keyword to form a URL slug."""
    if not isinstance(text, str) or not text:
        return ""
    text = text.lower().strip()
    text = re.sub(r'[^a-z0-9\s\-]', '', text)
    words = re.split(r'[\s\-]+', text)
    words = [w for w in words if w and w not in SEO_STOP_WORDS and w not in BRAND_WORDS]
    if not words:
        words = [w for w in re.split(r'[\s\-]+', text) if w and w not in SEO_STOP_WORDS]
    if not words:
        words = [w for w in re.split(r'[\s\-]+', text) if w]
    # Remove standalone copy/version numbers from the end of the slug
    if len(words) > 1 and words[-1].isdigit() and len(words[-1]) == 1:
        words.pop()
    return "-".join(words)

def suggest_marketing_url(library_url, top_query):
    """Suggests a proposed target marketing URL on www.croneri.co.uk based on path structure and queries."""
    library_url_unquoted = urllib.parse.unquote(library_url)
    
    if library_url in URL_OVERRIDES:
        return URL_OVERRIDES[library_url], URL_OVERRIDES[library_url]
    if library_url_unquoted in URL_OVERRIDES:
        return URL_OVERRIDES[library_url_unquoted], URL_OVERRIDES[library_url_unquoted]
        
    parsed = urlparse(library_url_unquoted)
    path = parsed.path.strip('/')
    
    parts = path.split('/')
    last_part = parts[-1] if parts else ""
    
    # Categorise folder based on URL path parts
    folder = "tax-audit-accounting"  # default marketing folder
    found_folder = False
    
    # Category indicators
    tax_indicators = {'pctm', 'btr', 'mot', 'etc', 'it', 'vat', 'dt', 'ct', 'cgt', 'sdlt', 'nics', 'tax', 'income-tax', 'capital-gains'}
    accounting_indicators = {'nuk102', 'nuk1a', 'frs', 'msr', 'acc', 'audit', 'ias', 'ifrs', 'accounting', 'model-accounts'}
    hs_indicators = {'hsc', 'h&s', 'hs', 'safety', 'fire', 'environment', 'health-and-safety', 'workplace'}
    hr_indicators = {'hr', 'emp', 'employment', 'personnel', 'payroll', 'dismissal', 'human-resources', 'redundancy'}
    care_indicators = {'care', 'clinic', 'nursing', 'compliance'}
    
    for part in parts:
        part_clean = part.lower()
        if any(ind in part_clean for ind in tax_indicators):
            folder = "tax-audit-accounting"
            found_folder = True
            break
        if any(ind in part_clean for ind in accounting_indicators):
            folder = "tax-audit-accounting"
            found_folder = True
            break
        if any(ind in part_clean for ind in hs_indicators):
            folder = "health-and-safety"
            found_folder = True
            break
        if any(ind in part_clean for ind in hr_indicators):
            folder = "human-resources"
            found_folder = True
            break
        if any(ind in part_clean for ind in care_indicators):
            folder = "compliance"
            found_folder = True
            break

    # If folder is not identified from path, check the top query
    if not found_folder and isinstance(top_query, str) and top_query:
        query_lower = top_query.lower()
        if any(ind in query_lower for ind in tax_indicators):
            folder = "tax-audit-accounting"
        elif any(ind in query_lower for ind in accounting_indicators):
            folder = "tax-audit-accounting"
        elif any(ind in query_lower for ind in hs_indicators):
            folder = "health-and-safety"
        elif any(ind in query_lower for ind in hr_indicators):
            folder = "human-resources"
        elif any(ind in query_lower for ind in care_indicators):
            folder = "compliance"

    # Determine slugs
    if not last_part or last_part == 'library.croneri.co.uk':
        if isinstance(top_query, str) and pd.notna(top_query) and top_query:
            default_slug = clean_and_shorten_slug(top_query)
            keyword_slug = clean_keyword_slug(top_query)
        else:
            default_slug = "home"
            keyword_slug = "home"
    else:
        if '.' in last_part:
            last_part = last_part.rsplit('.', 1)[0]
        default_slug = clean_and_shorten_slug(last_part)
        if not default_slug:
            default_slug = "page"
            
        if isinstance(top_query, str) and pd.notna(top_query) and top_query:
            keyword_slug = clean_keyword_slug(top_query)
        else:
            keyword_slug = default_slug
            
    if not keyword_slug:
        keyword_slug = default_slug
        
    default_url = f"https://www.croneri.co.uk/{folder}/{default_slug}"
    keyword_url = f"https://www.croneri.co.uk/{folder}/{keyword_slug}"
    
    return default_url, keyword_url

def check_url_disconnect(library_url, top_query):
    """Checks if there is a semantic disconnect between the library URL slug and GSC query keywords."""
    library_url_unquoted = urllib.parse.unquote(library_url)
    
    if library_url in URL_OVERRIDES or library_url_unquoted in URL_OVERRIDES:
        return False, ""
        
    parsed = urlparse(library_url_unquoted)
    path = parsed.path.strip('/')
    
    if not path or path == 'library.croneri.co.uk':
        return False, ""
        
    path_clean = path.replace('/', ' ').replace('-', ' ').replace('_', ' ').lower()
    path_words = set(re.findall(r'\b[a-z0-9]{3,}\b', path_clean))
    
    if not isinstance(top_query, str) or pd.isna(top_query) or not top_query:
        return False, ""
    query_clean = str(top_query).lower()
    query_words = set(re.findall(r'\b[a-z0-9]{3,}\b', query_clean))
    
    stop_words = {'the', 'and', 'for', 'with', 'from', 'you', 'your', 'our', 'what', 'how', 'why', 'who', 'when', 'where', 'will', 'this', 'that', 'are', 'was', 'were', 'about', 'difference', 'between'}
    path_words = path_words - stop_words
    query_words = query_words - stop_words
    
    if not query_words or not path_words:
        return False, ""
        
    path_stems = {w[:4] for w in path_words}
    query_stems = {w[:4] for w in query_words}
    
    overlap = path_stems.intersection(query_stems)
    if not overlap:
        return True, f"Library URL slug targets content related to '{path.split('/')[-1]}', but GSC queries are driven by '{top_query}'."
        
    return False, ""

def create_html_report(df_grouped, df_detail, start_date, end_date, site_url, stats, limit=100, queries_limit=5):
    """Generates a styled, interactive HTML report with expandable query tables for each page URL."""
    slug = get_filename_slug(site_url)
    
    # Generate HTML rows for the library pages table
    table_rows = []
    
    for i, row in df_grouped.head(limit).reset_index(drop=True).iterrows():
        page_url = row['page']
        clicks = int(row['clicks'])
        impressions = int(row['impressions'])
        ctr = float(row['ctr'])
        position = float(row['position'])
        unique_queries = int(row['unique_queries'])
        
        # Get top queries for this page
        page_queries = df_detail[df_detail['page'] == page_url].head(queries_limit)
        queries_list = page_queries['query'].tolist()
        queries_str_attr = html.escape(", ".join(queries_list))
        
        top_query_val = queries_list[0] if queries_list else ""
        default_url, keyword_url = suggest_marketing_url(page_url, top_query_val)
        has_disconnect, disconnect_reason = check_url_disconnect(page_url, top_query_val)
        
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
        
        # Handle disconnect styling and note
        disconnect_warning_html = ""
        disconnect_row_class = ""
        if has_disconnect:
            disconnect_warning_html = '<span class="badge badge-disconnect ms-2">⚠️ SEO Disconnect</span>'
            disconnect_row_class = "table-warning-light"
            audit_note = f'<div class="text-danger mt-2 fw-semibold" style="font-size: 0.85rem;">⚠️ Audit Note: {html.escape(disconnect_reason)}</div>'
        else:
            audit_note = ""
            
        collapse_id = f"collapse-page-{i}"
        
        # Combine default and keyword URLs if they differ
        proposed_url_block = f"""
        <div class="text-success" style="font-size: 0.85rem;">
            <strong>Proposed (Default):</strong> <a href="{default_url}" target="_blank" onclick="event.stopPropagation();" class="text-success text-decoration-none">{html.escape(default_url)}</a>
        </div>
        """
        if default_url != keyword_url:
            proposed_url_block += f"""
            <div class="text-info mt-1" style="font-size: 0.85rem;">
                <strong>Alternative (Keyword):</strong> <a href="{keyword_url}" target="_blank" onclick="event.stopPropagation();" class="text-info text-decoration-none">{html.escape(keyword_url)}</a>
            </div>
            """
        
        row_html = f"""
        <tr class="main-row {disconnect_row_class}" data-bs-toggle="collapse" data-bs-target="#{collapse_id}" style="cursor: pointer;" data-queries="{queries_str_attr}" data-collapse-target="{collapse_id}">
            <td class="text-center fw-bold">{i + 1}</td>
            <td class="page-url-cell">
                <a href="{page_url}" target="_blank" onclick="event.stopPropagation();" class="text-break fw-semibold">{html.escape(page_url)}</a>{disconnect_warning_html}
                <div class="mt-2">{proposed_url_block}</div>
            </td>
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
                        {audit_note}
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
    <title>Library to Marketing Migration Analysis: {site_url}</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body {{
            background-color: #f4f6f9;
            color: #1f2937;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            padding-bottom: 4rem;
        }}
        .hero-section {{
            background: linear-gradient(135deg, #1e3a8a, #0f172a);
            padding: 3rem 1.5rem;
            margin-bottom: 2.5rem;
            border-radius: 0 0 24px 24px;
            box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
        }}
        .hero-section h1 {{
            color: #ffffff !important;
        }}
        .hero-section p {{
            color: rgba(255, 255, 255, 0.7) !important;
        }}
        h1, h2, h3, h4 {{
            font-weight: 700;
            color: #111827;
        }}
        .metric-card {{
            background-color: #ffffff;
            border: none;
            border-radius: 16px;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03);
            transition: transform 0.2s, box-shadow 0.2s;
        }}
        .metric-card:hover {{
            transform: translateY(-2px);
            box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.05), 0 4px 6px -2px rgba(0, 0, 0, 0.05);
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
            color: #2563eb;
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
        .badge-disconnect {{
            background-color: #fef3c7;
            color: #d97706;
            border: 1px solid #fde68a;
            font-size: 0.75rem;
        }}
        .table-warning-light {{
            background-color: #fffdf5 !important;
        }}
        code {{
            color: #db2777;
            background-color: #f3f4f6;
            padding: 0.15rem 0.3rem;
            border-radius: 4px;
            font-size: 0.9em;
        }}
    </style>
</head>
<body>

<div class="hero-section text-center">
    <div class="container-fluid">
        <h1 class="display-5 mb-2">Library to Marketing Migration Analysis</h1>
        <p class="lead text-muted">Property: <strong>{html.escape(site_url)}</strong> | Reporting Period: <strong>{start_date} to {end_date}</strong></p>
        <span class="badge bg-primary p-2">Report generated on {datetime.now().strftime("%Y-%m-%d")}</span>
    </div>
</div>

<div class="container-fluid px-4">
    <!-- Performance Summary Cards -->
    <h4 class="fw-bold mb-3 text-secondary">Migration Overview Summary</h4>
    <div class="row g-4 mb-4">
        <!-- Analysed Pages -->
        <div class="col-md-3">
            <div class="card metric-card p-4 text-center">
                <small class="text-muted d-block text-uppercase fw-bold mb-1">Top Pages Analysed</small>
                <span class="h2 fw-bold text-primary">{stats['pages']:,}</span>
            </div>
        </div>
        <!-- Clicks Card -->
        <div class="col-md-3">
            <div class="card metric-card p-4 text-center">
                <small class="text-muted d-block text-uppercase fw-bold mb-1">Cumulative Clicks</small>
                <span class="h2 fw-bold text-success">{stats['clicks']:,}</span>
            </div>
        </div>
        <!-- Impressions Card -->
        <div class="col-md-3">
            <div class="card metric-card p-4 text-center">
                <small class="text-muted d-block text-uppercase fw-bold mb-1">Cumulative Impressions</small>
                <span class="h2 fw-bold text-info">{stats['impressions']:,}</span>
            </div>
        </div>
        <!-- CTR Card -->
        <div class="col-md-3">
            <div class="card metric-card p-4 text-center">
                <small class="text-muted d-block text-uppercase fw-bold mb-1">Average CTR</small>
                <span class="h2 fw-bold text-warning">{stats['ctr']:.2%}</span>
            </div>
        </div>
    </div>

    <!-- Explanatory Note -->
    <div class="card metric-card mb-4 p-4 border-start border-primary border-4">
        <h4 class="fw-bold mb-2">💡 Migration Intent</h4>
        <p class="text-secondary mb-0">
            We want to see the best performing pages on the deep research portal <code>library.croneri.co.uk</code>, and propose
            marketing versions on the core business site <code>www.croneri.co.uk</code>. By reviewing the top performing reference
            content, we can capture high-intent search traffic and redirect it to dedicated lead-generation landing pages.
            Click any row in the table below to inspect the top queries driving organic search traffic.
        </p>
    </div>

    <!-- Interactive Pages List -->
    <div class="d-flex align-items-center justify-content-between mb-3 mt-5">
        <div>
            <h4 class="fw-bold text-dark mb-1">Library Pages Organic Performance &amp; Keyword Map</h4>
            <p class="text-muted mb-0">Sorted by organic clicks. Click any row to view the top search queries driving traffic to that page.</p>
        </div>
        <div style="width: 350px;">
            <input type="text" id="pageSearch" class="form-control" placeholder="Search pages or search queries...">
        </div>
    </div>

    <div class="table-responsive mb-5">
        <table id="libraryPagesTable" class="table table-hover align-middle mb-0">
            <thead class="table-dark">
                <tr>
                    <th class="text-center" style="width: 60px;">Rank</th>
                    <th>Library Page URL &amp; Proposed Mapping</th>
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
        var rows = document.querySelectorAll('#libraryPagesTable tbody .main-row');
        
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
    document.querySelectorAll('#libraryPagesTable tbody .main-row').forEach(function(row) {{
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

def run_report(service, site_url, start_date, end_date, limit=100, max_rows=10000, queries_limit=5):
    """Executes the Library to Marketing Migration Analysis Report."""
    print(f"Running Library to Marketing Migration Analysis for {site_url}...")
    print(f"Retrieving GSC data (limit: {max_rows} rows)...")
    
    slug = get_filename_slug(site_url)
    output_dir = get_output_dir(site_url)
    os.makedirs(output_dir, exist_ok=True)
    
    # Fetch query and page dimensions
    df_raw = fetch_with_cache(service, site_url, start_date, end_date, ['query', 'page'], max_rows=max_rows)
    if df_raw.empty:
        print("Error: No data found in GSC API or cache for this period.")
        return None
        
    print(f"Retrieved {len(df_raw):,} query-page rows from GSC.")
    
    # Aggregate data by page
    df_pages = df_raw.groupby('page').agg(
        clicks=('clicks', 'sum'),
        impressions=('impressions', 'sum'),
        unique_queries=('query', 'nunique')
    ).reset_index()
    
    # Calculate position (weighted by impressions)
    weighted_pos = df_raw.groupby('page').apply(
        lambda g: (g['position'] * g['impressions']).sum() / g['impressions'].sum() if g['impressions'].sum() > 0 else g['position'].mean()
    ).reset_index(name='position')
    
    df_pages = df_pages.merge(weighted_pos, on='page')
    df_pages['ctr'] = df_pages['clicks'] / df_pages['impressions']
    df_pages = df_pages.sort_values(by='clicks', ascending=False)
    
    # Sort raw details to extract top queries per page
    df_raw_sorted = df_raw.sort_values(by=['page', 'clicks'], ascending=[True, False])
    
    top_n_pages = df_pages.head(limit).copy()
    
    # Stats for the top group
    total_group_clicks = int(top_n_pages['clicks'].sum())
    total_group_imps = int(top_n_pages['impressions'].sum())
    group_ctr = total_group_clicks / total_group_imps if total_group_imps > 0 else 0
    
    stats = {
        'pages': len(top_n_pages),
        'clicks': total_group_clicks,
        'impressions': total_group_imps,
        'ctr': group_ctr
    }
    
    # Save CSV
    csv_filename = f"library-marketing-migration-analysis-{slug}-{start_date}-to-{end_date}.csv"
    csv_path = os.path.join(output_dir, csv_filename)
    
    csv_rows = []
    for _, row in df_pages.iterrows():
        page_url = row['page']
        page_queries = df_raw_sorted[df_raw_sorted['page'] == page_url].head(5)
        top_query_val = page_queries.iloc[0]['query'] if not page_queries.empty else ""
        
        default_url, keyword_url = suggest_marketing_url(page_url, top_query_val)
        has_disconnect, disconnect_reason = check_url_disconnect(page_url, top_query_val)
        
        row_dict = {
            'library_page': page_url,
            'clicks': int(row['clicks']),
            'impressions': int(row['impressions']),
            'ctr': float(row['ctr']),
            'position': float(row['position']),
            'unique_queries': int(row['unique_queries']),
            'proposed_marketing_url_default': default_url,
            'proposed_marketing_url_keyword': keyword_url,
            'is_disconnect': has_disconnect,
            'disconnect_reason': disconnect_reason
        }
        
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
    print(f"CSV saved to: {csv_path}")
    
    # Generate HTML
    html_filename = f"library-marketing-migration-analysis-{slug}-{start_date}-to-{end_date}.html"
    html_path = os.path.join(output_dir, html_filename)
    
    html_content = create_html_report(
        df_grouped=top_n_pages,
        df_detail=df_raw_sorted,
        start_date=start_date,
        end_date=end_date,
        site_url=site_url,
        stats=stats,
        limit=limit,
        queries_limit=queries_limit
    )
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_content)
        
    print(f"HTML report saved to: {html_path}")
    print(f"Exported files are located at:\n  CSV:  [CSV File](file://{csv_path})\n  HTML: [HTML Report](file://{html_path})")
    
    return csv_path, html_path

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Run Library to Marketing Migration Analysis.')
    parser.add_argument('site_url', nargs='?', default='https://library.croneri.co.uk/', help='The library site URL or GSC property.')
    parser.add_argument('--start-date', help='Start date (YYYY-MM-DD).')
    parser.add_argument('--end-date', help='End date (YYYY-MM-DD).')
    parser.add_argument('--last-7-days', action='store_true', help='Run for the last 7 available days.')
    parser.add_argument('--last-month', action='store_true', help='Run for the last calendar month.')
    parser.add_argument('--limit', type=int, default=100, help='Maximum number of pages to display in HTML.')
    parser.add_argument('--max-rows', type=int, default=10000, help='Maximum number of raw page-query GSC rows to retrieve.')
    parser.add_argument('--queries-limit', type=int, default=5, help='Number of top search queries to display per page.')
    
    args = parser.parse_args()
    
    service = get_gsc_service()
    if service:
        start_date, end_date = parse_standard_date_args(args, service, args.site_url)
        run_report(service, args.site_url, start_date, end_date, args.limit, args.max_rows, args.queries_limit)
