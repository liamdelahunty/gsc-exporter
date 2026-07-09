"""
Report script to generate the Library to Marketing Migration Prioritisation Report.
Queries Google Search Console data for library.croneri.co.uk, maps deep technical reference
articles to proposed marketing URLs on www.croneri.co.uk under the appropriate folder structure,
and checks for semantic search disconnects.
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
    
    path_lower = path.lower()
    
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

def run_report(service, site_url, start_date, end_date, limit=100, max_rows=10000):
    """Executes the Library to Marketing Prioritisation Report."""
    print(f"Running Library to Marketing Migration Prioritisation Report for {site_url}...")
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
    
    # Construct rows for prioritisation report
    csv_rows = []
    list_items = []
    disconnect_items = []
    
    top_n_pages = df_pages.head(limit).copy()
    
    # Cumulative stats for the top list
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
        
        # Add to CSV row structure
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
        
        # Collect top 3 queries for display
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
        
        # Build HTML list item
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
    print(f"CSV saved to: {csv_path}")
    
    # Generate disconnect cards
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
            <p class="text-muted">During our check, we identified library pages where the search intent (the queries driving organic traffic) is disconnected from the library URL path slug. In these cases, we should review the proposed URL slug to ensure it aligns with user intent rather than simply translating the old path.</p>
            <div class="mt-2" style="font-size: 0.9rem; max-height: 400px; overflow-y: auto;">
                {"".join(audit_rows)}
            </div>
        </div>
        """
        
    list_items_html = "\n".join(list_items)
    
    html_content = f"""<!DOCTYPE html>
<html lang="en-GB">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Library to Marketing Migration Prioritisation Report</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body {{
            background-color: #0b0f19;
            color: #f3f4f6;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            padding-bottom: 4rem;
        }}
        .hero-section {{
            background: linear-gradient(135deg, #1e3a8a, #0f172a);
            border-bottom: 3px solid #3b82f6;
            padding: 3rem 1.5rem;
            margin-bottom: 2rem;
            border-radius: 0 0 24px 24px;
        }}
        h1, h2, h3, h4 {{
            font-weight: 700;
        }}
        .metric-card {{
            background-color: #111827;
            border: 1px solid #1f2937;
            border-radius: 16px;
            box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.3);
            transition: transform 0.2s, border-color 0.2s;
        }}
        .metric-card:hover {{
            transform: translateY(-2px);
            border-color: #3b82f6;
        }}
        .list-group-item {{
            background-color: #111827;
            border-color: #1f2937;
            color: #e5e7eb;
            transition: background-color 0.2s;
        }}
        .list-group-item:hover {{
            background-color: #1f2937;
        }}
        .text-muted {{
            color: #9ca3af !important;
        }}
        .w-70 {{
            width: 70%;
        }}
        a {{
            color: #3b82f6;
        }}
        a:hover {{
            color: #60a5fa;
            text-decoration: underline;
        }}
        .badge-disconnect {{
            background-color: #d97706;
            color: #000;
        }}
    </style>
</head>
<body>

<div class="hero-section text-center">
    <div class="container-fluid">
        <h1 class="display-5 mb-2">Library to Marketing Migration Prioritisation Report</h1>
        <p class="lead text-muted">Property: <strong>{html.escape(site_url)}</strong> | Reporting Period: <strong>{start_date} to {end_date}</strong></p>
        <span class="badge bg-primary p-2">Report generated on {datetime.now().strftime("%Y-%m-%d")}</span>
    </div>
</div>

<div class="container-fluid px-4">
    <!-- Highlight Cards -->
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

    <!-- Explanatory Note -->
    <div class="card metric-card mb-4 p-4 border-start border-blue border-4">
        <h4 class="fw-bold mb-2">💡 Migration Intent</h4>
        <p class="text-secondary mb-0">
            We want to see the best performing pages on the deep research portal <code>library.croneri.co.uk</code>, and propose
            marketing versions on the core business site <code>www.croneri.co.uk</code>. By reviewing the top performing reference
            content, we can capture high-intent search traffic and redirect it to dedicated lead-generation landing pages.
        </p>
    </div>

    <!-- SEO Disconnects Audit Section -->
    {audit_card_html}

    <!-- Top Pages List -->
    <h2 class="fw-bold text-light mb-3">Top Performing Library Pages to Migrate</h2>
    <p class="text-muted mb-3">Below are the top library pages ranked by organic clicks, displaying their primary search queries and proposed target URLs on www.croneri.co.uk.</p>
    
    <ul class="list-group">
        {list_items_html}
    </ul>

    <h2 class="fw-bold text-light mt-5 mb-3">Next Steps &amp; Exports</h2>
    <p class="text-muted">The complete dataset of library pages, GSC metrics, and proposed target marketing URLs has been exported to the following location:</p>
    <ul>
        <li><strong>Actionable CSV Export:</strong> <a href="file://{csv_path}">{csv_filename}</a></li>
    </ul>
</div>

<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>"""
    
    html_filename = f"library-marketing-migration-prioritisation-report-{slug}-{start_date}-to-{end_date}.html"
    html_path = os.path.join(output_dir, html_filename)
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_content)
        
    print(f"HTML report generated successfully at: {html_path}")
    print(f"Exported files are located at:\n  CSV:  [CSV File](file://{csv_path})\n  HTML: [HTML Report](file://{html_path})")
    
    return csv_path, html_path

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Run Library to Marketing Prioritisation Report.')
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
