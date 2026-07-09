"""
Report script to generate the Top 50 Prioritisation Report for Drupal to Dato migration.
Reads query-level GSC data, audits for SEO semantic disconnects, and suggests clean target URLs.
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

# Specific manual overrides for suggested URLs to align them with search intent (fixing disconnects)
URL_OVERRIDES = {
    "https://www.hr-inform.co.uk/comment-and-analysis/legislative-changes": {
        "url": "https://www.hr-inform.co.uk/features/webinars",
        "reason": "Search queries focus exclusively on 'webinars' rather than 'legislative changes'. Mapped to /features/webinars.",
        "is_disconnect": True
    },
    "https://www.hr-inform.co.uk/templates-and-tools/medical-checks": {
        "url": "https://www.hr-inform.co.uk/resources/employee-health-questionnaire-template",
        "reason": "Top query is 'employee health questionnaire template'. Mapped to a more specific template URL: /resources/employee-health-questionnaire-template.",
        "is_disconnect": True
    },
    "https://www.hr-inform.co.uk/news-article/action-on-gender-diversity-led-to-resignation-of-bbc-dj": {
        "url": "https://www.hr-inform.co.uk/features/simon-mayo-illness",
        "reason": "This news article ranks exclusively for 'simon mayo illness'. Mapped to /features/simon-mayo-illness.",
        "is_disconnect": True
    },
    "https://www.hr-inform.co.uk/templates-and-tools/probationary-periods": {
        "url": "https://www.hr-inform.co.uk/resources/probation-review-template",
        "reason": "Top query looks specifically for 'probation review template'. Mapped to /resources/probation-review-template.",
        "is_disconnect": True
    },
    "https://www.hr-inform.co.uk/case-law?field_category_target_id=15": {
        "url": "https://www.hr-inform.co.uk/guides/unfair-dismissal-cases",
        "reason": "Top queries focus on 'unfair dismissal cases' rather than generic case law. Mapped to /guides/unfair-dismissal-cases.",
        "is_disconnect": True
    },
    "https://www.hr-inform.co.uk/employment_law/employment-law-in-canada": {
        "url": "https://www.hr-inform.co.uk/guides/canadian-labour-laws",
        "reason": "Top queries look specifically for 'canadian labour laws'. Mapped to /guides/canadian-labour-laws.",
        "is_disconnect": True
    },
    "https://www.hr-inform.co.uk/system/files/downloads/2017-09/Template%20payslips.docx": {
        "url": "https://www.hr-inform.co.uk/resources/free-payslip-template",
        "reason": "Direct payslips file download link redirected to the new resources landing page.",
        "is_disconnect": False
    }
}

SEO_STOP_WORDS = {
    'a', 'an', 'the', 'and', 'or', 'but', 'so', 'if', 'of', 'in', 'on', 'at', 'by', 
    'to', 'for', 'with', 'from', 'about', 'between', 'against', 'during', 'without', 
    'before', 'after', 'over', 'under', 'through', 'into', 'is', 'are', 'was', 'were', 
    'be', 'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'whats', 'what', 
    'how', 'why', 'who', 'led', 'than', 'then', 'else', 'when', 'where', 'those', 'these', 
    'that', 'this', 'url', 'page', 'site', 'website'
}

BRAND_WORDS = {'cipd', 'hr-inform', 'hr', 'inform', 'co', 'uk'}

def load_dato_urls(slug):
    """Loads Dato (new platform) URLs from a configuration file."""
    dato_urls = set()
    config_path = os.path.join('config', f"dato-urls-{slug}.txt")
    if not os.path.exists(config_path):
        config_path = os.path.join('config', "dato-urls-hr-inform.txt")
        
    if os.path.exists(config_path):
        with open(config_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    dato_urls.add(line)
    return dato_urls

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
    # Remove standalone copy/version numbers like '2', '3' from the end of the slug
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
    # Remove standalone copy/version numbers like '2', '3' from the end of the slug
    if len(words) > 1 and words[-1].isdigit() and len(words[-1]) == 1:
        words.pop()
    return "-".join(words)

def suggest_dato_url(drupal_url, top_query):
    """Suggests a default and a keyword-aligned target URL for a legacy Drupal URL."""
    # Decode URL-encoded characters (like %20 -> space) first
    drupal_url_unquoted = urllib.parse.unquote(drupal_url)
    
    if drupal_url in URL_OVERRIDES:
        return URL_OVERRIDES[drupal_url]["url"], URL_OVERRIDES[drupal_url]["url"]
    if drupal_url_unquoted in URL_OVERRIDES:
        return URL_OVERRIDES[drupal_url_unquoted]["url"], URL_OVERRIDES[drupal_url_unquoted]["url"]
        
    parsed = urlparse(drupal_url_unquoted)
    path = parsed.path.strip('/')
    
    parts = path.split('/')
    last_part = parts[-1] if parts else ""
    
    is_node = len(parts) >= 2 and parts[0] == 'node'
    if is_node or not last_part:
        if isinstance(top_query, str) and pd.notna(top_query) and top_query:
            default_slug = clean_and_shorten_slug(top_query)
            keyword_slug = clean_keyword_slug(top_query)
        else:
            default_slug = f"page-{parts[-1]}" if parts else "home"
            keyword_slug = default_slug
    else:
        if '.' in last_part:
            last_part = last_part.rsplit('.', 1)[0]
        default_slug = clean_and_shorten_slug(last_part)
        if not default_slug:
            default_slug = f"page-{parts[-1]}" if parts else "home"
            
        if isinstance(top_query, str) and pd.notna(top_query) and top_query:
            keyword_slug = clean_keyword_slug(top_query)
        else:
            keyword_slug = default_slug
            
    if not keyword_slug:
        keyword_slug = default_slug

    is_template = any(k in path.lower() or k in default_slug.lower() for k in ['template', 'download', 'file', 'form', 'docx', 'pdf', 'checklist', 'model'])
    is_news = 'news-article' in path.lower() or 'comment' in path.lower()
    is_law = 'employment_law' in path.lower() or 'legislation' in path.lower()
    
    if is_template:
        folder = "resources"
        if 'template' not in default_slug:
            default_slug = f"{default_slug}-template"
        if 'template' not in keyword_slug:
            keyword_slug = f"{keyword_slug}-template"
    elif is_news:
        folder = "features"
    elif is_law:
        folder = "guides"
    else:
        folder = "features"
        
    default_url = f"https://www.hr-inform.co.uk/{folder}/{default_slug}"
    keyword_url = f"https://www.hr-inform.co.uk/{folder}/{keyword_slug}"
    
    return default_url, keyword_url

def check_url_disconnect(drupal_url, top_query):
    """Checks if there is a semantic disconnect between the Drupal URL slug and GSC query keywords."""
    # Decode URL-encoded characters first
    drupal_url_unquoted = urllib.parse.unquote(drupal_url)
    
    if drupal_url in URL_OVERRIDES:
        return URL_OVERRIDES[drupal_url].get("is_disconnect", False), URL_OVERRIDES[drupal_url]["reason"]
    if drupal_url_unquoted in URL_OVERRIDES:
        return URL_OVERRIDES[drupal_url_unquoted].get("is_disconnect", False), URL_OVERRIDES[drupal_url_unquoted]["reason"]
        
    parsed = urlparse(drupal_url_unquoted)
    path = parsed.path.strip('/')
    
    if path.startswith('node/') or 'node' in path.split('/')[0]:
        return False, ""
        
    if 'system/files' in path:
        return False, ""
        
    if path in ['contact', 'overview']:
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
        return True, f"Old slug targets content related to '{path.split('/')[-1]}', but GSC queries are driven by '{top_query}'."
        
    return False, ""

def run_report(service, site_url, start_date, end_date):
    """Executes the Prioritisation report."""
    print(f"Running Drupal to Dato Prioritisation Report for {site_url}...")
    
    slug = get_filename_slug(site_url)
    output_dir = get_output_dir(site_url)
    os.makedirs(output_dir, exist_ok=True)
    
    # 1. Ensure the base query-level migration analysis file exists
    csv_filename = f"drupal-dato-migration-analysis-{slug}-{start_date}-to-{end_date}.csv"
    csv_path = os.path.join(output_dir, csv_filename)
    
    if not os.path.exists(csv_path):
        print(f"Base migration analysis CSV not found at {csv_path}. Running drupal_dato_migration_analysis first...")
        from reports.drupal_dato_migration_analysis import run_report as run_analysis
        run_analysis(service, site_url, start_date, end_date)
        
    if not os.path.exists(csv_path):
        print("Error: Could not generate or read base migration analysis CSV.")
        return None
        
    df_migrate = pd.read_csv(csv_path)
    
    # Filter out /user/login from the migration list
    df_migrate_no_login = df_migrate[df_migrate['page'] != 'https://www.hr-inform.co.uk/user/login'].copy()
    top_50 = df_migrate_no_login.head(50)
    
    total_migrate_clicks = df_migrate_no_login['clicks'].sum()
    total_migrate_imps = df_migrate_no_login['impressions'].sum()
    
    top_50_clicks = top_50['clicks'].sum()
    top_50_imps = top_50['impressions'].sum()
    group_ctr = top_50_clicks / top_50_imps if top_50_imps > 0 else 0
    
    # 2. Fetch GSC Page-Level metrics dynamically for the platform distribution summary
    print("Fetching page-level GSC metrics dynamically...")
    df_all = fetch_with_cache(service, site_url, start_date, end_date, ['page'])
    
    dato_urls = load_dato_urls(slug)
    cleaned_dato_urls = {clean_url(u) for u in dato_urls}
    
    df_all['cleaned_page'] = df_all['page'].apply(clean_url)
    df_all['segment'] = df_all['cleaned_page'].apply(lambda p: 'Dato' if p in cleaned_dato_urls else 'Drupal')
    
    df_dato_seg = df_all[df_all['segment'] == 'Dato']
    df_drupal_seg = df_all[df_all['segment'] == 'Drupal']
    
    dato_clicks = int(df_dato_seg['clicks'].sum())
    dato_imps = int(df_dato_seg['impressions'].sum())
    dato_pages = df_dato_seg['page'].nunique()
    
    drupal_clicks = int(df_drupal_seg['clicks'].sum())
    drupal_imps = int(df_drupal_seg['impressions'].sum())
    drupal_pages = df_drupal_seg['page'].nunique()
    
    total_clicks = dato_clicks + drupal_clicks
    total_imps = dato_imps + drupal_imps
    total_pages = dato_pages + drupal_pages
    
    # 3. Generate list items and check disconnects
    disconnect_items = []
    list_items = []
    
    for idx, row in top_50.reset_index(drop=True).iterrows():
        page_url = row['page']
        clicks = int(row['clicks'])
        impressions = int(row['impressions'])
        ctr = float(row['ctr'])
        position = float(row['position'])
        top_query_val = row.get('top_query_1')
        
        default_url, keyword_url = suggest_dato_url(page_url, top_query_val)
        has_disconnect, disconnect_reason = check_url_disconnect(page_url, top_query_val)
        
        badge_html = ""
        warning_class = ""
        note_html = ""
        if has_disconnect:
            badge_html = ' <span class="badge bg-warning text-dark ms-2" style="font-size: 0.75rem;">⚠️ SEO Disconnect</span>'
            warning_class = "border-start border-warning border-3"
            note_html = f'<div class="text-danger mt-1" style="font-size: 0.82rem;"><strong>Audit Note:</strong> {disconnect_reason}</div>'
            disconnect_items.append((page_url, top_query_val, disconnect_reason))
        
        top_queries = []
        for q_idx in range(1, 4):
            q_val = row.get(f'top_query_{q_idx}')
            q_clicks = row.get(f'top_query_{q_idx}_clicks')
            if pd.notna(q_val) and q_val:
                top_queries.append(f"<code>{html.escape(str(q_val))}</code> ({int(q_clicks):,} clicks)")
                
        queries_str = ", ".join(top_queries)
        
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
                    <div class="fw-bold mb-1"><a href="{page_url}" target="_blank" class="text-break">{html.escape(page_url)}</a>{badge_html}</div>
                    <div class="text-primary mb-1" style="font-size: 0.88rem;">
                        <strong>Top Keywords:</strong> {queries_str}
                    </div>
                    <div class="text-success mb-0" style="font-size: 0.85rem;">
                        <strong>Proposed Dato URL (Default - Shortened):</strong> <a href="{default_url}" target="_blank" class="text-success text-decoration-none">{default_url}</a>
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
        
    list_items_html = "\n".join(list_items)
    
    # 4. Generate disconnect card
    audit_card_html = ""
    if disconnect_items:
        audit_rows = []
        for d_page, d_query, d_reason in disconnect_items:
            row_html = f"""
                <div class="py-2 border-bottom">
                    <strong>Page:</strong> <a href="{d_page}" target="_blank" class="text-break">{html.escape(d_page)}</a><br>
                    <strong>Top Query:</strong> <code>{html.escape(str(d_query))}</code><br>
                    <span class="text-danger">⚠️ {html.escape(d_reason)}</span>
                </div>
            """
            audit_rows.append(row_html)
        
        audit_card_html = f"""
        <div class="card border-warning border-3 mb-4 p-4" style="background-color: #fffdf5;">
            <h4 class="fw-bold text-warning mb-2">⚠️ SEO Disconnects Audit (Action Required)</h4>
            <p class="text-muted">During our check, we identified pages where the search intent (the queries driving organic traffic) is disconnected from the old URL path slug. In these cases, we have manually overridden the suggested Dato URLs to match user intent rather than simply translating the old slug. We should investigate these pages further before deploying redirects.</p>
            <div class="mt-2" style="font-size: 0.9rem;">
                {"".join(audit_rows)}
            </div>
        </div>
        """
        
    # Navigation bar template
    nav_html = f"""
    <div class="d-flex flex-wrap gap-2 justify-content-center mb-4 pb-3 border-bottom">
        <a href="dato-drupal-index-{slug}-{start_date}-to-{end_date}.html" class="btn btn-outline-primary px-4">Migration Index</a>
        <a href="drupal-dato-migration-analysis-{slug}-{start_date}-to-{end_date}.html" class="btn btn-outline-primary px-4">Breakdown Dashboard (Query-Level)</a>
        <a href="drupal-dato-migration-page-level-report-{slug}-{start_date}-to-{end_date}.html" class="btn btn-outline-primary px-4">Page-Level Report (All Clicks)</a>
        <a href="drupal-dato-migration-prioritisation-report-{slug}-{start_date}-to-{end_date}.html" class="btn btn-primary active px-4">Top 50 Prioritisation Report</a>
        <a href="dato-suggested-urls-alphabetical-{slug}-{start_date}-to-{end_date}.html" class="btn btn-outline-primary px-4">Proposed Dato URLs (Alphabetical)</a>
        <a href="gsc-data-comparison-{slug}-{start_date}-to-{end_date}.html" class="btn btn-outline-primary px-4">GSC Data Comparison</a>
        <a href="dato-pages-performance-report-{slug}-{start_date}-to-{end_date}.html" class="btn btn-outline-primary px-4">Dato Pages Performance</a>
    </div>
    """
    
    html_content = f"""<!DOCTYPE html>
<html lang="en-GB">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Drupal to Dato Prioritised Migration Report (Top 50 Pages)</title>
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
        h1 {{
            border-bottom: 2px solid #eee;
            padding-bottom: 0.75rem;
            margin-bottom: 2rem;
        }}
        h2 {{
            margin-top: 2.5rem;
            margin-bottom: 1.25rem;
            border-bottom: 1px solid #eee;
            padding-bottom: 0.5rem;
        }}
        .metric-card {{
            border: none;
            border-radius: 10px;
            box-shadow: 0 3px 10px rgba(0,0,0,0.04);
            background-color: #fcfcfc;
        }}
        .table {{
            margin-top: 1.5rem;
            margin-bottom: 1.5rem;
        }}
        .alert-warning {{
            border-left: 4px solid #ffc107;
            background-color: #fffdf5;
            color: #664d03;
        }}
        .list-group-item {{
            border: none;
            border-bottom: 1px solid #eee;
        }}
        .list-group-item:last-child {{
            border-bottom: none;
        }}
        .w-70 {{
            width: 70%;
        }}
    </style>
</head>
<body>
<div class="container-fluid py-4">
    <!-- Header -->
    <div class="d-flex align-items-center justify-content-between border-bottom pb-3 mb-4">
        <div>
            <h1 class="h3 mb-1 fw-bold text-dark">Drupal to Dato Prioritised Migration Report</h1>
            <p class="text-muted mb-0">Property: <strong>{html.escape(site_url)}</strong> | Reporting Period: <strong>{start_date} to {end_date}</strong></p>
        </div>
        <div class="text-end">
            <span class="badge bg-secondary p-2">Report generated on {datetime.now().strftime("%Y-%m-%d")}</span>
        </div>
    </div>

    <!-- Navigation Menu -->
    {nav_html}
    
    <!-- Top 50 Group Highlights Card -->
    <div class="card metric-card mb-4 border-start border-primary border-4 p-4">
        <h4 class="fw-bold text-primary mb-3">Top 50 Pages to Migrate: Performance Summary</h4>
        <p class="text-muted">Below are the cumulative metrics for the group of top 50 Drupal pages (excluding utility pages like <code>/user/login</code>). This shows the massive impact of focusing our initial rewriting efforts on this small subset of pages.</p>
        
        <div class="row g-4 text-center mt-1">
            <div class="col-md-3">
                <small class="text-muted d-block uppercase font-weight-bold">Group Clicks</small>
                <span class="h2 fw-bold text-dark">{top_50_clicks:,}</span>
            </div>
            <div class="col-md-3">
                <small class="text-muted d-block">Group Impressions</small>
                <span class="h2 fw-bold text-dark">{top_50_imps:,}</span>
            </div>
            <div class="col-md-3">
                <small class="text-muted d-block">Average CTR</small>
                <span class="h2 fw-bold text-dark">{group_ctr:.2%}</span>
            </div>
            <div class="col-md-3">
                <small class="text-muted d-block">Share of Drupal Click Traffic</small>
                <span class="h2 fw-bold text-success">{top_50_clicks / total_migrate_clicks:.2%}</span>
            </div>
        </div>
        
        <div class="mt-3 bg-light p-3 rounded text-secondary" style="font-size: 0.92rem;">
            💡 <strong>Insight:</strong> By migrating and redirecting just these <strong>50 pages</strong> (representing <strong>{50 / drupal_pages:.2%}</strong> of the {drupal_pages:,} remaining content pages), we will secure and carry over <strong>{top_50_clicks / total_migrate_clicks:.2%}</strong> of the organic search clicks currently driving traffic to our Drupal content.
        </div>
    </div>

    <!-- Platform Breakdown Summary -->
    <h2>Platform Breakdown Summary</h2>
    <p>The table below contrasts the search performance of the new, standalone Dato pages against the legacy pages running on the old Drupal platform:</p>
    
    <table class="table table-striped table-bordered align-middle">
        <thead class="table-dark">
            <tr>
                <th>Platform Segment</th>
                <th class="text-end">Organic Clicks</th>
                <th class="text-end">Click Share</th>
                <th class="text-end">Impressions</th>
                <th class="text-end">Impressions Share</th>
                <th class="text-end">Average CTR</th>
                <th class="text-end">Unique Landing Pages</th>
                <th class="text-end">Page Share</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td><strong>Dato (New Content)</strong></td>
                <td class="text-end">{dato_clicks:,}</td>
                <td class="text-end">{(dato_clicks/total_clicks):.2%}</td>
                <td class="text-end">{dato_imps:,}</td>
                <td class="text-end">{(dato_imps/total_imps):.2%}</td>
                <td class="text-end">{(dato_clicks/dato_imps) if dato_imps > 0 else 0:.2%}</td>
                <td class="text-end">{dato_pages:,}</td>
                <td class="text-end">{(dato_pages/total_pages):.2%}</td>
            </tr>
            <tr class="table-danger">
                <td><strong>Drupal (Old / "Purple")</strong></td>
                <td class="text-end">{drupal_clicks:,}</td>
                <td class="text-end">{(drupal_clicks/total_clicks):.2%}</td>
                <td class="text-end">{drupal_imps:,}</td>
                <td class="text-end">{(drupal_imps/total_imps):.2%}</td>
                <td class="text-end">{(drupal_clicks/drupal_imps) if drupal_imps > 0 else 0:.2%}</td>
                <td class="text-end">{drupal_pages:,}</td>
                <td class="text-end">{(drupal_pages/total_pages):.2%}</td>
            </tr>
            <tr class="table-group-divider fw-bold">
                <td>Total Site</td>
                <td class="text-end">{total_clicks:,}</td>
                <td class="text-end">100.00%</td>
                <td class="text-end">{total_imps:,}</td>
                <td class="text-end">100.00%</td>
                <td class="text-end">{(total_clicks/total_imps) if total_imps > 0 else 0:.2%}</td>
                <td class="text-end">{total_pages:,}</td>
                <td class="text-end">100.00%</td>
            </tr>
        </tbody>
    </table>

    <!-- SEO Disconnects Audit Section -->
    {audit_card_html}

    <!-- Top 50 list -->
    <h2>Top 50 Drupal Pages to Migrate &amp; Redirect</h2>
    <p>The following list ranks the top 50 content pages on the old Drupal platform by organic clicks, displaying their primary search queries and key GSC metrics. Focus our initial migration efforts here to capture the bulk of the old site's traffic.</p>
    
    <ol class="list-group list-group-numbered">
        {list_items_html}
    </ol>

    <h2>Next Steps &amp; Exports</h2>
    <p>The full prioritised list of all Drupal pages and their top search queries is available in the outputs:</p>
    <ul>
        <li><strong>Interactive HTML Report:</strong> <a href="drupal-dato-migration-analysis-{slug}-{start_date}-to-{end_date}.html">drupal-dato-migration-analysis-{slug}-{start_date}-to-{end_date}.html</a></li>
        <li><strong>Actionable CSV Export:</strong> <a href="drupal-dato-migration-analysis-{slug}-{start_date}-to-{end_date}.csv">drupal-dato-migration-analysis-{slug}-{start_date}-to-{end_date}.csv</a></li>
    </ul>
</div>
<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>"""

    out_path = os.path.join(output_dir, f"drupal-dato-migration-prioritisation-report-{slug}-{start_date}-to-{end_date}.html")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html_content)
        
    print(f"Summary HTML report with Top 50 and Disconnect Audit generated successfully at: {out_path}")
    return out_path

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Run Drupal to Dato prioritisation report.')
    parser.add_argument('site_url', nargs='?', default='https://www.hr-inform.co.uk', help='The site URL or property.')
    parser.add_argument('--start-date', help='Start date (YYYY-MM-DD).')
    parser.add_argument('--end-date', help='End date (YYYY-MM-DD).')
    parser.add_argument('--last-7-days', action='store_true', help='Run for the last 7 available days.')
    parser.add_argument('--last-month', action='store_true', help='Run for the last calendar month.')
    
    args = parser.parse_args()
    
    service = get_gsc_service()
    if service:
        start_date, end_date = parse_standard_date_args(args, service, args.site_url)
        run_report(service, args.site_url, start_date, end_date)
