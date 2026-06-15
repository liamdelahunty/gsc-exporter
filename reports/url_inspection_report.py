"""
Generates a report using the Google Search Console URL Inspection API.
Adapted for the modular GSC Exporter with intelligent property detection.
"""
import os
import sys
import argparse
import pandas as pd
from datetime import datetime
from urllib.parse import urlparse
from collections import defaultdict

# Add parent directory to sys.path to allow importing core
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.naming import get_output_dir, get_filename_slug
from core.date_utils import parse_standard_date_args
from core.client import get_gsc_service, get_available_properties

def find_best_property(inspect_url, available_properties):
    """
    Finds the best matching GSC property for a given URL.
    Prefers exact URL-prefix matches over domain properties.
    """
    best_match = None
    best_match_len = -1
    
    # Try to find the longest matching URL-prefix property
    for prop in available_properties:
        if prop.startswith('http') and inspect_url.startswith(prop):
            if len(prop) > best_match_len:
                best_match = prop
                best_match_len = len(prop)
                
    if best_match:
        return best_match
    
    # If no URL-prefix match, try to find a matching domain property
    parsed_url = urlparse(inspect_url)
    hostname = parsed_url.hostname
    if not hostname:
        return None
        
    for prop in available_properties:
        if prop.startswith('sc-domain:'):
            domain = prop.replace('sc-domain:', '')
            if hostname == domain or hostname.endswith('.' + domain):
                return prop
                
    return None

def normalize_property(site_url, available_properties):
    """Ensures the site_url matches the exact string registered in GSC (e.g. trailing slashes)."""
    if site_url in available_properties:
        return site_url
    
    # Try adding/removing trailing slash
    if site_url.endswith('/'):
        alt = site_url[:-1]
    else:
        alt = site_url + '/'
        
    if alt in available_properties:
        return alt
        
    # Case insensitive check
    for prop in available_properties:
        if prop.lower() == site_url.lower():
            return prop
            
    return site_url

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

def run_report(service, site_url, urls, site_list_name="report"):
    """Executes the URL inspection report for a list of URLs."""
    print(f"Running URL Inspection Report for {len(urls)} URLs using property: {site_url}")
    
    request_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    current_date_str = datetime.now().strftime("%Y-%m-%d")
    
    all_inspection_results = {}
    
    for url in urls:
        print(f"Inspecting: {url}")
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
    parser = argparse.ArgumentParser(description='Inspect URLs.')
    parser.add_argument('site_url_or_prop', nargs='?', help='GSC property OR a specific URL to inspect.')
    parser.add_argument('--url', help='Single URL to inspect (if first arg is the property).')
    parser.add_argument('--sites-file', help='File with a list of URLs to inspect.')
    
    # Standard boilerplate for modular reports
    parser.add_argument('--start-date', help='Ignored for this report.')
    parser.add_argument('--end-date', help='Ignored for this report.')
    parser.add_argument('--last-7-days', action='store_true', help='Ignored for this report.')
    parser.add_argument('--last-month', action='store_true', help='Ignored for this report.')
    
    args = parser.parse_args()
    
    service = get_gsc_service()
    if not service:
        sys.exit(1)
        
    available_properties = get_available_properties(service)
    
    # CASE 1: Batch processing from file
    if args.sites_file:
        if not os.path.exists(args.sites_file):
            print(f"Error: File not found: {args.sites_file}")
            sys.exit(1)
            
        with open(args.sites_file, 'r') as f:
            raw_urls = [line.strip() for line in f if line.strip()]
            
        if args.site_url_or_prop:
            # Force all URLs in file to use the provided property
            site_url = normalize_property(args.site_url_or_prop, available_properties)
            run_report(service, site_url, raw_urls)
        else:
            # INTELLIGENT BATCH: Group URLs by their best property
            groups = defaultdict(list)
            for url in raw_urls:
                prop = find_best_property(url, available_properties)
                if prop:
                    groups[prop].append(url)
                else:
                    print(f"Warning: Could not find an authorized GSC property for '{url}'. Skipping.")
            
            if not groups:
                print("Error: No URLs in the file could be matched to an authorized property.")
                sys.exit(1)
                
            for prop, urls in groups.items():
                run_report(service, prop, urls)

    # CASE 2: Single URL or Property provided via positional arg or --url
    elif args.site_url_or_prop:
        # User provided --url explicitly
        if args.url:
            site_url = normalize_property(args.site_url_or_prop, available_properties)
            run_report(service, site_url, [args.url])
        else:
            # INTELLIGENT SINGLE: First arg is either a property or a specific URL
            prop = normalize_property(args.site_url_or_prop, available_properties)
            if prop in available_properties:
                # It's a property. Inspect its root (if it's a URL-prefix property).
                if prop.startswith('http'):
                    run_report(service, prop, [prop])
                else:
                    print(f"Property '{prop}' is a domain property. Please provide a specific --url to inspect.")
            else:
                # It's not a property. Assume it's an inspection URL.
                best_prop = find_best_property(args.site_url_or_prop, available_properties)
                if best_prop:
                    print(f"Intelligently detected property '{best_prop}' for URL '{args.site_url_or_prop}'")
                    run_report(service, best_prop, [args.site_url_or_prop])
                else:
                    print(f"Error: Could not find an authorized GSC property for '{args.site_url_or_prop}'")
                    sys.exit(1)
    else:
        parser.print_help()
        sys.exit(1)
