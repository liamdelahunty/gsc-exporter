"""
Generates a report using the Google Search Console URL Inspection API.
Adapted for the modular GSC Exporter.
"""
import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pandas as pd
from datetime import datetime
from urllib.parse import urlparse
from core.naming import get_output_dir, get_filename_slug
from core.date_utils import parse_standard_date_args

def get_url_inspection_data(service, site_url, inspect_url):
    """Fetches URL inspection data for a given URL."""
    try:
        request = {
            'inspectionUrl': inspect_url,
            'siteUrl': site_url,
            'languageCode': 'en-US'
        }
        response = service.urlInspection().index().inspect(body=request).execute()
        return response.get('inspectionResult')
    except Exception as e:
        return {"error": str(e)}

def _format_inspection_data_for_csv(inspect_url, inspection_data, request_timestamp):
    """Flattens raw inspection data into a dictionary for CSV."""
    row = {'Request Timestamp': request_timestamp, 'URL': inspect_url}

    if inspection_data and inspection_data.get("error"):
        row['Error'] = inspection_data['error']
        return row
    elif not inspection_data:
        row['Error'] = 'No inspection data received.'
        return row
    
    index_status = inspection_data.get('indexStatusResult', {})
    mobile_usability = inspection_data.get('mobileUsability', {})
    rich_results = inspection_data.get('richResults', [])

    row.update({
        "Verdict": index_status.get('verdict', 'N/A'),
        "Indexing State": index_status.get('indexingState', 'N/A'),
        "Page Fetch State": index_status.get('pageFetchState', 'N/A'),
        "Last Crawl Time": index_status.get('lastCrawlTime', 'N/A'),
        "Google Canonical": index_status.get('googleCanonicalUrl', 'N/A'),
        "User Canonical": index_status.get('userCanonical', 'N/A'),
        "Robots.txt State": index_status.get('robotsTxtState', 'N/A'),
        "In Sitemap": index_status.get('sitemap', 'N/A'),
        "Crawled As": index_status.get('crawledAs', 'N/A'),
        "Coverage State": index_status.get('coverageState', 'N/A'),
        "Referring URLs": ', '.join(index_status.get('referringUrls', [])),
        "Mobile Usability Verdict": mobile_usability.get('verdict', 'N/A'),
        "Mobile Usability Issues": ', '.join([item.get('issueType', 'N/A') for item in mobile_usability.get('issues', [])]),
        "Rich Results Status": ', '.join([item.get('richResultType', 'N/A') + ' - ' + item.get('verdict', 'N/A') for item in rich_results])
    })
    return row

def create_html_report(df, report_title, timestamp):
    """Generates an HTML report from the DataFrame."""
    table_html = df.to_html(classes="table table-striped table-hover", index=False, border=0)

    return f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{report_title}</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body {{ padding: 2rem; background-color: #f8f9fa; }}
        h1 {{ border-bottom: 2px solid #dee2e6; padding-bottom: .5rem; }}
        .table-responsive {{ margin-top: 2rem; }}
        footer {{ margin-top: 3rem; text-align: center; color: #6c757d; }}
    </style>
</head>
<body>
    <div class="container-fluid">
        <h1>{report_title}</h1>
        <p class="text-muted">Inspection performed on: {timestamp}</p>
        <div class="table-responsive">
            {table_html}
        </div>
    </div>
    <footer>
        <p>Report generated on {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}. <a href="https://github.com/liamdelahunty/gsc-exporter" target="_blank">gsc-exporter</a></p>
    </footer>
</body>
</html>
"""

def run_report(service, site_url, start_date=None, end_date=None, urls=None, site_list_name="report"):
    """Executes the URL inspection report for a list of URLs."""
    if not urls:
        urls = [site_url] if site_url.startswith('http') else []
    
    print(f"Running URL Inspection Report for {len(urls)} URLs on {site_url}...")
    
    request_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    current_date_str = datetime.now().strftime("%Y-%m-%d")
    
    all_inspection_results = {}
    
    for url in urls:
        print(f"Inspecting: {url}")
        # The site_url passed in is the GSC property to use
        inspection_data = get_url_inspection_data(service, site_url, url)
        all_inspection_results[url] = inspection_data
    
    # Paths
    slug = get_filename_slug(site_url)
    output_dir = get_output_dir(site_url)
    os.makedirs(output_dir, exist_ok=True)
    
    base_filename = f"url-inspection-{slug}-{current_date_str}"
    csv_path = os.path.join(output_dir, f"{base_filename}.csv")
    html_path = os.path.join(output_dir, f"{base_filename}.html")
    
    # Save CSV
    formatted_data_list = [_format_inspection_data_for_csv(url, data, request_timestamp) for url, data in all_inspection_results.items()]
    df = pd.DataFrame(formatted_data_list)
    df.to_csv(csv_path, index=False, encoding='utf-8')
    
    # Save HTML
    html_content = create_html_report(
        df,
        f"URL Inspection Report: {site_url}",
        request_timestamp
    )
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(html_content)

    print(f"CSV saved to: {csv_path}")
    print(f"HTML saved to: {html_path}")
    return html_path

if __name__ == '__main__':
    import argparse
    from core.client import get_gsc_service
    
    parser = argparse.ArgumentParser(description='Inspect URLs.')
    parser.add_argument('site_url', help='The GSC property URL.')
    parser.add_argument('--url', help='Single URL to inspect.')
    parser.add_argument('--sites-file', help='File with URLs.')
    parser.add_argument('--start-date', help='Start date (YYYY-MM-DD).')
    parser.add_argument('--end-date', help='End date (YYYY-MM-DD).')
    parser.add_argument('--last-month', action='store_true', help='Run for the last calendar month.')
    
    args = parser.parse_args()
    start_date, end_date = parse_standard_date_args(args)
    
    service = get_gsc_service() 
    
    if service:
        urls = []
        name = "report"
        if args.url:
            urls = [args.url]
            name = "single"
        elif args.sites_file:
            with open(args.sites_file, 'r') as f:
                urls = [line.strip() for line in f if line.strip()]
            name = os.path.splitext(os.path.basename(args.sites_file))[0]
        else:
            urls = [args.site_url] if args.site_url.startswith('http') else []
            name = "site-root"
            
        if urls:
            run_report(service, args.site_url, start_date, end_date, urls, name)
        else:
            print("No URLs provided for inspection.")
