"""
Exports all pages from a Google Search Console property to a CSV and an HTML file.
Refactored for modular GSC Exporter.
"""
import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import pandas as pd
import math
from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta
from core.naming import get_output_dir, get_filename_slug
from core.cache import fetch_with_cache
from core.date_utils import parse_standard_date_args

NUM_COLUMNS = 3

def create_html_page(urls, page_title, num_columns, start_date, end_date, num_links):
    """Generates an HTML page with links arranged in columns."""
    footer_style = 'footer{margin-top:2rem;padding-top:1rem;border-top:1px solid #dee2e6;text-align:center;font-size:0.9rem;color:#6c757d;}'
    html_parts = [
        f'<!DOCTYPE html>\n<html lang="en">\n<head>\n<meta charset="UTF-8">\n<meta name="viewport" content="width=device-width, initial-scale=1.0">\n<title>{page_title}</title>',
        '<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">',
        f'<style>body{{padding:20px;}}.list-group-item a{{text-decoration:none;word-break:break-all;}}.list-group-item:hover{{background-color:#f8f9fa;}}{footer_style}</style>',
        f'</head>\n<body>\n<div class="container-fluid">\n<h1 class="mb-4">{page_title}</h1>\n'
        f'<p class="text-muted">Analysis for the period: {start_date} to {end_date}</p>\n'
        f'<h3 class="mb-4">Total Links: {num_links:,}</h3>\n'
        f'<div class="row">\n'
    ]
    
    items_per_column = math.ceil(len(urls) / num_columns)
    url_chunks = [urls[i:i + items_per_column] for i in range(0, len(urls), items_per_column)]

    for chunk in url_chunks:
        html_parts.append(f'<div class="col-md-{12 // num_columns}">')
        html_parts.append('<ul class="list-group">\n')
        for url in chunk:
            url_str = str(url).strip()
            html_parts.append(f'<li class="list-group-item"><a href="{url_str}" target="_blank">{url_str}</a></li>\n')
        html_parts.append('</ul>\n')
        html_parts.append('</div>')

    html_parts.extend(['</div></div><footer><p><a href="https://github.com/liamdelahunty/gsc-exporter" target="_blank">gsc-exporter</a></p></footer></body></html>'])
    return "".join(html_parts)

def run_report(service, site_url, start_date, end_date):
    """Executes the pages exporter report."""
    print(f"Running GSC Pages Exporter for {site_url}...")
    
    # 2. Fetch Data
    # Dimensions: page
    df = fetch_with_cache(service, site_url, start_date, end_date, ['page'])
    
    if df.empty:
        print("No pages found.")
        return None

    pages = sorted(df['page'].tolist())
    num_links = len(pages)
    print(f"Total unique pages found: {num_links:,}")

    # 3. Output Paths
    output_dir = get_output_dir(site_url)
    os.makedirs(output_dir, exist_ok=True)
    slug = get_filename_slug(site_url)
    
    file_prefix = f"gsc-pages-{slug}-{start_date}-to-{end_date}"
    csv_path = os.path.join(output_dir, f"{file_prefix}.csv")
    html_path = os.path.join(output_dir, f"{file_prefix}.html")

    # 4. Save and Generate
    df[['page']].to_csv(csv_path, index=False, encoding='utf-8')
    
    html_content = create_html_page(pages, f"Google Organic Pages for {slug}", NUM_COLUMNS, start_date, end_date, num_links)
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
        
    print(f"CSV saved to: {csv_path}")
    print(f"HTML saved to: {html_path}")
    return html_path

if __name__ == '__main__':
    import argparse
    from core.client import get_gsc_service
    
    parser = argparse.ArgumentParser(description='Export GSC pages.')
    parser.add_argument('site_url', help='The URL of the site.')
    parser.add_argument('--start-date', help='Start date.')
    parser.add_argument('--end-date', help='End date.')
    parser.add_argument('--last-month', action='store_true', help='Run for the last calendar month.')
    
    args = parser.parse_args()
    start_date, end_date = parse_standard_date_args(args)

    service = get_gsc_service()
    if service:
        run_report(service, args.site_url, start_date, end_date)
