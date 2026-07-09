"""
Report script to analyse GSC page-level performance data for www.hr-inform.co.uk.
Segments page-level GSC data into Drupal and Dato platforms and suggests target URLs.
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

def suggest_dato_url(drupal_url):
    """Suggests a new Dato target URL structure for a legacy Drupal URL."""
    # Decode URL-encoded characters (like %20 -> space) first
    drupal_url_unquoted = urllib.parse.unquote(drupal_url)
    
    if drupal_url in URL_OVERRIDES:
        return URL_OVERRIDES[drupal_url]["url"]
    if drupal_url_unquoted in URL_OVERRIDES:
        return URL_OVERRIDES[drupal_url_unquoted]["url"]
        
    parsed = urlparse(drupal_url_unquoted)
    path = parsed.path.strip('/')
    
    parts = path.split('/')
    last_part = parts[-1] if parts else ""
    
    is_node = len(parts) >= 2 and parts[0] == 'node'
    if is_node or not last_part:
        slug_str = f"page-{parts[-1]}" if parts else "home"
    else:
        if '.' in last_part:
            last_part = last_part.rsplit('.', 1)[0]
        slug_str = clean_and_shorten_slug(last_part)
        if not slug_str:
            slug_str = f"page-{parts[-1]}" if parts else "home"

    is_template = any(k in path.lower() or k in slug_str.lower() for k in ['template', 'download', 'file', 'form', 'docx', 'pdf', 'checklist', 'model'])
    is_news = 'news-article' in path.lower() or 'comment' in path.lower()
    is_law = 'employment_law' in path.lower() or 'legislation' in path.lower()
    
    if is_template:
        folder = "resources"
        if 'template' not in slug_str:
            slug_str = f"{slug_str}-template"
    elif is_news:
        folder = "features"
    elif is_law:
        folder = "guides"
    else:
        folder = "features"
        
    return f"https://www.hr-inform.co.uk/{folder}/{slug_str}"

def run_report(service, site_url, start_date, end_date):
    """Executes the Page-Level Report."""
    print(f"Running Drupal to Dato Migration Page-Level Report for {site_url}...")
    
    slug = get_filename_slug(site_url)
    output_dir = get_output_dir(site_url)
    os.makedirs(output_dir, exist_ok=True)
    
    # 1. Fetch Page-Level data (dimension: 'page')
    df = fetch_with_cache(service, site_url, start_date, end_date, ['page'])
    
    if df.empty:
        print("No page data found.")
        return None
        
    # 2. Segment into Drupal vs Dato platforms
    dato_urls = load_dato_urls(slug)
    cleaned_dato_urls = {clean_url(u) for u in dato_urls}
    
    df['cleaned_page'] = df['page'].apply(clean_url)
    df['segment'] = df['cleaned_page'].apply(lambda p: 'Dato' if p in cleaned_dato_urls else 'Drupal')
    
    df_dato = df[df['segment'] == 'Dato']
    df_drupal = df[df['segment'] == 'Drupal']
    
    dato_clicks = int(df_dato['clicks'].sum())
    dato_imps = int(df_dato['impressions'].sum())
    dato_pages = df_dato['page'].nunique()
    
    drupal_clicks = int(df_drupal['clicks'].sum())
    drupal_imps = int(df_drupal['impressions'].sum())
    drupal_pages = df_drupal['page'].nunique()
    
    total_clicks = dato_clicks + drupal_clicks
    total_imps = dato_imps + drupal_imps
    total_pages = dato_pages + drupal_pages
    
    clicks_progress = (dato_clicks / total_clicks * 100) if total_clicks > 0 else 0
    pages_progress = (dato_pages / total_pages * 100) if total_pages > 0 else 0
    
    # 3. Clean Drupal list and map proposed URLs
    df_drupal_clean = df_drupal.copy()
    df_drupal_migrate = df_drupal_clean[df_drupal_clean['page'] != 'https://www.hr-inform.co.uk/user/login'].copy()
    df_drupal_migrate = df_drupal_migrate.sort_values('clicks', ascending=False)
    df_drupal_migrate['suggested_url'] = df_drupal_migrate['page'].apply(suggest_dato_url)
    
    # 4. Save CSV
    csv_out_path = os.path.join(output_dir, f"drupal-dato-migration-page-level-report-{slug}-{start_date}-to-{end_date}.csv")
    df_drupal_migrate.to_csv(csv_out_path, index=False, columns=['page', 'clicks', 'impressions', 'ctr', 'position', 'suggested_url'])
    print(f"Page-level CSV saved to: {csv_out_path}")
    
    # 5. Generate HTML
    top_50_drupal = df_drupal_migrate.head(50)
    
    table_rows = []
    for idx, row in top_50_drupal.reset_index(drop=True).iterrows():
        page_url = row['page']
        clicks = int(row['clicks'])
        impressions = int(row['impressions'])
        ctr = float(row['ctr'])
        position = float(row['position'])
        s_url = row['suggested_url']
        
        row_html = f"""
        <tr>
            <td class="text-center fw-bold">{idx + 1}</td>
            <td class="page-url-cell"><a href="{page_url}" target="_blank" class="text-break">{html.escape(page_url)}</a></td>
            <td class="text-end fw-bold">{clicks:,}</td>
            <td class="text-end">{impressions:,}</td>
            <td class="text-end">{ctr:.2%}</td>
            <td class="text-end">{position:.2f}</td>
            <td class="suggested-url-cell"><a href="{s_url}" target="_blank" class="text-success text-decoration-none">{s_url}</a></td>
        </tr>
        """
        table_rows.append(row_html)
        
    table_rows_html = "\n".join(table_rows)
    
    # Navigation bar template
    nav_html = f"""
    <div class="d-flex flex-wrap gap-2 justify-content-center mb-4 pb-3 border-bottom">
        <a href="dato-drupal-index-{slug}-{start_date}-to-{end_date}.html" class="btn btn-outline-primary px-4">Migration Index</a>
        <a href="drupal-dato-migration-analysis-{slug}-{start_date}-to-{end_date}.html" class="btn btn-outline-primary px-4">Breakdown Dashboard (Query-Level)</a>
        <a href="drupal-dato-migration-page-level-report-{slug}-{start_date}-to-{end_date}.html" class="btn btn-primary active px-4">Page-Level Report (All Clicks)</a>
        <a href="drupal-dato-migration-prioritisation-report-{slug}-{start_date}-to-{end_date}.html" class="btn btn-outline-primary px-4">Top 50 Prioritisation Report</a>
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
    <title>Drupal to Dato Page-Level Migration Report: {site_url}</title>
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
            margin-top: 1.5rem;
        }}
    </style>
</head>
<body>
<div class="container-fluid py-4">
    <!-- Header -->
    <div class="d-flex align-items-center justify-content-between border-bottom pb-3 mb-4">
        <div>
            <h1 class="h3 mb-1 fw-bold text-dark">Drupal to Dato Migration Analysis (Page-Level)</h1>
            <p class="text-muted mb-0">Property: <strong>{html.escape(site_url)}</strong> | Reporting Period: <strong>{start_date} to {end_date}</strong></p>
        </div>
        <div class="text-end">
            <span class="badge bg-secondary p-2">Report generated on {datetime.now().strftime("%Y-%m-%d")}</span>
        </div>
    </div>

    <!-- Navigation Menu -->
    {nav_html}

    <!-- Platform Breakdown Dashboard -->
    <h4 class="fw-bold mb-3 text-secondary">Platform Breakdown Summary (Unfiltered Page-Level Data)</h4>
    <p class="text-muted">This report displays performance metrics derived from page-level analytics (which contains all GSC clicks and impressions, including long-tail anonymous queries).</p>
    
    <div class="row g-4 mb-4">
        <!-- Progress Bars Card -->
        <div class="col-xl-4 col-md-12">
            <div class="card h-100 metric-card p-4">
                <h5 class="card-title fw-bold text-muted mb-4">Platform Distribution</h5>
                
                <div class="mb-3">
                    <div class="d-flex justify-content-between mb-1">
                        <span class="fw-semibold">Dato Clicks (New Content)</span>
                        <span class="fw-bold text-success">{(dato_clicks / total_clicks * 100):.1f}%</span>
                    </div>
                    <div class="progress-bar-custom">
                        <div class="progress-fill-dato" style="width: {clicks_progress}%;"></div>
                    </div>
                    <small class="text-muted">{dato_clicks:,} / {total_clicks:,} total clicks</small>
                </div>
                
                <div>
                    <div class="d-flex justify-content-between mb-1">
                        <span class="fw-semibold">Dato Pages (New Content)</span>
                        <span class="fw-bold text-success">{(dato_pages / total_pages * 100):.1f}%</span>
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
                        <span class="h4 fw-bold text-dark">{drupal_clicks:,}</span>
                    </div>
                    <div class="col-6 mb-3">
                        <small class="text-muted d-block">Organic Impressions</small>
                        <span class="h4 fw-bold text-dark">{drupal_imps:,}</span>
                    </div>
                    <div class="col-6">
                        <small class="text-muted d-block">Landing Pages</small>
                        <span class="h4 fw-bold text-dark">{drupal_pages:,}</span>
                    </div>
                    <div class="col-6">
                        <small class="text-muted d-block">Average CTR</small>
                        <span class="h4 fw-bold text-dark">{(drupal_clicks/drupal_imps) if drupal_imps > 0 else 0:.2%}</span>
                    </div>
                </div>
            </div>
        </div>

        <!-- Dato Card -->
        <div class="col-xl-4 col-md-6">
            <div class="card h-100 metric-card p-4 border-start border-success border-4">
                <h5 class="card-title fw-bold text-success mb-3">Dato (New Platform)</h5>
                <div class="row">
                    <div class="col-6 mb-3">
                        <small class="text-muted d-block">Organic Clicks</small>
                        <span class="h4 fw-bold text-dark">{dato_clicks:,}</span>
                    </div>
                    <div class="col-6 mb-3">
                        <small class="text-muted d-block">Organic Impressions</small>
                        <span class="h4 fw-bold text-dark">{dato_imps:,}</span>
                    </div>
                    <div class="col-6">
                        <small class="text-muted d-block">Landing Pages</small>
                        <span class="h4 fw-bold text-dark">{dato_pages:,}</span>
                    </div>
                    <div class="col-6">
                        <small class="text-muted d-block">Average CTR</small>
                        <span class="h4 fw-bold text-dark">{(dato_clicks/dato_imps) if dato_imps > 0 else 0:.2%}</span>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <!-- Top 50 Pages Summary Table -->
    <h2>Top 50 Drupal Pages to Migrate &amp; Redirect (Page-Level Clicks)</h2>
    <p class="text-muted">The following list details the top 50 pages on the old Drupal platform ranked by total page-level clicks (representing all search traffic). Focus initial migration efforts here to capture the largest portion of old site traffic.</p>
    
    <div class="table-responsive">
        <table class="table table-hover table-striped align-middle mb-0">
            <thead class="table-dark">
                <tr>
                    <th class="text-center" style="width: 60px;">Rank</th>
                    <th>Drupal Landing Page URL</th>
                    <th class="text-end" style="width: 120px;">Clicks</th>
                    <th class="text-end" style="width: 150px;">Impressions</th>
                    <th class="text-end" style="width: 100px;">CTR</th>
                    <th class="text-end" style="width: 120px;">Avg. Position</th>
                    <th>Suggested Dato URL Target</th>
                </tr>
            </thead>
            <tbody>
                {table_rows_html}
            </tbody>
        </table>
    </div>
</div>
<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>"""

    html_out_path = os.path.join(output_dir, f"drupal-dato-migration-page-level-report-{slug}-{start_date}-to-{end_date}.html")
    with open(html_out_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"Page-level HTML report saved to: {html_out_path}")
    
    return html_out_path

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Run Drupal to Dato page-level report.')
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
