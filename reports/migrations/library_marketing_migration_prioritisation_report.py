"""
Report script to generate the Library to Marketing Migration Prioritisation Report.
Queries Google Search Console data for library.croneri.co.uk, maps deep technical reference
articles to proposed marketing URLs on www.croneri.co.uk, and checks for semantic search disconnects.
Generates two versions:
1. Standard report (with queries, keyword-level data).
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

def get_navbar(slug, start_date, end_date, active_page):
    """Shared navigation menu across all library migration reports."""
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

def run_report(service, site_url, start_date, end_date, limit=100, max_rows=10000):
    """Executes standard and page-only versions of the Library to Marketing Prioritisation Report."""
    print(f"Running Library to Marketing Migration Prioritisation Reports for {site_url}...")
    
    slug = get_filename_slug(site_url)
    output_dir = get_output_dir(site_url)
    os.makedirs(output_dir, exist_ok=True)
    
    # -------------------------------------------------------------------------
    # REPORT 1: Standard Keyword-Level Report (includes search query context)
    # -------------------------------------------------------------------------
    print("Retrieving GSC keyword-level data...")
    df_raw = fetch_with_cache(service, site_url, start_date, end_date, ['query', 'page'], max_rows=max_rows)
    if df_raw.empty:
        print("Error: No keyword-level data found.")
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
    
    csv_rows = []
    list_items = []
    disconnect_items = []
    
    top_n_pages = df_pages.head(limit).copy()
    total_group_clicks = int(top_n_pages['clicks'].sum())
    total_group_imps = int(top_n_pages['impressions'].sum())
    group_ctr = total_group_clicks / total_group_imps if total_group_imps > 0 else 0
    
    for idx, row in top_n_pages.reset_index(drop=True).iterrows():
        page_url = row['page']
        clicks = int(row['clicks'])
        impressions = int(row['impressions'])
        ctr = float(row['ctr'])
        position = float(row['position'])
        unique_queries = int(row['unique_queries'])
        
        # Get top queries
        page_queries = df_raw_sorted[df_raw_sorted['page'] == page_url].head(5)
        top_query_val = page_queries.iloc[0]['query'] if not page_queries.empty else ""
        
        default_url, keyword_url = suggest_marketing_url(page_url, top_query_val)
        has_disconnect, disconnect_reason = check_url_disconnect(page_url, top_query_val)
        
        row_dict = {
            'library_page': page_url,
            'clicks': clicks,
            'impressions': impressions,
            'ctr': ctr,
            'position': position,
            'unique_queries': unique_queries,
            'proposed_marketing_url_default': default_url,
            'proposed_marketing_url_keyword': keyword_url,
            'is_disconnect': has_disconnect,
            'disconnect_reason': disconnect_reason
        }
        
        top_queries_display = []
        for i in range(5):
            q_val = ""
            q_clicks = 0
            if i < len(page_queries):
                q_row = page_queries.iloc[i]
                q_val = q_row['query']
                q_clicks = int(q_row['clicks'])
                if i < 3:
                    top_queries_display.append(f"<code>{html.escape(str(q_val))}</code> ({q_clicks:,} clicks)")
            row_dict[f'top_query_{i+1}'] = q_val
            row_dict[f'top_query_{i+1}_clicks'] = q_clicks
            
        csv_rows.append(row_dict)
        
        badge_html = ""
        warning_class = ""
        note_html = ""
        if has_disconnect:
            badge_html = ' <span class="badge bg-warning text-dark ms-2" style="font-size: 0.75rem;">⚠️ SEO Disconnect</span>'
            warning_class = "border-start border-warning border-3"
            note_html = f'<div class="text-danger mt-1" style="font-size: 0.82rem;"><strong>Audit Note:</strong> {disconnect_reason}</div>'
            disconnect_items.append((page_url, top_query_val, disconnect_reason))
            
        queries_str = ", ".join(top_queries_display)
        
        alternative_html = ""
        if default_url != keyword_url:
            alternative_html = f"""
                        <div class="text-info mt-1" style="font-size: 0.85rem;">
                            <strong>Alternative proposed URL (Keyword-Aligned):</strong> <a href="{keyword_url}" target="_blank" class="text-info text-decoration-none">{keyword_url}</a>
                        </div>
            """
            
        item_html = f"""
        <li class="list-group-item py-3 {warning_class}">
            <div class="d-flex justify-content-between align-items-start">
                <div class="ms-2 me-auto w-70">
                    <div class="fw-bold mb-1"><span class="badge bg-dark me-2">{idx + 1}</span><a href="{page_url}" target="_blank" class="text-break">{html.escape(page_url)}</a>{badge_html}</div>
                    <div class="text-primary mb-1" style="font-size: 0.88rem;">
                        <strong>Top Keywords:</strong> {queries_str}
                    </div>
                    <div class="text-success mb-0" style="font-size: 0.85rem;">
                        <strong>Proposed Marketing URL (Default):</strong> <a href="{default_url}" target="_blank" class="text-success text-decoration-none">{default_url}</a>
                    </div>
                    {alternative_html}
                    {note_html}
                </div>
                <div class="text-end border-start ps-3" style="min-width: 180px;">
                    <div class="fw-bold text-dark">{clicks:,} <span class="text-muted fw-normal" style="font-size: 0.8rem;">clicks</span></div>
                    <div class="text-muted" style="font-size: 0.85rem;">{impressions:,} <span class="fw-normal" style="font-size: 0.8rem;">imps</span></div>
                    <div class="text-muted" style="font-size: 0.85rem;">{ctr:.2%} <span class="fw-normal" style="font-size: 0.8rem;">CTR</span></div>
                    <div class="text-muted" style="font-size: 0.85rem;">{position:.2f} <span class="fw-normal" style="font-size: 0.8rem;">position</span></div>
                </div>
            </div>
        </li>
        """
        list_items.append(item_html)
        
    df_csv = pd.DataFrame(csv_rows)
    csv_filename = f"library-marketing-migration-prioritisation-report-{slug}-{start_date}-to-{end_date}.csv"
    csv_path = os.path.join(output_dir, csv_filename)
    df_csv.to_csv(csv_path, index=False, encoding='utf-8')
    
    audit_card_html = ""
    if disconnect_items:
        audit_rows = []
        for d_page, d_query, d_reason in disconnect_items:
            row_html = f"""
                <div class="py-2 border-bottom">
                    <strong>Library Page:</strong> <a href="{d_page}" target="_blank" class="text-break">{html.escape(d_page)}</a><br>
                    <strong>Top Query:</strong> <code>{html.escape(str(d_query))}</code><br>
                    <span class="text-danger">⚠️ {html.escape(d_reason)}</span>
                </div>
            """
            audit_rows.append(row_html)
            
        audit_card_html = f"""
        <div class="card border-warning border-3 mb-4 p-4" style="background-color: #fffdf5; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.02);">
            <h4 class="fw-bold text-warning mb-2">⚠️ SEO Disconnects Audit (Action Required)</h4>
            <p class="text-muted">During our check, we identified library pages where the search intent (the queries driving organic traffic) is disconnected from the library URL path slug.</p>
            <div class="mt-2" style="font-size: 0.9rem; max-height: 400px; overflow-y: auto;">
                {"".join(audit_rows)}
            </div>
        </div>
        """
        
    list_items_html = "\n".join(list_items)
    nav_html = get_navbar(slug, start_date, end_date, "prio_kw")
    
    html_content = f"""<!DOCTYPE html>
<html lang="en-GB">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Library to Marketing Migration Prioritisation Report</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body {{ background-color: #f4f6f9; color: #1f2937; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; padding-bottom: 4rem; }}
        .hero-section {{ background: linear-gradient(135deg, #1e3a8a, #0f172a); padding: 3rem 1.5rem; margin-bottom: 2rem; border-radius: 0 0 24px 24px; box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1); }}
        .hero-section h1 {{ color: #ffffff !important; }}
        .hero-section p {{ color: rgba(255, 255, 255, 0.7) !important; }}
        h1, h2, h3, h4 {{ font-weight: 700; color: #111827; }}
        .metric-card {{ background-color: #ffffff; border: none; border-radius: 16px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05); transition: transform 0.2s; }}
        .metric-card:hover {{ transform: translateY(-2px); }}
        .list-group-item {{ background-color: #ffffff; border-color: #e5e7eb; color: #374151; }}
        .text-muted {{ color: #6b7280 !important; }}
        .text-secondary {{ color: #4b5563 !important; }}
        .w-70 {{ width: 70%; }}
        a {{ color: #2563eb; text-decoration: none; }}
        a:hover {{ color: #1d4ed8; text-decoration: underline; }}
        code {{ color: #db2777; background-color: #f3f4f6; padding: 0.15rem 0.3rem; border-radius: 4px; font-size: 0.9em; }}
    </style>
</head>
<body>

<div class="hero-section text-center">
    <div class="container-fluid">
        <h1 class="display-5 mb-2">Library to Marketing Migration Prioritisation Report</h1>
        <p class="lead text-muted">Property: <strong>{html.escape(site_url)}</strong> | Reporting Period: <strong>{start_date} to {end_date}</strong> (Keyword-Level Data)</p>
    </div>
</div>

<div class="container-fluid px-4">
    {nav_html}

    <div class="row g-4 mb-4">
        <div class="col-md-3">
            <div class="card metric-card p-4 text-center">
                <small class="text-muted d-block uppercase fw-bold mb-1">Top Pages Analysed</small>
                <span class="h2 fw-bold text-primary">{len(top_n_pages)}</span>
            </div>
        </div>
        <div class="col-md-3">
            <div class="card metric-card p-4 text-center">
                <small class="text-muted d-block fw-bold mb-1">Cumulative Clicks</small>
                <span class="h2 fw-bold text-success">{total_group_clicks:,}</span>
            </div>
        </div>
        <div class="col-md-3">
            <div class="card metric-card p-4 text-center">
                <small class="text-muted d-block fw-bold mb-1">Cumulative Impressions</small>
                <span class="h2 fw-bold text-info">{total_group_imps:,}</span>
            </div>
        </div>
        <div class="col-md-3">
            <div class="card metric-card p-4 text-center">
                <small class="text-muted d-block fw-bold mb-1">Average CTR</small>
                <span class="h2 fw-bold text-warning">{group_ctr:.2%}</span>
            </div>
        </div>
    </div>

    <div class="card metric-card mb-4 p-4 border-start border-primary border-4">
        <h4 class="fw-bold mb-2">💡 Migration Intent (Keywords Mode)</h4>
        <p class="text-secondary mb-0">
            This report prioritises pages based on GSC keyword data. Note that GSC applies privacy filters to low-volume searches, causing the sums above to be lower than true page-level totals.
        </p>
    </div>

    {audit_card_html}

    <h2 class="fw-bold text-dark mb-3">Top Performing Library Pages to Migrate</h2>
    <ul class="list-group">
        {list_items_html}
    </ul>

    <h2 class="fw-bold text-dark mt-5 mb-3">Next Steps &amp; Exports</h2>
    <ul>
        <li><strong>Actionable CSV Export:</strong> <a href="file://{csv_path}">{csv_filename}</a></li>
    </ul>
</div>
<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>"""
    
    html_high_path = os.path.join(output_dir, f"library-marketing-migration-prioritisation-report-{slug}-{start_date}-to-{end_date}.html")
    with open(html_high_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"Standard HTML Report generated at: {html_high_path}")

    # -------------------------------------------------------------------------
    # REPORT 2: Page-Only Report (Unfiltered Clicks & Impressions)
    # -------------------------------------------------------------------------
    print("Retrieving GSC page-only data for unfiltered impressions & clicks...")
    df_raw_page = fetch_with_cache(service, site_url, start_date, end_date, ['page'], max_rows=max_rows)
    if df_raw_page.empty:
        print("Warning: No page-only data found.")
        return
        
    df_pages_only = df_raw_page.groupby('page').agg(
        clicks=('clicks', 'sum'),
        impressions=('impressions', 'sum'),
        position=('position', 'mean')
    ).reset_index()
    
    df_pages_only['ctr'] = df_pages_only['clicks'] / df_pages_only['impressions']
    df_pages_only = df_pages_only.sort_values(by='clicks', ascending=False)
    
    csv_rows_po = []
    list_items_po = []
    top_n_pages_po = df_pages_only.head(limit).copy()
    
    total_clicks_po = int(top_n_pages_po['clicks'].sum())
    total_imps_po = int(top_n_pages_po['impressions'].sum())
    group_ctr_po = total_clicks_po / total_imps_po if total_imps_po > 0 else 0
    
    for idx, row in top_n_pages_po.reset_index(drop=True).iterrows():
        page_url = row['page']
        clicks = int(row['clicks'])
        impressions = int(row['impressions'])
        ctr = float(row['ctr'])
        position = float(row['position'])
        
        # Suggest URLs (without top query context)
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
        
        item_html_po = f"""
        <li class="list-group-item py-3">
            <div class="d-flex justify-content-between align-items-start">
                <div class="ms-2 me-auto w-70">
                    <div class="fw-bold mb-1"><span class="badge bg-dark me-2">{idx + 1}</span><a href="{page_url}" target="_blank" class="text-break">{html.escape(page_url)}</a></div>
                    <div class="text-success mb-0" style="font-size: 0.85rem;">
                        <strong>Proposed Marketing URL:</strong> <a href="{default_url}" target="_blank" class="text-success text-decoration-none">{default_url}</a>
                    </div>
                </div>
                <div class="text-end border-start ps-3" style="min-width: 180px;">
                    <div class="fw-bold text-dark">{clicks:,} <span class="text-muted fw-normal" style="font-size: 0.8rem;">clicks</span></div>
                    <div class="text-muted" style="font-size: 0.85rem;">{impressions:,} <span class="fw-normal" style="font-size: 0.8rem;">imps</span></div>
                    <div class="text-muted" style="font-size: 0.85rem;">{ctr:.2%} <span class="fw-normal" style="font-size: 0.8rem;">CTR</span></div>
                    <div class="text-muted" style="font-size: 0.85rem;">{position:.2f} <span class="fw-normal" style="font-size: 0.8rem;">position</span></div>
                </div>
            </div>
        </li>
        """
        list_items_po.append(item_html_po)
        
    df_csv_po = pd.DataFrame(csv_rows_po)
    csv_po_filename = f"library-marketing-migration-prioritisation-page-only-{slug}-{start_date}-to-{end_date}.csv"
    csv_po_path = os.path.join(output_dir, csv_po_filename)
    df_csv_po.to_csv(csv_po_path, index=False, encoding='utf-8')
    
    list_items_po_html = "\n".join(list_items_po)
    nav_po_html = get_navbar(slug, start_date, end_date, "prio_po")
    
    html_po_content = f"""<!DOCTYPE html>
<html lang="en-GB">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Library to Marketing Migration Prioritisation (Page-Only)</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body {{ background-color: #f4f6f9; color: #1f2937; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; padding-bottom: 4rem; }}
        .hero-section {{ background: linear-gradient(135deg, #1e3a8a, #0f172a); padding: 3rem 1.5rem; margin-bottom: 2rem; border-radius: 0 0 24px 24px; box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1); }}
        .hero-section h1 {{ color: #ffffff !important; }}
        .hero-section p {{ color: rgba(255, 255, 255, 0.7) !important; }}
        h1, h2, h3, h4 {{ font-weight: 700; color: #111827; }}
        .metric-card {{ background-color: #ffffff; border: none; border-radius: 16px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05); transition: transform 0.2s; }}
        .metric-card:hover {{ transform: translateY(-2px); }}
        .list-group-item {{ background-color: #ffffff; border-color: #e5e7eb; color: #374151; }}
        .text-muted {{ color: #6b7280 !important; }}
        .text-secondary {{ color: #4b5563 !important; }}
        .w-70 {{ width: 70%; }}
        a {{ color: #2563eb; text-decoration: none; }}
        a:hover {{ color: #1d4ed8; text-decoration: underline; }}
    </style>
</head>
<body>

<div class="hero-section text-center">
    <div class="container-fluid">
        <h1 class="display-5 mb-2">Library to Marketing Migration Prioritisation Report (Page-Only)</h1>
        <p class="lead text-muted">Property: <strong>{html.escape(site_url)}</strong> | Reporting Period: <strong>{start_date} to {end_date}</strong> (Unfiltered Page-Level Data)</p>
    </div>
</div>

<div class="container-fluid px-4">
    {nav_po_html}

    <div class="row g-4 mb-4">
        <div class="col-md-3">
            <div class="card metric-card p-4 text-center">
                <small class="text-muted d-block uppercase fw-bold mb-1">Top Pages Analysed</small>
                <span class="h2 fw-bold text-primary">{len(top_n_pages_po)}</span>
            </div>
        </div>
        <div class="col-md-3">
            <div class="card metric-card p-4 text-center">
                <small class="text-muted d-block fw-bold mb-1">Cumulative Clicks</small>
                <span class="h2 fw-bold text-success">{total_clicks_po:,}</span>
            </div>
        </div>
        <div class="col-md-3">
            <div class="card metric-card p-4 text-center">
                <small class="text-muted d-block fw-bold mb-1">Cumulative Impressions</small>
                <span class="h2 fw-bold text-info">{total_imps_po:,}</span>
            </div>
        </div>
        <div class="col-md-3">
            <div class="card metric-card p-4 text-center">
                <small class="text-muted d-block fw-bold mb-1">Average CTR</small>
                <span class="h2 fw-bold text-warning">{group_ctr_po:.2%}</span>
            </div>
        </div>
    </div>

    <div class="card metric-card mb-4 p-4 border-start border-primary border-4">
        <h4 class="fw-bold mb-2">💡 Unfiltered Page-Level Traffic</h4>
        <p class="text-secondary mb-0">
            This report represents the true, unfiltered clicks and impressions for library URLs, without GSC keyword privacy threshold exclusions.
        </p>
    </div>

    <h2 class="fw-bold text-dark mb-3">Top Performing Library Pages to Migrate</h2>
    <ul class="list-group">
        {list_items_po_html}
    </ul>

    <h2 class="fw-bold text-dark mt-5 mb-3">Next Steps &amp; Exports</h2>
    <ul>
        <li><strong>Actionable CSV Export:</strong> <a href="file://{csv_po_path}">{csv_po_filename}</a></li>
    </ul>
</div>
<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>"""
    
    html_po_path = os.path.join(output_dir, f"library-marketing-migration-prioritisation-page-only-{slug}-{start_date}-to-{end_date}.html")
    with open(html_po_path, "w", encoding="utf-8") as f:
        f.write(html_po_content)
    print(f"Page-Only HTML Report generated successfully at: {html_po_path}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Run Library to Marketing Prioritisation Reports.')
    parser.add_argument('site_url', nargs='?', default='https://library.croneri.co.uk/', help='The library site URL or GSC property.')
    parser.add_argument('--start-date', help='Start date (YYYY-MM-DD).')
    parser.add_argument('--end-date', help='End date (YYYY-MM-DD).')
    parser.add_argument('--last-7-days', action='store_true', help='Run for the last 7 available days.')
    parser.add_argument('--last-month', action='store_true', help='Run for the last calendar month.')
    parser.add_argument('--limit', type=int, default=100, help='Maximum number of pages to display in HTML.')
    parser.add_argument('--max-rows', type=int, default=10000, help='Maximum number of raw page-query GSC rows to retrieve.')
    
    args = parser.parse_args()
    
    service = get_gsc_service()
    if service:
        start_date, end_date = parse_standard_date_args(args, service, args.site_url)
        run_report(service, args.site_url, start_date, end_date, args.limit, args.max_rows)
