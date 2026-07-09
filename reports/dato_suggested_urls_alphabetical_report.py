"""
Report script to generate the Proposed Dato URLs (Alphabetical) listing for Drupal to Dato migration.
Reads GSC data, suggests clean targets, and generates an alphabetical HTML mapping page.
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
        "url": "https://www.hr-inform.co.uk/features/webinars"
    },
    "https://www.hr-inform.co.uk/templates-and-tools/medical-checks": {
        "url": "https://www.hr-inform.co.uk/resources/employee-health-questionnaire-template"
    },
    "https://www.hr-inform.co.uk/news-article/action-on-gender-diversity-led-to-resignation-of-bbc-dj": {
        "url": "https://www.hr-inform.co.uk/features/simon-mayo-illness"
    },
    "https://www.hr-inform.co.uk/templates-and-tools/probationary-periods": {
        "url": "https://www.hr-inform.co.uk/resources/probation-review-template"
    },
    "https://www.hr-inform.co.uk/case-law?field_category_target_id=15": {
        "url": "https://www.hr-inform.co.uk/guides/unfair-dismissal-cases"
    },
    "https://www.hr-inform.co.uk/employment_law/employment-law-in-canada": {
        "url": "https://www.hr-inform.co.uk/guides/canadian-labour-laws"
    },
    "https://www.hr-inform.co.uk/system/files/downloads/2017-09/Template%20payslips.docx": {
        "url": "https://www.hr-inform.co.uk/resources/free-payslip-template"
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
    """Cleans GSC query keywords to form a URL slug."""
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

def generate_seo_metadata(url, top_query=None):
    """Suggests an SEO title and meta description for a given proposed Dato URL."""
    parsed = urlparse(url)
    path = parsed.path.strip('/')
    parts = path.split('/')
    folder = parts[0] if parts else "features"
    slug_str = parts[-1] if len(parts) > 1 else ""
    
    # Base readable name from slug
    slug_clean = slug_str.replace('-template', '').replace('-', ' ').strip()
    title_base = slug_clean.title()
    
    if top_query and isinstance(top_query, str):
        clean_query = top_query.replace('-', ' ').strip()
        title_base = clean_query.title()
        
    if folder in ['resources', 'policies'] or 'template' in slug_str:
        suggested_title = f"{title_base} Template | HR-inform"
        meta_desc = f"Download our free, customisable {title_base.lower()} template. Ensure your business remains fully compliant with UK employment law."
    elif folder == 'guides':
        suggested_title = f"Guide to {title_base} | HR-inform"
        meta_desc = f"Explore our comprehensive employer guide to {title_base.lower()}. Learn about key legal requirements and best practices under UK law."
    else:
        suggested_title = f"{title_base} | Latest HR Updates & Analysis"
        meta_desc = f"Read the latest updates, expert insights, and compliance analysis on {title_base.lower()} from the HR-inform editorial team."
        
    return suggested_title, meta_desc

def run_report(service, site_url, start_date, end_date):
    """Executes the Alphabetical URL report."""
    print(f"Running Proposed Dato URLs Alphabetical Report for {site_url}...")
    
    slug = get_filename_slug(site_url)
    output_dir = get_output_dir(site_url)
    os.makedirs(output_dir, exist_ok=True)
    
    # Ensure base migration analysis CSV exists
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
    
    # Filter out login
    df_migrate_no_login = df_migrate[df_migrate['page'] != 'https://www.hr-inform.co.uk/user/login'].copy()
    top_50 = df_migrate_no_login.head(50)
    
    proposed_data = {}
    for idx, row in top_50.iterrows():
        page_url = row['page']
        top_query_val = row.get('top_query_1')
        default_url, keyword_url = suggest_dato_url(page_url, top_query_val)
        
        # Map default
        if default_url not in proposed_data:
            proposed_data[default_url] = {'sources': set(), 'top_query': top_query_val}
        proposed_data[default_url]['sources'].add(page_url)
        
        # Map keyword alternative
        if keyword_url not in proposed_data:
            proposed_data[keyword_url] = {'sources': set(), 'top_query': top_query_val}
        proposed_data[keyword_url]['sources'].add(page_url)
        
    sorted_urls = sorted(list(proposed_data.keys()))
    
    list_items = []
    for url in sorted_urls:
        sources = sorted(list(proposed_data[url]['sources']))
        top_query_val = proposed_data[url]['top_query']
        suggested_title, suggested_meta = generate_seo_metadata(url, top_query_val)
        
        source_links = [f'<a href="{s}" target="_blank" class="text-break">{html.escape(s)}</a>' for s in sources]
        source_links_str = ", ".join(source_links)
        
        item_html = f"""
        <li class="list-group-item py-3">
            <div class="d-flex justify-content-between align-items-center mb-1">
                <span class="url-text fw-bold text-success text-break"><a href="{url}" target="_blank">{html.escape(url)}</a></span>
                <button class="btn btn-sm btn-outline-secondary copy-btn px-3" onclick="copyToClipboard('{html.escape(url)}', this)" style="font-size: 0.8rem; border-radius: 6px;">Copy URL</button>
            </div>
            <div class="text-muted mb-2" style="font-size: 0.82rem;">
                <strong>Old Drupal Source(s):</strong> {source_links_str}
            </div>
            <div class="p-3 rounded border-start border-primary border-3" style="background-color: #fcfcfc; font-size: 0.85rem;">
                <div class="mb-1"><strong>Suggested SEO Title:</strong> <span class="text-dark fw-semibold">{html.escape(suggested_title)}</span></div>
                <div><strong>Suggested Meta Description:</strong> <span class="text-muted">{html.escape(suggested_meta)}</span></div>
            </div>
        </li>
        """
        list_items.append(item_html)
        
    list_items_html = "\n".join(list_items)
    
    # Navigation bar template
    nav_html = f"""
    <div class="d-flex flex-wrap gap-2 justify-content-center mb-4 pb-3 border-bottom">
        <a href="dato-drupal-index-{slug}-{start_date}-to-{end_date}.html" class="btn btn-outline-primary px-4">Migration Index</a>
        <a href="drupal-dato-migration-analysis-{slug}-{start_date}-to-{end_date}.html" class="btn btn-outline-primary px-4">Breakdown Dashboard (Query-Level)</a>
        <a href="drupal-dato-migration-page-level-report-{slug}-{start_date}-to-{end_date}.html" class="btn btn-outline-primary px-4">Page-Level Report (All Clicks)</a>
        <a href="drupal-dato-migration-prioritisation-report-{slug}-{start_date}-to-{end_date}.html" class="btn btn-outline-primary px-4">Top 50 Prioritisation Report</a>
        <a href="dato-suggested-urls-alphabetical-{slug}-{start_date}-to-{end_date}.html" class="btn btn-primary active px-4">Proposed Dato URLs (Alphabetical)</a>
        <a href="gsc-data-comparison-{slug}-{start_date}-to-{end_date}.html" class="btn btn-outline-primary px-4">GSC Data Comparison</a>
        <a href="dato-pages-performance-report-{slug}-{start_date}-to-{end_date}.html" class="btn btn-outline-primary px-4">Dato Pages Performance</a>
    </div>
    """
    
    html_content = f"""<!DOCTYPE html>
<html lang="en-GB">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Proposed Dato URLs: {len(sorted_urls)} Unique Paths</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body {{
            background-color: #f8f9fa;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            color: #333;
            padding-bottom: 4rem;
        }}
        h1 {{
            font-weight: 700;
            color: #2c3e50;
        }}
        .list-group-item {{
            border: none;
            border-bottom: 1px solid #eee;
        }}
        .list-group-item:last-child {{
            border-bottom: none;
        }}
        .copy-btn {{
            transition: all 0.2s;
        }}
    </style>
</head>
<body>
<div class="container py-4">
    <!-- Header -->
    <div class="d-flex align-items-center justify-content-between border-bottom pb-3 mb-4">
        <div>
            <h1 class="h3 mb-1 fw-bold text-dark">Proposed DatoCMS Target URLs</h1>
            <p class="text-muted mb-0">Property: <strong>{html.escape(site_url)}</strong> | Reporting Period: <strong>{start_date} to {end_date}</strong></p>
        </div>
        <div class="text-end">
            <span class="badge bg-secondary p-2">Report generated on {datetime.now().strftime("%Y-%m-%d")}</span>
        </div>
    </div>

    <!-- Navigation Menu -->
    {nav_html}

    <div class="alert alert-info py-3 mb-4">
        💡 <strong>Proposed target URLs</strong> are sorted alphabetically below. Both default (slug-based) and keyword-aligned options are mapped to help you quickly identify the best redirection targets.
    </div>

    <ul class="list-group shadow-sm rounded bg-white" id="urlList">
        {list_items_html}
    </ul>
    
    <div class="text-center mt-4">
        <a href="drupal-dato-migration-prioritisation-report-{slug}-{start_date}-to-{end_date}.html" class="btn btn-primary px-4 py-2" style="border-radius: 8px;">Back to Prioritisation Report</a>
    </div>
</div>

<script>
    function copyToClipboard(text, button) {{
        navigator.clipboard.writeText(text).then(function() {{
            var originalText = button.textContent;
            button.textContent = "Copied!";
            button.classList.replace("btn-outline-secondary", "btn-success");
            setTimeout(function() {{
                button.textContent = originalText;
                button.classList.replace("btn-success", "btn-outline-secondary");
            }}, 1500);
        }}, function(err) {{
            console.error('Could not copy text: ', err);
        }});
    }}
</script>
<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>"""

    out_path = os.path.join(output_dir, f"dato-suggested-urls-alphabetical-{slug}-{start_date}-to-{end_date}.html")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html_content)
        
    print(f"Alphabetical proposed URLs report generated successfully at: {out_path}")
    return out_path

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Run Proposed Dato URLs Alphabetical Report.')
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
