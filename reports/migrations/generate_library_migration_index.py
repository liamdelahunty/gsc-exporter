"""
Report script to compile the Croner-i Library to Marketing Migration Index page.
Provides a central portal linking all library migration reports (HTML and CSV formats).
"""
import os
import sys
import argparse
import html
import shutil
from datetime import datetime

# Add parent directory to sys.path to allow importing core
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.naming import get_output_dir, get_filename_slug
from core.client import get_gsc_service
from core.date_utils import parse_standard_date_args

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

def run_report(service, site_url, start_date, end_date):
    print(f"Compiling Library to Marketing Migration Index for {site_url}...")
    
    slug = get_filename_slug(site_url)
    output_dir = get_output_dir(site_url)
    os.makedirs(output_dir, exist_ok=True)
    
    nav_html = get_navbar(slug, start_date, end_date, "index")
    
    # Filenames definitions
    dates = f"{start_date}-to-{end_date}"
    
    reports_list = [
        {
            'name': 'Prioritisation Report (Keywords)',
            'desc': 'Prioritised list of top 100 library pages to migrate, featuring search queries context and SEO disconnect audits (requires GSC privacy query threshold approval).',
            'html': f"library-marketing-migration-prioritisation-report-{slug}-{dates}.html",
            'csv': f"library-marketing-migration-prioritisation-report-{slug}-{dates}.csv"
        },
        {
            'name': 'Prioritisation Report (Page-only)',
            'desc': 'Prioritised list of top 100 library pages featuring unfiltered page-level traffic data (no GSC search query privacy exclusions applied).',
            'html': f"library-marketing-migration-prioritisation-page-only-{slug}-{dates}.html",
            'csv': f"library-marketing-migration-prioritisation-page-only-{slug}-{dates}.csv"
        },
        {
            'name': 'Migration Analysis (Keywords)',
            'desc': 'Interactive table mapping library pages to proposed marketing URLs, featuring expandable search keyword detail drawers.',
            'html': f"library-marketing-migration-analysis-{slug}-{dates}.html",
            'csv': f"library-marketing-migration-analysis-{slug}-{dates}.csv"
        },
        {
            'name': 'Migration Analysis (Page-only)',
            'desc': 'Interactive table mapping library pages to proposed marketing URLs, featuring unfiltered page-level clicks and impressions.',
            'html': f"library-marketing-migration-analysis-page-only-{slug}-{dates}.html",
            'csv': f"library-marketing-migration-analysis-page-only-{slug}-{dates}.csv"
        },
        {
            'name': 'Quick Links Highlighted Report (Keywords)',
            'desc': 'Organic search performance and queries breakdown for the 19 highlighted Quick Links from the product owner.',
            'html': f"library-quick-links-highlighted-report-{slug}-{dates}.html",
            'csv': f"library-quick-links-highlighted-report-{slug}-{dates}.csv"
        },
        {
            'name': 'Quick Links Highlighted (Page-only)',
            'desc': 'True unfiltered page-level clicks and impressions for the 19 highlighted Quick Links.',
            'html': f"library-quick-links-highlighted-page-only-{slug}-{dates}.html",
            'csv': f"library-quick-links-highlighted-page-only-{slug}-{dates}.csv"
        },
        {
            'name': 'Quick Links All Report (Keywords)',
            'desc': 'Organic search performance and queries breakdown for all 190 unique Quick Links found in the topic tree.',
            'html': f"library-quick-links-all-report-{slug}-{dates}.html",
            'csv': f"library-quick-links-all-report-{slug}-{dates}.csv"
        },
        {
            'name': 'Quick Links All (Page-only)',
            'desc': 'True unfiltered page-level clicks and impressions for all 190 unique Quick Links.',
            'html': f"library-quick-links-all-page-only-{slug}-{dates}.html",
            'csv': f"library-quick-links-all-page-only-{slug}-{dates}.csv"
        }
    ]
    
    rows = []
    for r in reports_list:
        html_exists = os.path.exists(os.path.join(output_dir, r['html']))
        csv_exists = os.path.exists(os.path.join(output_dir, r['csv']))
        
        html_link = f'<a href="{r["html"]}" class="btn btn-sm btn-primary">Open HTML</a>' if html_exists else '<span class="badge bg-secondary">Not Generated</span>'
        csv_link = f'<a href="{r["csv"]}" class="btn btn-sm btn-outline-success">Download CSV</a>' if csv_exists else '<span class="badge bg-secondary">Not Generated</span>'
        
        rows.append(f"""
        <tr>
            <td class="fw-bold">{html.escape(r['name'])}</td>
            <td class="text-secondary">{html.escape(r['desc'])}</td>
            <td class="text-center">{html_link}</td>
            <td class="text-center">{csv_link}</td>
        </tr>
        """)
        
    rows_html = "\n".join(rows)
    
    html_content = f"""<!DOCTYPE html>
<html lang="en-GB">
<head>
    <meta charset="UTF-8"><title>Library to Marketing Migration Dashboard</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body {{ background-color: #f4f6f9; color: #1f2937; font-family: 'Segoe UI', sans-serif; padding-bottom: 4rem; }}
        .hero-section {{ background: linear-gradient(135deg, #1e3a8a, #0f172a); padding: 3.5rem 1.5rem; margin-bottom: 2.5rem; border-radius: 0 0 24px 24px; box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1); }}
        .hero-section h1 {{ color: #ffffff !important; }}
        .hero-section p {{ color: rgba(255, 255, 255, 0.7) !important; }}
        h1, h2, h3, h4 {{ font-weight: 700; color: #111827; }}
        .metric-card {{ background-color: #ffffff; border: none; border-radius: 16px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05); }}
        .table-responsive {{ border-radius: 12px; overflow: hidden; box-shadow: 0 4px 12px rgba(0,0,0,0.05); background-color: #fff; }}
    </style>
</head>
<body>
<div class="hero-section text-center">
    <div class="container-fluid">
        <h1 class="display-5 mb-2">Library to Marketing Migration Dashboard</h1>
        <p class="lead text-muted">Property: <strong>{html.escape(site_url)}</strong> | Reporting Period: <strong>{start_date} to {end_date}</strong></p>
    </div>
</div>
<div class="container-fluid px-4">
    {nav_html}
    
    <div class="card metric-card mb-4 p-4 border-start border-primary border-4">
        <h4 class="fw-bold mb-2">🚀 Migration Portal Index</h4>
        <p class="text-secondary mb-0">
            This dashboard indexes all migration prioritisation, keywords mapping, and Quick Links performance analysis reports.
            Choose between **Keywords** reports (to see queries context with GSC privacy limitations) and **Page-Only** reports (to see true unfiltered clicks and impressions).
        </p>
    </div>

    <h2 class="fw-bold text-dark mt-5 mb-3">Available Migration Reports</h2>
    <div class="table-responsive">
        <table class="table table-hover align-middle mb-0">
            <thead class="table-dark">
                <tr>
                    <th style="width: 280px;">Report Name</th>
                    <th>Description</th>
                    <th class="text-center" style="width: 150px;">HTML View</th>
                    <th class="text-center" style="width: 150px;">CSV Export</th>
                </tr>
            </thead>
            <tbody>
                {rows_html}
            </tbody>
        </table>
    </div>
</div>
</body>
</html>"""
    
    dated_index_filename = f"library-migration-index-{slug}-{dates}.html"
    dated_index_path = os.path.join(output_dir, dated_index_filename)
    with open(dated_index_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"Dated Index page generated successfully at: {dated_index_path}")
    
    # Copy to generic filename: library-migration-index.html
    generic_index_path = os.path.join(output_dir, "library-migration-index.html")
    shutil.copyfile(dated_index_path, generic_index_path)
    print(f"Generic Index page updated at: {generic_index_path}")
    
    return dated_index_path

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Generate Library Migration Index.')
    parser.add_argument('site_url', nargs='?', default='https://library.croneri.co.uk/', help='The library site URL or GSC property.')
    parser.add_argument('--start-date', help='Start date (YYYY-MM-DD).')
    parser.add_argument('--end-date', help='End date (YYYY-MM-DD).')
    parser.add_argument('--last-month', action='store_true', help='Run for the last calendar month.')
    
    args = parser.parse_args()
    service = get_gsc_service()
    if service:
        start_date, end_date = parse_standard_date_args(args, service, args.site_url)
        run_report(service, args.site_url, start_date, end_date)
