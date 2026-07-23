"""
Audits HTTP status codes, response times, redirect chains, and server responses for a list of URLs.
Support for batch file input, multi-threaded requests, CSV generation, and interactive HTML dashboards.
"""
import os
import sys
import json
import argparse
import time
import pandas as pd
from datetime import datetime
from urllib.parse import urlparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import httpx
from jinja2 import Environment, FileSystemLoader

# Add parent directory to sys.path to allow importing core
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.naming import get_output_dir, get_filename_slug

DEFAULT_USER_AGENT = "Mozilla/5.0 (compatible; GSCExporterHTTPChecker/1.0; +https://github.com/liamdelahunty/gsc-exporter)"

import re

def extract_canonical_from_html(html_text):
    """Extracts the href from <link rel="canonical" href="..."> in HTML text."""
    if not html_text:
        return "None detected"
    match = re.search(r'<link\s+[^>]*rel=["\']canonical["\'][^>]*href=["\']([^"\']+)["\']', html_text, re.IGNORECASE)
    if not match:
        match = re.search(r'<link\s+[^>]*href=["\']([^"\']+)["\'][^>]*rel=["\']canonical["\']', html_text, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return "None detected"

def check_single_url(url, timeout=10.0, follow_redirects=True, user_agent=DEFAULT_USER_AGENT):
    """
    Performs an HTTP request for a single URL and returns detailed status information.
    """
    headers = {"User-Agent": user_agent}
    start_time = time.time()
    
    # Ensure scheme is present
    fetch_url = url.strip()
    if not fetch_url.startswith(('http://', 'https://')):
        fetch_url = 'https://' + fetch_url

    try:
        with httpx.Client(timeout=timeout, follow_redirects=follow_redirects) as client:
            response = client.get(fetch_url, headers=headers)
            elapsed_ms = int((time.time() - start_time) * 1000)
            
            # Format redirect chain if redirects occurred
            chain_parts = []
            if response.history:
                for resp in response.history:
                    chain_parts.append(f"{resp.url} ({resp.status_code})")
                chain_parts.append(f"{response.url} ({response.status_code})")
            
            redirect_chain = " -> ".join(chain_parts) if chain_parts else ""
            
            final_url_str = str(response.url)
            is_redirect = bool(response.history) or (final_url_str.rstrip('/') != fetch_url.rstrip('/'))
            
            content_type = response.headers.get("content-type", "")
            extracted_canonical = "None detected"
            if "html" in content_type.lower() and response.text:
                extracted_canonical = extract_canonical_from_html(response.text)
                
            canonical_differs = "No"
            if extracted_canonical not in ("None detected", "N/A", ""):
                if extracted_canonical.rstrip('/') != final_url_str.rstrip('/'):
                    canonical_differs = "Yes"

            return {
                "URL": url,
                "Is Redirect": "Yes" if is_redirect else "No",
                "Status Code": response.status_code,
                "Status Reason": response.reason_phrase,
                "Response Time (ms)": elapsed_ms,
                "Final URL": final_url_str,
                "Extracted Canonical": extracted_canonical,
                "Canonical Differs From Destination": canonical_differs,
                "Redirect Count": len(response.history),
                "Redirect Chain": redirect_chain,
                "Content Type": content_type if content_type else "N/A",
                "Error": ""
            }
    except httpx.TimeoutException:
        elapsed_ms = int((time.time() - start_time) * 1000)
        return {
            "URL": url,
            "Is Redirect": "No",
            "Status Code": 0,
            "Status Reason": "Connection Timeout",
            "Response Time (ms)": elapsed_ms,
            "Final URL": fetch_url,
            "Extracted Canonical": "N/A",
            "Canonical Differs From Destination": "No",
            "Redirect Count": 0,
            "Redirect Chain": "",
            "Content Type": "N/A",
            "Error": f"Timeout after {timeout} seconds"
        }
    except Exception as e:
        elapsed_ms = int((time.time() - start_time) * 1000)
        return {
            "URL": url,
            "Is Redirect": "No",
            "Status Code": 0,
            "Status Reason": "Request Error",
            "Response Time (ms)": elapsed_ms,
            "Final URL": fetch_url,
            "Extracted Canonical": "N/A",
            "Canonical Differs From Destination": "No",
            "Redirect Count": 0,
            "Redirect Chain": "",
            "Content Type": "N/A",
            "Error": str(e)
        }

def load_urls_from_file(file_path):
    """Loads URLs from a text file or CSV file."""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")
        
    ext = os.path.splitext(file_path)[1].lower()
    if ext == '.csv':
        df = pd.read_csv(file_path)
        for col in ['url', 'URL', 'page', 'Page', 'loc', 'Loc']:
            if col in df.columns:
                return [str(u).strip() for u in df[col].dropna() if str(u).strip()]
        return [str(u).strip() for u in df.iloc[:, 0].dropna() if str(u).strip()]
    else:
        with open(file_path, 'r', encoding='utf-8') as f:
            return [line.strip() for line in f if line.strip() and not line.strip().startswith('#')]

def create_html_report(df, report_title, timestamp):
    """Generates an HTML report from DataFrame using Jinja2 template."""
    df_clean = df.fillna('N/A')
    
    records = []
    for _, row in df_clean.iterrows():
        records.append({
            'url': str(row.get('URL', '')),
            'is_redirect': str(row.get('Is Redirect', 'No')),
            'status_code': str(row.get('Status Code', '0')),
            'status_reason': str(row.get('Status Reason', 'N/A')),
            'response_time_ms': str(row.get('Response Time (ms)', '0')),
            'final_url': str(row.get('Final URL', '')),
            'extracted_canonical': str(row.get('Extracted Canonical', 'None detected')),
            'canonical_differs': str(row.get('Canonical Differs From Destination', 'No')),
            'redirect_count': str(row.get('Redirect Count', '0')),
            'redirect_chain': str(row.get('Redirect Chain', '')),
            'content_type': str(row.get('Content Type', 'N/A')),
            'error': str(row.get('Error', ''))
        })

    # Try workspace templates directory first
    template_loader = FileSystemLoader('templates')
    env = Environment(loader=template_loader)
    template = env.get_template('http-status-template.html')

    return template.render(
        report_title=report_title,
        request_timestamp=timestamp,
        data_json=json.dumps(records)
    )

def run_report(urls, site_url="http-audit", max_workers=20, timeout=10.0, follow_redirects=True, user_agent=DEFAULT_USER_AGENT):
    """Executes the HTTP status checker report for a list of URLs."""
    if isinstance(urls, str):
        urls = [urls]
        
    print(f"Auditing HTTP Status Codes for {len(urls)} URLs (Concurrency: {max_workers})...")
    request_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    current_date_str = datetime.now().strftime("%Y-%m-%d")
    
    results = []
    completed_count = 0
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_url = {
            executor.submit(check_single_url, url, timeout, follow_redirects, user_agent): url 
            for url in urls
        }
        for future in as_completed(future_to_url):
            res = future.result()
            results.append(res)
            completed_count += 1
            if completed_count % 10 == 0 or completed_count == len(urls):
                print(f"Progress: {completed_count}/{len(urls)} URLs audited...")

    # Sort results by original URL list order
    url_order_map = {url: i for i, url in enumerate(urls)}
    results.sort(key=lambda r: url_order_map.get(r['URL'], 999999))
    
    df = pd.DataFrame(results)
    
    # Save CSV and HTML
    slug = get_filename_slug(site_url)
    output_dir = get_output_dir(site_url)
    os.makedirs(output_dir, exist_ok=True)
    
    base_filename = f"http-status-check-{slug}-{current_date_str}"
    csv_path = os.path.join(output_dir, f"{base_filename}.csv")
    html_path = os.path.join(output_dir, f"{base_filename}.html")
    
    df.to_csv(csv_path, index=False, encoding='utf-8')
    
    html_content = create_html_report(df, f"HTTP Status Audit: {site_url}", request_timestamp)
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
        
    print(f"\nCSV Report saved to: {csv_path}")
    print(f"HTML Report saved to: {html_path}")
    print(f"file://{os.path.abspath(csv_path)}")
    print(f"file://{os.path.abspath(html_path)}")
    return html_path

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Audit HTTP status codes for a list of URLs.')
    parser.add_argument('site_url_or_prop', nargs='?', help='GSC property OR a specific URL to check.')
    parser.add_argument('--url', help='Single URL or comma-separated URLs to inspect.')
    parser.add_argument('--sites-file', '--file', dest='sites_file', help='Path to text or CSV file containing URLs.')
    parser.add_argument('--max-workers', type=int, default=20, help='Maximum concurrent HTTP requests (default 20).')
    parser.add_argument('--timeout', type=float, default=10.0, help='Timeout per request in seconds (default 10.0).')
    parser.add_argument('--no-follow-redirects', action='store_true', help='Disable following HTTP redirects.')
    parser.add_argument('--user-agent', default=DEFAULT_USER_AGENT, help='Custom User-Agent string.')
    
    # Standard boilerplate for modular reports
    parser.add_argument('--start-date', help='Ignored for this report.')
    parser.add_argument('--end-date', help='Ignored for this report.')
    parser.add_argument('--last-7-days', action='store_true', help='Ignored for this report.')
    parser.add_argument('--last-month', action='store_true', help='Ignored for this report.')
    
    args = parser.parse_args()
    
    urls_to_check = []
    site_namespace = "http-audit"
    
    if args.sites_file:
        urls_to_check = load_urls_from_file(args.sites_file)
        if args.site_url_or_prop:
            site_namespace = args.site_url_or_prop
        elif urls_to_check:
            # Infer site namespace from first URL
            parsed = urlparse(urls_to_check[0] if urls_to_check[0].startswith('http') else 'https://' + urls_to_check[0])
            if parsed.netloc:
                site_namespace = parsed.netloc
    elif args.url:
        urls_to_check = [u.strip() for u in args.url.split(',') if u.strip()]
        if args.site_url_or_prop:
            site_namespace = args.site_url_or_prop
        elif urls_to_check:
            parsed = urlparse(urls_to_check[0] if urls_to_check[0].startswith('http') else 'https://' + urls_to_check[0])
            if parsed.netloc:
                site_namespace = parsed.netloc
    elif args.site_url_or_prop:
        if args.site_url_or_prop.startswith(('http://', 'https://')):
            urls_to_check = [args.site_url_or_prop]
            parsed = urlparse(args.site_url_or_prop)
            if parsed.netloc:
                site_namespace = parsed.netloc
        else:
            site_namespace = args.site_url_or_prop
            print(f"Property or domain '{args.site_url_or_prop}' specified. Please provide --sites-file or --url to audit.")
            sys.exit(1)
    else:
        parser.print_help()
        sys.exit(1)
        
    if not urls_to_check:
        print("Error: No valid URLs provided to audit.")
        sys.exit(1)
        
    run_report(
        urls=urls_to_check,
        site_url=site_namespace,
        max_workers=args.max_workers,
        timeout=args.timeout,
        follow_redirects=not args.no_follow_redirects,
        user_agent=args.user_agent
    )
