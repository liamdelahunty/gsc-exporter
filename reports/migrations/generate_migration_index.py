"""
Report script to compile a migration index dashboard linking all migration-related reports.
Explains the purpose, benefits, and local assets for the Drupal to DatoCMS migration.
"""
import os
import sys
import argparse
import html
from datetime import datetime

# Add parent directory to sys.path to allow importing core
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.naming import get_output_dir, get_filename_slug
from core.client import get_gsc_service
from core.date_utils import parse_standard_date_args

def build_index_html(site_url, start_date, end_date, slug):
    """Renders the HTML migration index dashboard linking all assets."""
    # Navigation Links (to be uniform across all reports)
    nav_html = f"""
    <div class="d-flex flex-wrap gap-2 justify-content-center mb-4 pb-3 border-bottom">
        <a href="dato-drupal-index-{slug}-{start_date}-to-{end_date}.html" class="btn btn-primary active px-4">Migration Index</a>
        <a href="drupal-dato-migration-analysis-{slug}-{start_date}-to-{end_date}.html" class="btn btn-outline-primary px-4">Breakdown Dashboard (Query-Level)</a>
        <a href="drupal-dato-migration-page-level-report-{slug}-{start_date}-to-{end_date}.html" class="btn btn-outline-primary px-4">Page-Level Report (All Clicks)</a>
        <a href="drupal-dato-migration-prioritisation-report-{slug}-{start_date}-to-{end_date}.html" class="btn btn-outline-primary px-4">Top 50 Prioritisation Report</a>
        <a href="dato-suggested-urls-alphabetical-{slug}-{start_date}-to-{end_date}.html" class="btn btn-outline-primary px-4">Proposed Dato URLs (Alphabetical)</a>
        <a href="gsc-data-comparison-{slug}-{start_date}-to-{end_date}.html" class="btn btn-outline-primary px-4">GSC Data Comparison</a>
        <a href="dato-pages-performance-report-{slug}-{start_date}-to-{end_date}.html" class="btn btn-outline-primary px-4">Dato Pages Performance</a>
    </div>
    """

    # Report Files Configuration
    reports_config = [
        {
            "id": "breakdown-dashboard",
            "title": "Platform Breakdown Dashboard (Query-Level)",
            "purpose": "Provides a high-level performance comparison between the new DatoCMS platform and the legacy Drupal structure based on Google Search Console queries.",
            "metrics": "Calculates traffic shares (clicks, impressions) and page count distribution to track overall migration progress.",
            "html_file": f"drupal-dato-migration-analysis-{slug}-{start_date}-to-{end_date}.html",
            "csv_file": f"drupal-dato-migration-analysis-{slug}-{start_date}-to-{end_date}.csv",
            "icon": "bi-speedometer2"
        },
        {
            "id": "dato-performance",
            "title": "DatoCMS Pages Performance",
            "purpose": "Provides detailed organic search performance (clicks, impressions, CTR, average position) for all pages migrated to the new DatoCMS platform.",
            "metrics": "Tracks organic landing page performance and lists the top search queries driving traffic to each DatoCMS page.",
            "html_file": f"dato-pages-performance-report-{slug}-{start_date}-to-{end_date}.html",
            "csv_file": f"dato-pages-performance-report-{slug}-{start_date}-to-{end_date}.csv",
            "icon": "bi-graph-up-arrow"
        },
        {
            "id": "prioritisation-report",
            "title": "Top 50 Prioritisation Report",
            "purpose": "Identifies the highest-performing legacy Drupal pages that must be migrated and redirected next to prevent organic traffic loss.",
            "metrics": "Aggregates CTR, average position, and unique queries, demonstrating that migrating just these top 50 pages secures over 68% of remaining Drupal traffic.",
            "html_file": f"drupal-dato-migration-prioritisation-report-{slug}-{start_date}-to-{end_date}.html",
            "csv_file": None,
            "icon": "bi-list-stars"
        },
        {
            "id": "page-level-report",
            "title": "Page-Level Report (All Clicks)",
            "purpose": "A complete census of all legacy Drupal URLs that have recorded organic search clicks during the selected period.",
            "metrics": "Serves as the master inventory of pages requiring redirection rules, ensuring that long-tail page traffic is retained.",
            "html_file": f"drupal-dato-migration-page-level-report-{slug}-{start_date}-to-{end_date}.html",
            "csv_file": f"drupal-dato-migration-page-level-report-{slug}-{start_date}-to-{end_date}.csv",
            "icon": "bi-file-earmark-spreadsheet"
        },
        {
            "id": "proposed-urls",
            "title": "Proposed Dato URLs (Alphabetical)",
            "purpose": "Lists recommended clean, SEO-friendly target paths on the new DatoCMS platform for our legacy Drupal content.",
            "metrics": "Cleans up old database node paths, avoids directory name collisions, and includes convenient click-to-copy target URLs. Note: These URLs are generated programmatically and must be verified by a human.",
            "html_file": f"dato-suggested-urls-alphabetical-{slug}-{start_date}-to-{end_date}.html",
            "csv_file": None,
            "icon": "bi-link-45deg"
        },
        {
            "id": "gsc-comparison",
            "title": "GSC Data Comparison & Directory Audit",
            "purpose": "Compares unfiltered Page-Level GSC traffic with Query-Level traffic to highlight search clicks lost to GSC's privacy filtering thresholds.",
            "metrics": "Features a directory-level breakdown of traffic by parent path, showing legacy structures versus new target structures with core directory descriptions.",
            "html_file": f"gsc-data-comparison-{slug}-{start_date}-to-{end_date}.html",
            "csv_file": f"gsc-data-comparison-{slug}-{start_date}-to-{end_date}.csv",
            "icon": "bi-arrow-left-right"
        }
    ]

    # Render Report Cards HTML
    report_cards_html = ""
    for r in reports_config:
        # Check if local HTML file exists
        html_exists = os.path.exists(os.path.join(get_output_dir(site_url), r["html_file"]))
        status_badge = '<span class="badge bg-success mb-2">Available</span>' if html_exists else '<span class="badge bg-secondary mb-2">Not Generated</span>'
        
        # Link buttons
        html_link = f'<a href="{r["html_file"]}" class="btn btn-sm btn-primary me-2"><i class="bi bi-eye"></i> View HTML Report</a>' if html_exists else ''
        
        csv_link = ""
        if r["csv_file"]:
            csv_exists = os.path.exists(os.path.join(get_output_dir(site_url), r["csv_file"]))
            if csv_exists:
                csv_link = f'<a href="{r["csv_file"]}" class="btn btn-sm btn-outline-secondary" download><i class="bi bi-download"></i> Download CSV</a>'
        
        report_cards_html += f"""
        <div class="col-md-6 col-lg-4 mb-4">
            <div class="card h-100 report-card p-3">
                <div class="card-body d-flex flex-column">
                    <div class="d-flex justify-content-between align-items-start">
                        <h5 class="card-title fw-bold text-dark mb-1">{html.escape(r["title"])}</h5>
                    </div>
                    {status_badge}
                    <p class="card-text text-muted mb-2" style="font-size: 0.9rem;">{html.escape(r["purpose"])}</p>
                    <p class="card-text text-secondary mb-4" style="font-size: 0.85rem; border-top: 1px dashed #eee; padding-top: 8px;"><strong>Metrics &amp; Scope:</strong> {html.escape(r["metrics"])}</p>
                    <div class="mt-auto pt-2 border-top">
                        {html_link}
                        {csv_link}
                    </div>
                </div>
            </div>
        </div>
        """

    # Compile the final template
    html_content = f"""<!DOCTYPE html>
<html lang="en-GB">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Drupal to DatoCMS Migration Reporting Hub: {html.escape(site_url)}</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css">
    <style>
        body {{
            background-color: #f4f6f9;
            font-family: 'Outfit', 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            color: #333;
            padding-bottom: 4rem;
        }}
        h1, h2, h3, h4 {{
            font-weight: 700;
            color: #2c3e50;
        }}
        .hero-section {{
            background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
            color: #ffffff;
            border-radius: 16px;
            padding: 3rem;
            margin-bottom: 2.5rem;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
        }}
        .benefit-card {{
            background: rgba(255, 255, 255, 0.08);
            border: 1px solid rgba(255, 255, 255, 0.15);
            border-radius: 10px;
            padding: 1.5rem;
            height: 100%;
            backdrop-filter: blur(10px);
        }}
        .report-card {{
            border: none;
            border-radius: 12px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.05);
            background-color: #ffffff;
            transition: transform 0.2s, box-shadow 0.2s;
        }}
        .report-card:hover {{
            transform: translateY(-4px);
            box-shadow: 0 8px 24px rgba(0,0,0,0.08);
        }}
        .folder-badge {{
            font-family: monospace;
            font-size: 0.9rem;
            padding: 0.3rem 0.6rem;
            border-radius: 4px;
        }}
    </style>
</head>
<body>

<div class="container-fluid py-4" style="max-width: 1400px; margin: 0 auto;">
    
    <!-- Hero Header -->
    <div class="hero-section text-center text-md-start">
        <div class="row align-items-center">
            <div class="col-12">
                <h1 class="display-5 fw-bold text-white mb-2">Drupal to DatoCMS Migration</h1>
                <p class="lead mb-4 text-white-50">Property: <strong>{html.escape(site_url)}</strong> | Reporting Period: <strong>{start_date} to {end_date}</strong></p>
                <p class="fs-6 mb-0">Use the reports below to audit legacy Drupal pages, check new DatoCMS traffic distribution, and manage URL redirection strategies to protect organic search equity.</p>
            </div>
        </div>
    </div>

    {nav_html}

    <!-- Core Introduction & Project Context -->
    <div class="row mb-5">
        <div class="col-lg-8">
            <div class="card border-0 shadow-sm p-4 h-100">
                <h3 class="fw-bold mb-3 text-secondary">Migration Overview &amp; Project Context</h3>
                <p>Our primary objective is to salvage legacy Drupal content ahead of the platform's decommissioning. Although this content is several years old, retaining its organic search rankings will enable us to transform these high-performing pages into an active source of inbound leads.</p>
                
                <h5 class="fw-bold mt-4 mb-2 text-dark">Why We Are Migrating:</h5>
                <ul>
                    <li class="mb-2"><strong>SEO Equity Retention:</strong> Over the years, our Drupal site has built substantial authority in HR and employment law. By creating direct mappings and automated redirect configurations, we protect our established search rankings and user traffic.</li>
                    <li class="mb-2"><strong>Platform Modernisation:</strong> Moving away from legacy monoliths allows us to separate structural content administration (DatoCMS) from fast, secure web rendering.</li>
                    <li class="mb-2"><strong>Clean Architecture:</strong> We are transforming old database index paths (such as raw node pages) into structured, readable paths. This helps search engine crawlers index our pages more efficiently.</li>
                </ul>

                <div class="alert alert-warning mt-4 mb-0" role="alert">
                    <i class="bi bi-exclamation-triangle-fill me-2"></i>
                    <strong>Please Note:</strong> Proposed target URLs across these reports are generated programmatically and must be manually checked and verified by a human before final redirection rules are implemented.
                </div>
            </div>
        </div>
        
        <div class="col-lg-4">
            <div class="card border-0 shadow-sm p-4 h-100 bg-white">
                <h3 class="fw-bold mb-3 text-secondary">New Dato Directory Taxonomy</h3>
                <p class="text-muted" style="font-size: 0.9rem;">The migration shifts content into structured directories, each representing a clear purpose:</p>
                
                <div class="d-flex flex-column gap-3">
                    <div class="p-2 bg-light rounded border-start border-success border-3">
                        <span class="badge bg-success mb-1">DatoCMS Directory</span>
                        <div class="fw-bold"><code>/features/</code></div>
                        <small class="text-muted">News, webinars, commentaries, and HR developments.</small>
                    </div>
                    <div class="p-2 bg-light rounded border-start border-success border-3">
                        <span class="badge bg-success mb-1">DatoCMS Directory</span>
                        <div class="fw-bold"><code>/guides/</code></div>
                        <small class="text-muted">Employment law handbooks and comprehensive guides.</small>
                    </div>
                    <div class="p-2 bg-light rounded border-start border-success border-3">
                        <span class="badge bg-success mb-1">DatoCMS Directory</span>
                        <div class="fw-bold"><code>/resources/</code></div>
                        <small class="text-muted">Downloadable files, contract templates, and payslips.</small>
                    </div>
                    <div class="p-2 bg-light rounded border-start border-success border-3">
                        <span class="badge bg-success mb-1">DatoCMS Directory</span>
                        <div class="fw-bold"><code>/policies/</code></div>
                        <small class="text-muted">Standard company policies and employee handbooks.</small>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <!-- Interactive Report Registry -->
    <h3 class="fw-bold mb-4 text-secondary">Local Migration Assets &amp; Reports Registry</h3>
    <div class="row">
        {report_cards_html}
    </div>

</div>

</body>
</html>
"""
    return html_content

def run_report(service, site_url, start_date, end_date):
    """Generates the Migration Index dashboard file."""
    print(f"Compiling Drupal to DatoCMS Migration Index for {site_url}...")
    print(f"Period: {start_date} to {end_date}")
    
    slug = get_filename_slug(site_url)
    output_dir = get_output_dir(site_url)
    os.makedirs(output_dir, exist_ok=True)
    
    # Generate path with date slug
    date_path = os.path.join(output_dir, f"dato-drupal-index-{slug}-{start_date}-to-{end_date}.html")
    # Generate generic path
    generic_path = os.path.join(output_dir, "dato-drupal-index.html")
    
    html_content = build_index_html(site_url, start_date, end_date, slug)
    
    # Save the dated version
    with open(date_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
        
    # Save the generic version
    with open(generic_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
        
    print("\n" + "="*60)
    print(f"Migration Index page generated successfully.")
    print(f"Index (Dated):   {date_path}")
    print(f"Index (Generic): {generic_path}")
    print("="*60 + "\n")
    
    return generic_path, date_path

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Compile GSC Drupal to DatoCMS Migration Index.')
    parser.add_argument('site_url', nargs='?', default='https://www.hr-inform.co.uk', help='The site URL or GSC property.')
    parser.add_argument('--start-date', help='Start date (YYYY-MM-DD).')
    parser.add_argument('--end-date', help='End date (YYYY-MM-DD).')
    parser.add_argument('--last-7-days', action='store_true', help='Run for the last 7 available days.')
    parser.add_argument('--last-month', action='store_true', help='Run for the last complete calendar month.')
    
    args = parser.parse_args()
    
    service = get_gsc_service()
    if service:
        start_date, end_date = parse_standard_date_args(args, service, args.site_url)
        run_report(service, args.site_url, start_date, end_date)
