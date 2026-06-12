"""
Generates an XML sitemap and a discovery summary based on Google Search Console data.
Uses a long date range (default 16 months) to ensure maximum URL discovery.
Refactored for modular GSC Exporter.
"""
import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import pandas as pd
from datetime import datetime
from core.naming import get_output_dir, get_filename_slug
from core.cache import fetch_with_cache, _get_monthly_chunks
from core.date_utils import parse_standard_date_args, get_month_range_lookback

def generate_xml_sitemap(urls):
    """Generates a standard XML sitemap string."""
    xml_header = '<?xml version="1.0" encoding="UTF-8"?>\n'
    xml_header += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    
    xml_body = ""
    for url in urls:
        xml_body += f"  <url>\n    <loc>{url}</loc>\n  </url>\n"
        
    xml_footer = '</urlset>'
    return xml_header + xml_body + xml_footer

def create_html_summary(site_url, start_date, end_date, monthly_stats, total_pages):
    """Generates an HTML summary report of the sitemap generation."""
    rows_html = ""
    for stat in monthly_stats:
        rows_html += f"""
        <tr>
            <td>{stat['month']}</td>
            <td class="text-end">{stat['pages']:,}</td>
            <td class="text-end">{stat['clicks']:,}</td>
            <td class="text-end">{stat['impressions']:,}</td>
        </tr>
        """

    return f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Sitemap Generation Summary - {site_url}</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body {{ padding: 2rem; background-color: #f8f9fa; }}
        .container {{ max-width: 800px; background: white; padding: 2rem; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        h1 {{ border-bottom: 2px solid #dee2e6; padding-bottom: .5rem; margin-bottom: 1.5rem; }}
        footer {{ margin-top: 3rem; text-align: center; color: #6c757d; font-size: 0.9rem; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Sitemap Discovery Summary</h1>
        <p class="lead">{site_url}</p>
        <p class="text-muted">Analysis Period: {start_date} to {end_date}</p>
        
        <div class="alert alert-success">
            <strong>Total Unique URLs Discovered: {total_pages:,}</strong>
        </div>

        <h3 class="mt-4">Monthly Discovery Breakdown</h3>
        <p class="small text-muted">This table shows the number of unique URLs that Google showed in search results for each month.</p>
        <table class="table table-striped table-hover mt-3">
            <thead class="table-dark">
                <tr>
                    <th>Month</th>
                    <th class="text-end">Unique URLs</th>
                    <th class="text-end">Clicks</th>
                    <th class="text-end">Impressions</th>
                </tr>
            </thead>
            <tbody>
                {rows_html}
            </tbody>
        </table>
    </div>
    <footer>
        <p>Report generated on {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}. <a href="https://github.com/liamdelahunty/gsc-exporter" target="_blank">gsc-exporter</a></p>
    </footer>
</body>
</html>
"""

def run_report(service, site_url, start_date, end_date, min_impressions=0):
    """Executes the sitemap generator report."""
    print(f"Generating XML Sitemap for {site_url}...")
    
    # 1. Get Monthly Chunks for analysis
    chunks = _get_monthly_chunks(start_date, end_date)
    monthly_stats = []
    all_pages_set = set()
    
    # 2. Fetch and Analyze month-by-month
    print(f"Analysing discovery across {len(chunks)} months...")
    for chunk_start, chunk_end in chunks:
        s_str = chunk_start.strftime('%Y-%m-%d')
        e_str = chunk_end.strftime('%Y-%m-%d')
        month_name = chunk_start.strftime('%B %Y')
        
        # We use dimensions=['page'] to get unique URLs for the month
        df_month = fetch_with_cache(service, site_url, s_str, e_str, ['page'])
        
        if not df_month.empty:
            if min_impressions > 0:
                df_month = df_month[df_month['impressions'] >= min_impressions]
            
            month_pages = set(df_month['page'].tolist())
            all_pages_set.update(month_pages)
            
            monthly_stats.append({
                'month': month_name,
                'pages': len(month_pages),
                'clicks': int(df_month['clicks'].sum()),
                'impressions': int(df_month['impressions'].sum())
            })
        else:
            monthly_stats.append({
                'month': month_name,
                'pages': 0,
                'clicks': 0,
                'impressions': 0
            })

    if not all_pages_set:
        print("No pages found in the specified date range.")
        return None

    sorted_pages = sorted(list(all_pages_set))
    total_pages = len(sorted_pages)
    print(f"Total unique pages discovered: {total_pages:,}")

    # 3. Output paths
    output_dir = get_output_dir(site_url)
    os.makedirs(output_dir, exist_ok=True)
    slug = get_filename_slug(site_url)
    
    xml_path = os.path.join(output_dir, f"sitemap-{slug}.xml")
    csv_path = os.path.join(output_dir, f"sitemap-urls-{slug}.csv")
    html_path = os.path.join(output_dir, f"sitemap-summary-{slug}.html")

    # 4. Save XML
    xml_content = generate_xml_sitemap(sorted_pages)
    with open(xml_path, 'w', encoding='utf-8') as f:
        f.write(xml_content)
    
    # 5. Save CSV
    pd.DataFrame(sorted_pages, columns=['url']).to_csv(csv_path, index=False)
    
    # 6. Save HTML Summary
    html_content = create_html_summary(site_url, start_date, end_date, monthly_stats, total_pages)
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
        
    print(f"XML Sitemap saved to: {xml_path}")
    print(f"CSV URL list saved to: {csv_path}")
    print(f"HTML Summary saved to: {html_path}")
    return html_path

if __name__ == '__main__':
    import argparse
    from core.client import get_gsc_service
    
    parser = argparse.ArgumentParser(description='Generate an XML sitemap and discovery summary.')
    parser.add_argument('site_url', help='The URL of the site.')
    parser.add_argument('--start-date', help='Start date.')
    parser.add_argument('--end-date', help='End date.')
    parser.add_argument('--lookback-months', type=int, default=16, help='Number of months to look back (default 16).')
    parser.add_argument('--min-impressions', type=int, default=0, help='Minimum impressions to include a URL.')
    parser.add_argument('--last-month', action='store_true', help='Override lookback to use only last month.')
    parser.add_argument('--last-7-days', action='store_true', help='Override lookback to use only last 7 days.')
    
    args = parser.parse_args()
    
    service = get_gsc_service()
    if service:
        if args.start_date or args.last_month or args.last_7_days:
            start_date, end_date = parse_standard_date_args(args, service, args.site_url)
        else:
            from core.date_utils import get_latest_available_date
            latest = get_latest_available_date(service, args.site_url)
            end_date = latest.strftime('%Y-%m-%d')
            start_date, _ = get_month_range_lookback(end_date, args.lookback_months)
            
        run_report(service, args.site_url, start_date, end_date, args.min_impressions)
