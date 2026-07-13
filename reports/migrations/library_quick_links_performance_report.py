"""
Report script to generate GSC performance reports for Croner-i Library Quick Links.
Generates four reports:
1. Highlighted Quick Links (Keywords)
2. Highlighted Quick Links (Page-only - Unfiltered)
3. All Quick Links (Keywords)
4. All Quick Links (Page-only - Unfiltered)
Each HTML report shares a unified navigation header.
"""
import os
import sys
import pandas as pd
import numpy as np
import argparse
import html
from datetime import datetime
from urllib.parse import urlparse
from html.parser import HTMLParser

# Add parent directory to sys.path to allow importing core
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.naming import get_output_dir, get_filename_slug
from core.cache import fetch_with_cache
from core.client import get_gsc_service
from core.date_utils import parse_standard_date_args

HIGHLIGHTED_URLS = {
    "https://library.croneri.co.uk/topic/company-purchase-own-shares",
    "https://library.croneri.co.uk/topic/making-tax-digital",
    "https://library.croneri.co.uk/topic/engagement-letters-and-compliance",
    "https://library.croneri.co.uk/topic/business-asset-disposal-relief-badr",
    "https://library.croneri.co.uk/topic/hold-over-relief-gifts",
    "https://library.croneri.co.uk/topic/losses-corporation-tax",
    "https://library.croneri.co.uk/topic/frs-102",
    "https://library.croneri.co.uk/topic/intangible-fixed-assets",
    "https://library.croneri.co.uk/topic/group-relief",
    "https://library.croneri.co.uk/topic/enterprise-management-incentives-emi",
    "https://library.croneri.co.uk/topic/business-property-relief",
    "https://library.croneri.co.uk/topic/rollover-relief",
    "https://library.croneri.co.uk/topic/employee-ownership-trusts-eots",
    "https://library.croneri.co.uk/topic/capital-allowances",
    "https://library.croneri.co.uk/topic/cars-and-vans",
    "https://library.croneri.co.uk/topic/charities",
    "https://library.croneri.co.uk/topic/capital-gains-tax-non-residents",
    "https://library.croneri.co.uk/topic/loans-directors-and-employees",
    "https://library.croneri.co.uk/topic/annual-investment-allowance-aia"
}

class QuickLinksHrefExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = {}

    def handle_starttag(self, tag, attrs):
        if tag == 'a':
            href = None
            for name, value in attrs:
                if name == 'href':
                    href = value
                    break
            if href:
                if href.startswith('/'):
                    abs_url = "https://library.croneri.co.uk" + href
                elif not href.startswith('http'):
                    abs_url = "https://library.croneri.co.uk/" + href
                else:
                    abs_url = href
                self.current_href = abs_url
                self.current_text = []

    def handle_endtag(self, tag):
        if tag == 'a' and hasattr(self, 'current_href'):
            text = " ".join("".join(self.current_text).split())
            self.links[self.current_href] = text
            del self.current_href
            del self.current_text

    def handle_data(self, data):
        if hasattr(self, 'current_href'):
            self.current_text.append(data)

def extract_quick_links(html_path):
    if not os.path.exists(html_path):
        print(f"Warning: HTML file not found at {html_path}")
        return {}
    with open(html_path, 'r', encoding='utf-8') as f:
        content = f.read()
    parser = QuickLinksHrefExtractor()
    parser.feed(content)
    return parser.links

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

def build_report_data(df_raw, target_links, include_queries=True):
    """Filters GSC data for target links and aggregates metrics."""
    target_urls_lower = {url.lower(): (url, title) for url, title in target_links.items()}
    df_raw_norm = df_raw.copy()
    df_raw_norm['page_lower'] = df_raw_norm['page'].str.lower().str.rstrip('/')
    
    df_matched = df_raw_norm[df_raw_norm['page_lower'].isin(target_urls_lower.keys())].copy()
    if df_matched.empty:
        return pd.DataFrame(), pd.DataFrame(), {}
        
    df_matched['original_url'] = df_matched['page_lower'].map(lambda x: target_urls_lower[x][0])
    df_matched['title'] = df_matched['page_lower'].map(lambda x: target_urls_lower[x][1])
    
    if include_queries:
        df_pages = df_matched.groupby(['original_url', 'title']).agg(
            clicks=('clicks', 'sum'),
            impressions=('impressions', 'sum'),
            unique_queries=('query', 'nunique')
        ).reset_index()
        weighted_pos = df_matched.groupby(['original_url', 'title']).apply(
            lambda g: (g['position'] * g['impressions']).sum() / g['impressions'].sum() if g['impressions'].sum() > 0 else g['position'].mean()
        ).reset_index(name='position')
        df_pages = df_pages.merge(weighted_pos, on=['original_url', 'title'])
    else:
        df_pages = df_matched.groupby(['original_url', 'title']).agg(
            clicks=('clicks', 'sum'),
            impressions=('impressions', 'sum'),
            position=('position', 'mean')
        ).reset_index()
        df_pages['unique_queries'] = 0
        
    df_pages['ctr'] = df_pages['clicks'] / df_pages['impressions']
    df_pages = df_pages.sort_values(by='clicks', ascending=False)
    
    df_queries_sorted = df_matched.sort_values(by=['original_url', 'clicks'], ascending=[True, False]) if include_queries else pd.DataFrame()
    
    stats = {
        'total_links': len(target_links),
        'active_links': len(df_pages),
        'clicks': int(df_pages['clicks'].sum()),
        'impressions': int(df_pages['impressions'].sum()),
        'ctr': float(df_pages['clicks'].sum() / df_pages['impressions'].sum()) if df_pages['impressions'].sum() > 0 else 0.0
    }
    return df_pages, df_queries_sorted, stats

def generate_html_file(df_pages, df_queries, stats, start_date, end_date, site_url, report_title, active_page, include_queries=True):
    """Renders the HTML report dashboard for Quick Links."""
    table_rows = []
    slug = get_filename_slug(site_url)
    
    for i, row in df_pages.iterrows():
        url = row['original_url']
        title = row['title']
        clicks = int(row['clicks'])
        impressions = int(row['impressions'])
        ctr = float(row['ctr'])
        position = float(row['position'])
        unique_queries = int(row['unique_queries'])
        
        sub_table_html = ""
        queries_str_attr = ""
        collapse_id = f"collapse-link-{i}"
        
        if include_queries:
            page_queries = df_queries[df_queries['original_url'] == url].head(5)
            queries_list = page_queries['query'].tolist()
            queries_str_attr = html.escape(", ".join(queries_list))
            
            sub_table_body = ""
            for _, q_row in page_queries.iterrows():
                sub_table_body += f"""
                    <tr>
                        <td><code>{html.escape(q_row['query'])}</code></td>
                        <td class="text-end">{int(q_row['clicks']):,}</td>
                        <td class="text-end">{int(q_row['impressions']):,}</td>
                        <td class="text-end">{float(q_row['ctr']):.2%}</td>
                        <td class="text-end">{float(q_row['position']):.2f}</td>
                    </tr>"""
            sub_table_html = f"""
            <tr class="collapse-row">
                <td colspan="8" class="p-0 border-0">
                    <div id="{collapse_id}" class="collapse">
                        <div class="p-3 bg-light border-start border-primary border-4">
                            <div class="d-flex align-items-center mb-2">
                                <h6 class="mb-0 text-primary fw-bold">Top Queries driving traffic:</h6>
                            </div>
                            <table class="table table-sm table-bordered mt-2 mb-0">
                                <thead class="table-secondary">
                                    <tr><th>Search Query</th><th class="text-end" style="width: 120px;">Clicks</th><th class="text-end" style="width: 150px;">Impressions</th><th class="text-end" style="width: 100px;">CTR</th><th class="text-end" style="width: 100px;">Avg. Position</th></tr>
                                </thead>
                                <tbody>{sub_table_body}</tbody>
                            </table>
                        </div>
                    </div>
                </td>
            </tr>"""

        row_click_attr = f'data-bs-toggle="collapse" data-bs-target="#{collapse_id}" style="cursor: pointer;" data-queries="{queries_str_attr}" data-collapse-target="{collapse_id}"' if include_queries else ''
        row_class = "main-row" if include_queries else ""
        
        row_html = f"""
        <tr class="{row_class}" {row_click_attr}>
            <td class="text-center fw-bold">{i + 1}</td>
            <td>
                <span class="fw-semibold text-dark">{html.escape(title)}</span>
                <div class="text-muted" style="font-size: 0.82rem;">
                    <a href="{url}" target="_blank" onclick="event.stopPropagation();">{html.escape(url)}</a>
                </div>
            </td>
            <td class="text-end fw-bold">{clicks:,}</td>
            <td class="text-end">{impressions:,}</td>
            <td class="text-end">{ctr:.2%}</td>
            <td class="text-end">{position:.2f}</td>
            {f'<td class="text-end">{unique_queries:,}</td><td class="text-center"><button class="btn btn-xs btn-outline-primary py-0 px-2" style="font-size: 0.75rem;">Show Queries</button></td>' if include_queries else ''}
        </tr>
        {sub_table_html}
        """
        table_rows.append(row_html)
        
    table_rows_html = "\n".join(table_rows)
    nav_html = get_navbar(slug, start_date, end_date, active_page)
    
    html_content = f"""<!DOCTYPE html>
<html lang="en-GB">
<head>
    <meta charset="UTF-8"><title>{html.escape(report_title)}</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body {{ background-color: #f4f6f9; color: #1f2937; font-family: 'Segoe UI', sans-serif; padding-bottom: 4rem; }}
        .hero-section {{ background: linear-gradient(135deg, #1e3a8a, #0f172a); padding: 3rem 1.5rem; margin-bottom: 2.5rem; border-radius: 0 0 24px 24px; box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1); }}
        .hero-section h1 {{ color: #ffffff !important; }}
        .hero-section p {{ color: rgba(255, 255, 255, 0.7) !important; }}
        h1, h2, h3, h4 {{ font-weight: 700; color: #111827; }}
        .metric-card {{ background-color: #ffffff; border: none; border-radius: 16px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05); }}
        .collapse-row td {{ background-color: #fcfcfc; }}
        .btn-xs {{ padding: 1px 5px; font-size: 0.75rem; }}
        .table-responsive {{ border-radius: 12px; overflow: hidden; box-shadow: 0 4px 12px rgba(0,0,0,0.05); background-color: #fff; }}
        code {{ color: #db2777; background-color: #f3f4f6; padding: 0.15rem 0.3rem; border-radius: 4px; font-size: 0.9em; }}
    </style>
</head>
<body>
<div class="hero-section text-center">
    <div class="container-fluid">
        <h1 class="display-5 mb-2">{html.escape(report_title)}</h1>
        <p class="lead text-muted">Property: <strong>{html.escape(site_url)}</strong> | Reporting Period: <strong>{start_date} to {end_date}</strong></p>
    </div>
</div>
<div class="container-fluid px-4">
    {nav_html}
    <div class="row g-4 mb-4">
        <div class="col-md-3"><div class="card metric-card p-4 text-center"><small class="text-muted d-block text-uppercase fw-bold mb-1">Total Quick Links</small><span class="h2 fw-bold text-primary">{stats['total_links']:,}</span></div></div>
        <div class="col-md-2"><div class="card metric-card p-4 text-center"><small class="text-muted d-block text-uppercase fw-bold mb-1">Active Links</small><span class="h2 fw-bold text-dark">{stats['active_links']:,}</span></div></div>
        <div class="col-md-2"><div class="card metric-card p-4 text-center"><small class="text-muted d-block text-uppercase fw-bold mb-1">Cumulative Clicks</small><span class="h2 fw-bold text-success">{stats['clicks']:,}</span></div></div>
        <div class="col-md-3"><div class="card metric-card p-4 text-center"><small class="text-muted d-block text-uppercase fw-bold mb-1">Cumulative Impressions</small><span class="h2 fw-bold text-info">{stats['impressions']:,}</span></div></div>
        <div class="col-md-2"><div class="card metric-card p-4 text-center"><small class="text-muted d-block text-uppercase fw-bold mb-1">Average CTR</small><span class="h2 fw-bold text-warning">{stats['ctr']:.2%}</span></div></div>
    </div>
    <div class="card metric-card mb-4 p-4 border-start border-primary border-4">
        <h4 class="fw-bold mb-2">💡 Quick Links Analysis Mode</h4>
        <p class="text-secondary mb-0">
            { 'This report displays GSC keyword-level data. Low-volume query thresholds apply.' if include_queries else 'This report displays unfiltered GSC page-level data. These represent the true clicks and impressions totals.' }
        </p>
    </div>
    <div class="d-flex align-items-center justify-content-between mb-3 mt-5">
        <div>
            <h4 class="fw-bold text-dark mb-1">Quick Links Performance Overview</h4>
            <p class="text-muted mb-0">Sorted by organic clicks. { 'Click any row to view queries.' if include_queries else '' }</p>
        </div>
        <div style="width: 350px;">
            <input type="text" id="pageSearch" class="form-control" placeholder="Search topics...">
        </div>
    </div>
    <div class="table-responsive mb-5">
        <table id="quickLinksTable" class="table table-hover align-middle mb-0">
            <thead class="table-dark">
                <tr>
                    <th class="text-center" style="width: 60px;">Rank</th><th>Quick Link Topic &amp; URL</th>
                    <th class="text-end" style="width: 120px;">Clicks</th><th class="text-end" style="width: 150px;">Impressions</th>
                    <th class="text-end" style="width: 100px;">CTR</th><th class="text-end" style="width: 120px;">Avg. Position</th>
                    { '<th class="text-end" style="width: 130px;">Unique Queries</th><th class="text-center" style="width: 120px;">Queries</th>' if include_queries else '' }
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
        var rows = document.querySelectorAll('#quickLinksTable tbody .main-row, #quickLinksTable tbody tr:not(.collapse-row)');
        rows.forEach(function(row) {{
            var pageText = row.textContent.toLowerCase();
            row.style.display = pageText.indexOf(filter) > -1 ? '' : 'none';
        }});
    }});
    
    document.querySelectorAll('#quickLinksTable tbody .main-row').forEach(function(row) {{
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
    return html_content

def export_csv(df_pages, df_queries, filepath, include_queries=True):
    csv_rows = []
    for _, row in df_pages.iterrows():
        url = row['original_url']
        row_dict = {
            'quick_link_title': row['title'],
            'quick_link_url': url,
            'clicks': int(row['clicks']),
            'impressions': int(row['impressions']),
            'ctr': float(row['ctr']),
            'position': float(row['position']),
            'unique_queries': int(row['unique_queries']) if include_queries else 0
        }
        
        if include_queries:
            page_queries = df_queries[df_queries['original_url'] == url].head(5)
            for i in range(5):
                q_val, q_clicks = "", ""
                if i < len(page_queries):
                    q_row = page_queries.iloc[i]
                    q_val = q_row['query']
                    q_clicks = int(q_row['clicks'])
                row_dict[f'top_query_{i+1}'] = q_val
                row_dict[f'top_query_{i+1}_clicks'] = q_clicks
        csv_rows.append(row_dict)
    pd.DataFrame(csv_rows).to_csv(filepath, index=False, encoding='utf-8')

def run_reports(service, site_url, start_date, end_date, max_rows=10000):
    slug = get_filename_slug(site_url)
    output_dir = get_output_dir(site_url)
    os.makedirs(output_dir, exist_ok=True)
    
    html_path_source = 'config/library-quick-links.html'
    all_links = extract_quick_links(html_path_source)
    print(f"Extracted {len(all_links)} total quick links from {html_path_source}")
    if not all_links:
        return
        
    highlighted_links = {url: title for url, title in all_links.items() if url in HIGHLIGHTED_URLS}
    for url in HIGHLIGHTED_URLS:
        if url not in highlighted_links:
            slug_title = urlparse(url).path.strip('/').split('/')[-1].replace('-', ' ').title()
            highlighted_links[url] = slug_title
            
    # Fetch both datasets
    print("Retrieving GSC keyword-level data...")
    df_raw_kw = fetch_with_cache(service, site_url, start_date, end_date, ['query', 'page'], max_rows=max_rows)
    print("Retrieving GSC page-only data...")
    df_raw_po = fetch_with_cache(service, site_url, start_date, end_date, ['page'], max_rows=max_rows)
    
    # -------------------------------------------------------------------------
    # HIGHLIGHTED REPORTS
    # -------------------------------------------------------------------------
    # 1. Keywords
    print("\n--- Highlighted Quick Links Report (Keywords) ---")
    df_pages, df_queries, stats = build_report_data(df_raw_kw, highlighted_links, include_queries=True)
    if not df_pages.empty:
        export_csv(df_pages, df_queries, os.path.join(output_dir, f"library-quick-links-highlighted-report-{slug}-{start_date}-to-{end_date}.csv"), include_queries=True)
        html_content = generate_html_file(df_pages, df_queries, stats, start_date, end_date, site_url, "Highlighted Quick Links Performance Report (Keywords)", "ql_hl_kw", include_queries=True)
        with open(os.path.join(output_dir, f"library-quick-links-highlighted-report-{slug}-{start_date}-to-{end_date}.html"), 'w') as f:
            f.write(html_content)
            
    # 2. Page-Only
    print("\n--- Highlighted Quick Links Report (Page-Only) ---")
    df_pages, _, stats = build_report_data(df_raw_po, highlighted_links, include_queries=False)
    if not df_pages.empty:
        export_csv(df_pages, pd.DataFrame(), os.path.join(output_dir, f"library-quick-links-highlighted-page-only-{slug}-{start_date}-to-{end_date}.csv"), include_queries=False)
        html_content = generate_html_file(df_pages, pd.DataFrame(), stats, start_date, end_date, site_url, "Highlighted Quick Links Performance Report (Page-Only)", "ql_hl_po", include_queries=False)
        with open(os.path.join(output_dir, f"library-quick-links-highlighted-page-only-{slug}-{start_date}-to-{end_date}.html"), 'w') as f:
            f.write(html_content)

    # -------------------------------------------------------------------------
    # ALL QUICK LINKS REPORTS
    # -------------------------------------------------------------------------
    # 3. Keywords
    print("\n--- All Quick Links Report (Keywords) ---")
    df_pages, df_queries, stats = build_report_data(df_raw_kw, all_links, include_queries=True)
    if not df_pages.empty:
        export_csv(df_pages, df_queries, os.path.join(output_dir, f"library-quick-links-all-report-{slug}-{start_date}-to-{end_date}.csv"), include_queries=True)
        html_content = generate_html_file(df_pages, df_queries, stats, start_date, end_date, site_url, "All Quick Links Performance Report (Keywords)", "ql_all_kw", include_queries=True)
        with open(os.path.join(output_dir, f"library-quick-links-all-report-{slug}-{start_date}-to-{end_date}.html"), 'w') as f:
            f.write(html_content)
            
    # 4. Page-Only
    print("\n--- All Quick Links Report (Page-Only) ---")
    df_pages, _, stats = build_report_data(df_raw_po, all_links, include_queries=False)
    if not df_pages.empty:
        export_csv(df_pages, pd.DataFrame(), os.path.join(output_dir, f"library-quick-links-all-page-only-{slug}-{start_date}-to-{end_date}.csv"), include_queries=False)
        html_content = generate_html_file(df_pages, pd.DataFrame(), stats, start_date, end_date, site_url, "All Quick Links Performance Report (Page-Only)", "ql_all_po", include_queries=False)
        with open(os.path.join(output_dir, f"library-quick-links-all-page-only-{slug}-{start_date}-to-{end_date}.html"), 'w') as f:
            f.write(html_content)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Run Croner-i Library Quick Links Performance Reports.')
    parser.add_argument('site_url', nargs='?', default='https://library.croneri.co.uk/', help='The library site URL or GSC property.')
    parser.add_argument('--start-date', help='Start date (YYYY-MM-DD).')
    parser.add_argument('--end-date', help='End date (YYYY-MM-DD).')
    parser.add_argument('--last-month', action='store_true', help='Run for the last calendar month.')
    parser.add_argument('--max-rows', type=int, default=20000, help='Maximum GSC rows to fetch.')
    
    args = parser.parse_args()
    service = get_gsc_service()
    if service:
        start_date, end_date = parse_standard_date_args(args, service, args.site_url)
        run_reports(service, args.site_url, start_date, end_date, args.max_rows)
