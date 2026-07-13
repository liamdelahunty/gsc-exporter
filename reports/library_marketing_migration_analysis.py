"""
Report script to generate the Library to Marketing Migration Analysis.
Queries Google Search Console data for library.croneri.co.uk, maps deep technical reference
articles to proposed marketing URLs on www.croneri.co.uk, and displays an interactive table.
Generates two versions:
1. Standard report (with query-level keywords and expandable drawers).
2. Page-only report (without queries, showing unfiltered page-level traffic data).
"""
import os
import sys
import pandas as pd
import numpy as np
import argparse
import html
import re
import urllib.parse
from datetime import datetime
from urllib.parse import urlparse

# Add parent directory to sys.path to allow importing core
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.naming import get_output_dir, get_filename_slug
from core.cache import fetch_with_cache
from core.client import get_gsc_service
from core.date_utils import parse_standard_date_args

# Specific manual overrides for suggested URLs to align them with search intent (if needed)
URL_OVERRIDES = {}

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
    if not isinstance(url, str):
        return ""
    return url.strip().lower().rstrip('/')

def clean_and_shorten_slug(text):
    if not isinstance(text, str) or not text:
        return ""
    text = text.lower().strip()
    text = re.sub(r'[^a-z0-9\s\-]', '', text)
    words = re.split(r'[\s\-]+', text)
    words = [w for w in words if w and w not in SEO_STOP_WORDS]
    if not words:
        words = [w for w in re.split(r'[\s\-]+', text) if w]
    if len(words) > 1 and words[-1].isdigit() and len(words[-1]) == 1:
        words.pop()
    return "-".join(words)

def clean_keyword_slug(text):
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
    if len(words) > 1 and words[-1].isdigit() and len(words[-1]) == 1:
        words.pop()
    return "-".join(words)

def suggest_marketing_url(library_url, top_query):
    library_url_unquoted = urllib.parse.unquote(library_url)
    if library_url in URL_OVERRIDES:
        return URL_OVERRIDES[library_url], URL_OVERRIDES[library_url]
    if library_url_unquoted in URL_OVERRIDES:
        return URL_OVERRIDES[library_url_unquoted], URL_OVERRIDES[library_url_unquoted]
        
    parsed = urlparse(library_url_unquoted)
    path = parsed.path.strip('/')
    parts = path.split('/')
    last_part = parts[-1] if parts else ""
    
    folder = "tax-audit-accounting"
    found_folder = False
    
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
    return f"https://www.croneri.co.uk/{folder}/{default_slug}", f"https://www.croneri.co.uk/{folder}/{keyword_slug}"

def check_url_disconnect(library_url, top_query):
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
    stop_words = {'the', 'and', 'for', 'with', 'from', 'you', 'your', 'our', 'what', 'how', 'why', 'who', 'when', 'where', 'will', 'this', 'that', 'are', 'was', 'were', 'about'}
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

def get_navbar(slug, start_date, end_date, active_page):
    files = {
        'index': f"library-migration-index-{slug}-{start_date}-to-{end_date}.html",
        'prio_kw': f"library-marketing-migration-prioritisation-report-{slug}-{start_date}-to-{end_date}.html",
        'prio_po': f"library-marketing-migration-prioritisation-page-only-{slug}-{start_date}-to-{end_date}.html",
        'anal_kw': f"library-marketing-migration-analysis-{slug}-{start_date}-to-{end_date}.html",
        'anal_po': f"library-marketing-migration-analysis-page-only-{slug}-{start_date}-to-{end_date}.html",
        'ql_hl_kw': f"library-quick-links-highlighted-report-{slug}-{start_date}-to-{end_date}.html",
        'ql_hl_po': f"library-quick-links-highlighted-page-only-{slug}-{start_date}-to-{end_date}.html",
        'ql_all_kw': f"library-quick-links-all-report-{slug}-{start_date}-to-{end_date}.html",
        'ql_all_po': f"library-quick-links-all-page-only-{slug}-{start_date}-to-{end_date}.html",
    }
    def btn_class(key):
        return "btn btn-primary active" if key == active_page else "btn btn-outline-primary"
    return f"""
    <div class="d-flex flex-wrap gap-2 justify-content-center mb-4 pb-3 border-bottom">
        <a href="{files['index']}" class="{btn_class('index')} px-3">Migration Index</a>
        <div class="btn-group">
            <a href="{files['prio_kw']}" class="{btn_class('prio_kw')}">Prioritisation (Keywords)</a>
            <a href="{files['prio_po']}" class="{btn_class('prio_po')}">Prioritisation (Page-only)</a>
        </div>
        <div class="btn-group">
            <a href="{files['anal_kw']}" class="{btn_class('anal_kw')}">Analysis (Keywords)</a>
            <a href="{files['anal_po']}" class="{btn_class('anal_po')}">Analysis (Page-only)</a>
        </div>
        <div class="btn-group">
            <a href="{files['ql_hl_kw']}" class="{btn_class('ql_hl_kw')}">Quick Links Highlighted (Keywords)</a>
            <a href="{files['ql_hl_po']}" class="{btn_class('ql_hl_po')}">Quick Links Highlighted (Page-only)</a>
        </div>
        <div class="btn-group">
            <a href="{files['ql_all_kw']}" class="{btn_class('ql_all_kw')}">Quick Links All (Keywords)</a>
            <a href="{files['ql_all_po']}" class="{btn_class('ql_all_po')}">Quick Links All (Page-only)</a>
        </div>
    </div>
    """

def run_report(service, site_url, start_date, end_date, limit=100, max_rows=10000, queries_limit=5):
    """Executes standard and page-only versions of the Library to Marketing Migration Analysis Report."""
    print(f"Running Library to Marketing Migration Analysis for {site_url}...")
    slug = get_filename_slug(site_url)
    output_dir = get_output_dir(site_url)
    os.makedirs(output_dir, exist_ok=True)
    
    # -------------------------------------------------------------------------
    # REPORT 1: Standard Keyword-Level Report
    # -------------------------------------------------------------------------
    print("Retrieving GSC keyword-level data...")
    df_raw = fetch_with_cache(service, site_url, start_date, end_date, ['query', 'page'], max_rows=max_rows)
    if df_raw.empty:
        print("Error: No data found.")
        return
        
    df_pages = df_raw.groupby('page').agg(
        clicks=('clicks', 'sum'),
        impressions=('impressions', 'sum'),
        unique_queries=('query', 'nunique')
    ).reset_index()
    
    weighted_pos = df_raw.groupby('page').apply(
        lambda g: (g['position'] * g['impressions']).sum() / g['impressions'].sum() if g['impressions'].sum() > 0 else g['position'].mean()
    ).reset_index(name='position')
    
    df_pages = df_pages.merge(weighted_pos, on='page')
    df_pages['ctr'] = df_pages['clicks'] / df_pages['impressions']
    df_pages = df_pages.sort_values(by='clicks', ascending=False)
    
    df_raw_sorted = df_raw.sort_values(by=['page', 'clicks'], ascending=[True, False])
    
    top_n_pages = df_pages.head(limit).copy()
    stats_kw = {
        'pages': len(top_n_pages),
        'clicks': int(top_n_pages['clicks'].sum()),
        'impressions': int(top_n_pages['impressions'].sum()),
        'ctr': float(top_n_pages['clicks'].sum() / top_n_pages['impressions'].sum()) if top_n_pages['impressions'].sum() > 0 else 0
    }
    
    # Generate standard HTML table rows
    table_rows = []
    for i, row in top_n_pages.reset_index(drop=True).iterrows():
        page_url = row['page']
        clicks = int(row['clicks'])
        impressions = int(row['impressions'])
        ctr = float(row['ctr'])
        position = float(row['position'])
        unique_queries = int(row['unique_queries'])
        
        page_queries = df_raw_sorted[df_raw_sorted['page'] == page_url].head(queries_limit)
        queries_list = page_queries['query'].tolist()
        queries_str_attr = html.escape(", ".join(queries_list))
        
        top_query_val = queries_list[0] if queries_list else ""
        default_url, keyword_url = suggest_marketing_url(page_url, top_query_val)
        has_disconnect, disconnect_reason = check_url_disconnect(page_url, top_query_val)
        
        sub_table_body = ""
        for _, q_row in page_queries.iterrows():
            sub_table_body += f"""
                <tr>
                    <td><code>{html.escape(q_row['query'])}</code></td>
                    <td class="text-end">{int(q_row['clicks']):,}</td>
                    <td class="text-end">{int(q_row['impressions']):,}</td>
                    <td class="text-end">{float(q_row['ctr']):.2%}</td>
                    <td class="text-end">{float(q_row['position']):.2f}</td>
                </tr>
            """
        sub_table_html = f"""
        <table class="table table-sm table-bordered mt-2 mb-0">
            <thead class="table-secondary">
                <tr><th>Search Query</th><th class="text-end" style="width: 120px;">Clicks</th><th class="text-end" style="width: 150px;">Impressions</th><th class="text-end" style="width: 100px;">CTR</th><th class="text-end" style="width: 100px;">Avg. Position</th></tr>
            </thead>
            <tbody>{sub_table_body}</tbody>
        </table>"""
        
        disconnect_warning_html = ""
        disconnect_row_class = ""
        audit_note = ""
        if has_disconnect:
            disconnect_warning_html = '<span class="badge badge-disconnect ms-2">⚠️ SEO Disconnect</span>'
            disconnect_row_class = "table-warning-light"
            audit_note = f'<div class="text-danger mt-2 fw-semibold" style="font-size: 0.85rem;">⚠️ Audit Note: {html.escape(disconnect_reason)}</div>'
            
        collapse_id = f"collapse-page-{i}"
        
        proposed_url_block = f"""
        <div class="text-success" style="font-size: 0.85rem;">
            <strong>Proposed (Default):</strong> <a href="{default_url}" target="_blank" onclick="event.stopPropagation();" class="text-success text-decoration-none">{html.escape(default_url)}</a>
        </div>"""
        if default_url != keyword_url:
            proposed_url_block += f"""
            <div class="text-info mt-1" style="font-size: 0.85rem;">
                <strong>Alternative (Keyword):</strong> <a href="{keyword_url}" target="_blank" onclick="event.stopPropagation();" class="text-info text-decoration-none">{html.escape(keyword_url)}</a>
            </div>"""
            
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
                            <h6 class="mb-0 text-primary fw-bold">Top Queries driving traffic:</h6>
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
    nav_kw_html = get_navbar(slug, start_date, end_date, "anal_kw")
    
    html_content = f"""<!DOCTYPE html>
<html lang="en-GB">
<head>
    <meta charset="UTF-8"><title>Library to Marketing Migration Analysis</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body {{ background-color: #f4f6f9; color: #1f2937; font-family: 'Segoe UI', sans-serif; padding-bottom: 4rem; }}
        .hero-section {{ background: linear-gradient(135deg, #1e3a8a, #0f172a); padding: 3rem 1.5rem; margin-bottom: 2.5rem; border-radius: 0 0 24px 24px; box-shadow: 0 10px 15px -3px rgba(0,0,0,0.1); }}
        .hero-section h1 {{ color: #ffffff !important; }}
        .hero-section p {{ color: rgba(255, 255, 255, 0.7) !important; }}
        h1, h2, h3, h4 {{ font-weight: 700; color: #111827; }}
        .metric-card {{ background-color: #ffffff; border: none; border-radius: 16px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05); }}
        .collapse-row td {{ background-color: #fcfcfc; }}
        .btn-xs {{ padding: 1px 5px; font-size: 0.75rem; }}
        .page-url-cell a {{ color: #2563eb; text-decoration: none; }}
        .table-responsive {{ border-radius: 12px; overflow: hidden; box-shadow: 0 4px 12px rgba(0,0,0,0.05); background-color: #fff; }}
        .badge-disconnect {{ background-color: #fef3c7; color: #d97706; border: 1px solid #fde68a; font-size: 0.75rem; }}
        .table-warning-light {{ background-color: #fffdf5 !important; }}
        code {{ color: #db2777; background-color: #f3f4f6; padding: 0.15rem 0.3rem; border-radius: 4px; font-size: 0.9em; }}
    </style>
</head>
<body>
<div class="hero-section text-center">
    <div class="container-fluid">
        <h1 class="display-5 mb-2">Library to Marketing Migration Analysis</h1>
        <p class="lead text-muted">Property: <strong>{html.escape(site_url)}</strong> | Reporting Period: <strong>{start_date} to {end_date}</strong> (Keyword-Level Data)</p>
    </div>
</div>
<div class="container-fluid px-4">
    {nav_kw_html}
    <div class="row g-4 mb-4">
        <div class="col-md-3"><div class="card metric-card p-4 text-center"><small class="text-muted d-block text-uppercase fw-bold mb-1">Pages Analysed</small><span class="h2 fw-bold text-primary">{stats_kw['pages']}</span></div></div>
        <div class="col-md-3"><div class="card metric-card p-4 text-center"><small class="text-muted d-block text-uppercase fw-bold mb-1">Cumulative Clicks</small><span class="h2 fw-bold text-success">{stats_kw['clicks']:,}</span></div></div>
        <div class="col-md-3"><div class="card metric-card p-4 text-center"><small class="text-muted d-block text-uppercase fw-bold mb-1">Cumulative Impressions</small><span class="h2 fw-bold text-info">{stats_kw['impressions']:,}</span></div></div>
        <div class="col-md-3"><div class="card metric-card p-4 text-center"><small class="text-muted d-block text-uppercase fw-bold mb-1">Average CTR</small><span class="h2 fw-bold text-warning">{stats_kw['ctr']:.2%}</span></div></div>
    </div>
    <div class="d-flex align-items-center justify-content-between mb-3 mt-5">
        <div><h4 class="fw-bold text-dark mb-1">Library Pages Organic Performance &amp; Keyword Map</h4></div>
        <div style="width: 350px;"><input type="text" id="pageSearch" class="form-control" placeholder="Search pages or queries..."></div>
    </div>
    <div class="table-responsive mb-5">
        <table id="libraryPagesTable" class="table table-hover align-middle mb-0">
            <thead class="table-dark">
                <tr>
                    <th class="text-center" style="width: 60px;">Rank</th><th>Library Page URL &amp; Proposed Mapping</th>
                    <th class="text-end" style="width: 120px;">Clicks</th><th class="text-end" style="width: 150px;">Impressions</th>
                    <th class="text-end" style="width: 100px;">CTR</th><th class="text-end" style="width: 120px;">Avg. Position</th>
                    <th class="text-end" style="width: 130px;">Unique Queries</th><th class="text-center" style="width: 120px;">Queries</th>
                </tr>
            </thead>
            <tbody>{table_rows_html}</tbody>
        </table>
    </div>
</div>
<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"></script>
<script>
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
                var collapseId = row.getAttribute('data-collapse-target');
                var collapseEl = document.getElementById(collapseId);
                if (collapseEl && collapseEl.classList.contains('show')) {{
                    collapseEl.classList.remove('show');
                }}
            }}
        }});
    }});
    document.querySelectorAll('#libraryPagesTable tbody .main-row').forEach(function(row) {{
        row.addEventListener('click', function(e) {{
            if (e.target.tagName !== 'A') {{
                var collapseId = row.getAttribute('data-collapse-target');
                var collapseEl = document.getElementById(collapseId);
                var bsCollapse = bootstrap.Collapse.getOrCreateInstance(collapseEl);
                bsCollapse.toggle();
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
</html>"""
    
    html_path = os.path.join(output_dir, f"library-marketing-migration-analysis-{slug}-{start_date}-to-{end_date}.html")
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"Standard HTML Analysis generated at: {html_path}")

    # Save Standard CSV
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
            if i < len(page_queries):
                q_row = page_queries.iloc[i]
                query_val = q_row['query']
                query_clicks = int(q_row['clicks'])
            row_dict[f'top_query_{i+1}'] = query_val
            row_dict[f'top_query_{i+1}_clicks'] = query_clicks
        csv_rows.append(row_dict)
    pd.DataFrame(csv_rows).to_csv(csv_path, index=False, encoding='utf-8')

    # -------------------------------------------------------------------------
    # REPORT 2: Page-Only Report (Unfiltered)
    # -------------------------------------------------------------------------
    print("Retrieving GSC page-only data for unfiltered analysis...")
    df_raw_page = fetch_with_cache(service, site_url, start_date, end_date, ['page'], max_rows=max_rows)
    if df_raw_page.empty:
        print("Warning: No page-only data found.")
        return
        
    df_pages_po = df_raw_page.groupby('page').agg(
        clicks=('clicks', 'sum'),
        impressions=('impressions', 'sum'),
        position=('position', 'mean')
    ).reset_index()
    
    df_pages_po['ctr'] = df_pages_po['clicks'] / df_pages_po['impressions']
    df_pages_po = df_pages_po.sort_values(by='clicks', ascending=False)
    
    top_n_pages_po = df_pages_po.head(limit).copy()
    stats_po = {
        'pages': len(top_n_pages_po),
        'clicks': int(top_n_pages_po['clicks'].sum()),
        'impressions': int(top_n_pages_po['impressions'].sum()),
        'ctr': float(top_n_pages_po['clicks'].sum() / top_n_pages_po['impressions'].sum()) if top_n_pages_po['impressions'].sum() > 0 else 0
    }
    
    table_rows_po = []
    csv_rows_po = []
    
    for i, row in top_n_pages_po.reset_index(drop=True).iterrows():
        page_url = row['page']
        clicks = int(row['clicks'])
        impressions = int(row['impressions'])
        ctr = float(row['ctr'])
        position = float(row['position'])
        
        default_url, _ = suggest_marketing_url(page_url, "")
        
        row_dict_po = {
            'library_page': page_url,
            'clicks': clicks,
            'impressions': impressions,
            'ctr': ctr,
            'position': position,
            'proposed_marketing_url': default_url
        }
        csv_rows_po.append(row_dict_po)
        
        row_html_po = f"""
        <tr class="main-row">
            <td class="text-center fw-bold">{i + 1}</td>
            <td class="page-url-cell">
                <a href="{page_url}" target="_blank" class="text-break fw-semibold">{html.escape(page_url)}</a>
                <div class="text-success mt-2" style="font-size: 0.85rem;">
                    <strong>Proposed:</strong> <a href="{default_url}" target="_blank" class="text-success text-decoration-none">{html.escape(default_url)}</a>
                </div>
            </td>
            <td class="text-end fw-bold">{clicks:,}</td>
            <td class="text-end">{impressions:,}</td>
            <td class="text-end">{ctr:.2%}</td>
            <td class="text-end">{position:.2f}</td>
        </tr>
        """
        table_rows_po.append(row_html_po)
        
    table_rows_po_html = "\n".join(table_rows_po)
    nav_po_html = get_navbar(slug, start_date, end_date, "anal_po")
    
    html_po_content = f"""<!DOCTYPE html>
<html lang="en-GB">
<head>
    <meta charset="UTF-8"><title>Library to Marketing Migration Analysis (Page-Only)</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body {{ background-color: #f4f6f9; color: #1f2937; font-family: 'Segoe UI', sans-serif; padding-bottom: 4rem; }}
        .hero-section {{ background: linear-gradient(135deg, #1e3a8a, #0f172a); padding: 3rem 1.5rem; margin-bottom: 2.5rem; border-radius: 0 0 24px 24px; box-shadow: 0 10px 15px -3px rgba(0,0,0,0.1); }}
        .hero-section h1 {{ color: #ffffff !important; }}
        .hero-section p {{ color: rgba(255, 255, 255, 0.7) !important; }}
        h1, h2, h3, h4 {{ font-weight: 700; color: #111827; }}
        .metric-card {{ background-color: #ffffff; border: none; border-radius: 16px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05); }}
        .page-url-cell a {{ color: #2563eb; text-decoration: none; }}
        .table-responsive {{ border-radius: 12px; overflow: hidden; box-shadow: 0 4px 12px rgba(0,0,0,0.05); background-color: #fff; }}
    </style>
</head>
<body>
<div class="hero-section text-center">
    <div class="container-fluid">
        <h1 class="display-5 mb-2">Library to Marketing Migration Analysis (Page-Only)</h1>
        <p class="lead text-muted">Property: <strong>{html.escape(site_url)}</strong> | Reporting Period: <strong>{start_date} to {end_date}</strong> (Unfiltered Page-Level Data)</p>
    </div>
</div>
<div class="container-fluid px-4">
    {nav_po_html}
    <div class="row g-4 mb-4">
        <div class="col-md-3"><div class="card metric-card p-4 text-center"><small class="text-muted d-block text-uppercase fw-bold mb-1">Pages Analysed</small><span class="h2 fw-bold text-primary">{stats_po['pages']}</span></div></div>
        <div class="col-md-3"><div class="card metric-card p-4 text-center"><small class="text-muted d-block text-uppercase fw-bold mb-1">Cumulative Clicks</small><span class="h2 fw-bold text-success">{stats_po['clicks']:,}</span></div></div>
        <div class="col-md-3"><div class="card metric-card p-4 text-center"><small class="text-muted d-block text-uppercase fw-bold mb-1">Cumulative Impressions</small><span class="h2 fw-bold text-info">{stats_po['impressions']:,}</span></div></div>
        <div class="col-md-3"><div class="card metric-card p-4 text-center"><small class="text-muted d-block text-uppercase fw-bold mb-1">Average CTR</small><span class="h2 fw-bold text-warning">{stats_po['ctr']:.2%}</span></div></div>
    </div>
    <div class="d-flex align-items-center justify-content-between mb-3 mt-5">
        <div><h4 class="fw-bold text-dark mb-1">Library Pages Organic Performance (Unfiltered)</h4></div>
        <div style="width: 350px;"><input type="text" id="pageSearch" class="form-control" placeholder="Search pages..."></div>
    </div>
    <div class="table-responsive mb-5">
        <table id="libraryPagesTable" class="table table-hover align-middle mb-0">
            <thead class="table-dark">
                <tr>
                    <th class="text-center" style="width: 60px;">Rank</th><th>Library Page URL &amp; Proposed Mapping</th>
                    <th class="text-end" style="width: 120px;">Clicks</th><th class="text-end" style="width: 150px;">Impressions</th>
                    <th class="text-end" style="width: 100px;">CTR</th><th class="text-end" style="width: 120px;">Avg. Position</th>
                </tr>
            </thead>
            <tbody>{table_rows_po_html}</tbody>
        </table>
    </div>
</div>
<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"></script>
<script>
    document.getElementById('pageSearch').addEventListener('keyup', function() {{
        var filter = this.value.toLowerCase();
        var rows = document.querySelectorAll('#libraryPagesTable tbody tr');
        rows.forEach(function(row) {{
            var text = row.querySelector('.page-url-cell').textContent.toLowerCase();
            row.style.display = text.indexOf(filter) > -1 ? '' : 'none';
        }});
    }});
</script>
</body>
</html>"""
    
    html_po_path = os.path.join(output_dir, f"library-marketing-migration-analysis-page-only-{slug}-{start_date}-to-{end_date}.html")
    with open(html_po_path, "w", encoding="utf-8") as f:
        f.write(html_po_content)
    print(f"Page-Only HTML Analysis generated successfully at: {html_po_path}")

    csv_po_filename = f"library-marketing-migration-analysis-page-only-{slug}-{start_date}-to-{end_date}.csv"
    csv_po_path = os.path.join(output_dir, csv_po_filename)
    pd.DataFrame(csv_rows_po).to_csv(csv_po_path, index=False, encoding='utf-8')
    print(f"Page-Only CSV saved to: {csv_po_path}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Run Library to Marketing Migration Analysis.')
    parser.add_argument('site_url', nargs='?', default='https://library.croneri.co.uk/', help='The library site URL or GSC property.')
    parser.add_argument('--start-date', help='Start date (YYYY-MM-DD).')
    parser.add_argument('--end-date', help='End date (YYYY-MM-DD).')
    parser.add_argument('--last-month', action='store_true', help='Run for the last calendar month.')
    parser.add_argument('--limit', type=int, default=100, help='Maximum number of pages to display.')
    parser.add_argument('--max-rows', type=int, default=10000, help='Maximum rows to retrieve.')
    
    args = parser.parse_args()
    
    service = get_gsc_service()
    if service:
        start_date, end_date = parse_standard_date_args(args, service, args.site_url)
        run_report(service, args.site_url, start_date, end_date, args.limit, args.max_rows)
