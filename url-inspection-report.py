"""
Generates a report using the Google Search Console URL Inspection API.

This script can inspect either a single URL or a list of URLs provided in a text file.
It outputs an HTML report containing detailed inspection data for each URL.

Usage:
    # Inspect a single URL
    python url-inspection-report.py --url https://www.example.com/blog/article-a.html

    # Inspect a list of URLs from a file
    python url-inspection-report.py --sites-file my_urls.txt
"""
import os
import argparse
import re
from datetime import datetime
from urllib.parse import urlparse

# Google API client libraries
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.auth import exceptions

# --- Configuration ---
SCOPES = ['https://www.googleapis.com/auth/webmasters.readonly']
CLIENT_SECRET_FILE = 'client_secret.json'
TOKEN_FILE = 'token.json'

def get_gsc_service():
    """Authenticates and returns a Google Search Console service object."""
    creds = None
    if os.path.exists(TOKEN_FILE):
        try:
            creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
        except Exception as e:
            print(f"Could not load credentials from {TOKEN_FILE}. Error: {e}")
            print("Will attempt to re-authenticate.")
            creds = None

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except exceptions.RefreshError as e:
                print(f"Error refreshing token: {e}")
                print("The refresh token is expired or revoked. Deleting it and re-authenticating.")
                if os.path.exists(TOKEN_FILE):
                    os.remove(TOKEN_FILE)
                creds = None
        
        if not creds:
            if not os.path.exists(CLIENT_SECRET_FILE):
                print(f"Error: {CLIENT_SECRET_FILE} not found. Please follow setup instructions in README.md.")
                return None
            
            print("A browser window will open for you to authorize access.")
            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        
        with open(TOKEN_FILE, 'w') as token:
            token.write(creds.to_json())
            print("Authentication successful. Credentials saved.")

    return build('searchconsole', 'v1', credentials=creds)

def get_url_inspection_data(service, site_url, inspect_url):
    """
    Fetches URL inspection data for a given URL.
    The site_url is the GSC property (e.g., https://example.com/)
    The inspect_url is the specific URL to inspect.
    """
    try:
        request = {
            'inspectionUrl': inspect_url,
            'siteUrl': site_url, # The GSC property must be specified here
            'languageCode': 'en-US' # Or 'en-GB' if preferred, API defaults to 'en-US'
        }
        response = service.urlInspection().index().inspect(body=request).execute()
        return response.get('inspectionResult')
    except HttpError as e:
        error_content = e.content.decode('utf-8')
        if "URL_NOT_IN_PROPERTY" in error_content or "Not found" in error_content:
            return {"error": f"URL not found in property: {site_url}"}
        else:
            print(f"HTTP Error inspecting {inspect_url} within property {site_url}: {e}")
            return {"error": f"API Error: {e.resp.status} - {error_content}"}
    except Exception as e:
        print(f"An unexpected error occurred while inspecting {inspect_url}: {e}")
        return {"error": f"Unexpected Error: {e}"}

def parse_url_for_paths(url):
    """
    Parses a URL to extract hostname and path-based filename for output.
    e.g., https://www.example.com/blog/article-a.html -> example.com, blog-article-a
    """
    parsed_url = urlparse(url)
    hostname = parsed_url.netloc
    
    # Remove 'www.' and get a clean hostname
    clean_hostname = hostname.replace('www.', '')

    path_segments = [s for s in parsed_url.path.split('/') if s]
    
    # Remove file extension from the last segment if present
    if path_segments:
        last_segment = path_segments[-1]
        if '.' in last_segment:
            path_segments[-1] = last_segment.rsplit('.', 1)[0]
    
    # Join with hyphens, handle empty path (root URL)
    if path_segments:
        path_filename = "-".join(path_segments)
    else:
        path_filename = "root" # For root URLs like https://example.com/

    return clean_hostname, path_filename

def create_single_url_html_report(inspect_url, inspection_data, output_path):
    """
    Generates an HTML report for a single URL inspection.
    """
    report_title = f"URL Inspection Report for: {inspect_url}"
    
    if inspection_data and inspection_data.get("error"):
        content_html = f"<p>Error inspecting URL: {inspection_data['error']}</p>"
    elif not inspection_data:
        content_html = "<p>No inspection data received for this URL.</p>"
    else:
        # Extract relevant fields (as per earlier discussion)
        index_status = inspection_data.get('indexStatusResult', {})
        resource_issues = inspection_data.get('resourceIssues', []) # This might be detailed in future
        mobile_usability = inspection_data.get('mobileUsability', {})
        rich_results = inspection_data.get('richResults', []) # This might be detailed in future
        
        
        last_crawl_time_raw = index_status.get('lastCrawlTime')
        formatted_last_crawl_time = 'N/A'
        if last_crawl_time_raw and last_crawl_time_raw != 'N/A':
            try:
                # The API returns ISO 8601 format, e.g., "2023-10-27T12:34:56.789Z"
                dt_object = datetime.fromisoformat(last_crawl_time_raw.replace('Z', '+00:00'))
                formatted_last_crawl_time = dt_object.strftime("%Y-%m-%d %H:%M:%S")
            except ValueError:
                formatted_last_crawl_time = last_crawl_time_raw # Keep original if parsing fails

        data_points = {
            "Last Crawl Time": formatted_last_crawl_time,
            "Page Fetch State": index_status.get('pageFetchState', 'N/A'),
            "Robots.txt State": index_status.get('robotsTxtState', 'N/A'),
            "Indexing State": index_status.get('indexingState', 'N/A'),
            "Google Canonical": index_status.get('googleCanonicalUrl', 'N/A'),
            "User Canonical": index_status.get('userCanonical', 'N/A'),
            "In Sitemap": index_status.get('sitemap', 'N/A'),
            "Crawled As": index_status.get('crawledAs', 'N/A'),
            "Coverage State": index_status.get('coverageState', 'N/A'),
            "Verdict": index_status.get('verdict', 'N/A'),
            "Referring URLs": ', '.join(index_status.get('referringUrls', [])), # This is often empty or large
            "Mobile Usability Verdict": mobile_usability.get('verdict', 'N/A'),
            "Mobile Usability Issues": ', '.join([item.get('issueType', 'N/A') for item in mobile_usability.get('issues', [])]),
            "Rich Results Status": ', '.join([item.get('richResultType', 'N/A') + ' - ' + item.get('verdict', 'N/A') for item in rich_results])
        }

        table_rows = ""
        for key, value in data_points.items():
            table_rows += f"""
            <tr>
                <td class="col-md-3"><strong>{key}</strong></td>
                <td class="col-md-9">{value}</td>
            </tr>
            """

        content_html = f"""
        <div class="table-responsive">
            <table class="table table-bordered table-striped">
                <tbody>
                    {table_rows}
                </tbody>
            </table>
        </div>
        """

    html_template = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{report_title}</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body {{ padding-top: 56px; }}
        h1 {{ border-bottom: 2px solid #dee2e6; padding-bottom: .5rem; }}
        .table-responsive {{ margin-top: 20px; }}
    </style>
</head>
<body>
    <header class="navbar navbar-expand-lg navbar-light bg-light border-bottom mb-4 fixed-top">
        <div class="container-fluid">
            <h1 class="h3 mb-0">{report_title}</h1>
        </div>
    </header>
    <main class="container-fluid py-4 flex-grow-1">
        {content_html}
    </main>
    <footer class="footer mt-auto py-3 bg-light">
        <div class="container text-center">
            <span class="text-muted">Report generated on {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</span>
        </div>
    </footer>
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
"""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html_template)
    print(f"Report saved to {output_path}")

def create_list_url_html_report(site_list_name, all_inspection_results, output_path):
    """
    Generates an HTML report for a list of URL inspections, presenting data in a summary table.
    """
    report_title = f"URL Inspection Summary Report for: {site_list_name}"

    table_header = """
    <thead>
        <tr>
            <th>URL</th>
            <th>Verdict</th>
            <th>Indexing State</th>
            <th>Page Fetch State</th>
            <th>Last Crawl Time</th>
            <th>Google Canonical</th>
            <th>Robots.txt State</th>
            <th>Mobile Usability Verdict</th>
        </tr>
    </thead>
    """
    table_rows = ""
    for url, inspection_data in all_inspection_results.items():
        if inspection_data and inspection_data.get("error"):
            table_rows += f"""
            <tr>
                <td><a href="{url}" target="_blank">{url}</a></td>
                <td colspan="7" class="text-danger">{inspection_data['error']}</td>
            </tr>
            """
        elif not inspection_data:
             table_rows += f"""
            <tr>
                <td><a href="{url}" target="_blank">{url}</a></td>
                <td colspan="7" class="text-warning">No inspection data received.</td>
            </tr>
            """
        else:
            index_status = inspection_data.get('indexStatusResult', {})
            mobile_usability = inspection_data.get('mobileUsability', {})
            
            last_crawl_time_raw = index_status.get('lastCrawlTime')
            formatted_last_crawl_time = 'N/A'
            if last_crawl_time_raw and last_crawl_time_raw != 'N/A':
                try:
                    dt_object = datetime.fromisoformat(last_crawl_time_raw.replace('Z', '+00:00'))
                    formatted_last_crawl_time = dt_object.strftime("%Y-%m-%d %H:%M:%S")
                except ValueError:
                    formatted_last_crawl_time = last_crawl_time_raw # Keep original if parsing fails
            
            table_rows += f"""
            <tr>
                <td><a href="{url}" target="_blank">{url}</a></td>
                <td>{index_status.get('verdict', 'N/A')}</td>
                <td>{index_status.get('indexingState', 'N/A')}</td>
                <td>{index_status.get('pageFetchState', 'N/A')}</td>
                <td>{formatted_last_crawl_time}</td>
                <td>{index_status.get('googleCanonicalUrl', 'N/A')}</td>
                <td>{index_status.get('robotsTxtState', 'N/A')}</td>
                <td>{mobile_usability.get('verdict', 'N/A')}</td>
            </tr>
            """
    
    content_html = f"""
    <div class="table-responsive">
        <table class="table table-bordered table-striped table-hover">
            {table_header}
            <tbody>
                {table_rows}
            </tbody>
        </table>
    </div>
    """

    html_template = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{report_title}</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body {{ padding-top: 56px; }}
        h1 {{ border-bottom: 2px solid #dee2e6; padding-bottom: .5rem; }}
        .table-responsive {{ margin-top: 20px; }}
    </style>
</head>
<body>
    <header class="navbar navbar-expand-lg navbar-light bg-light border-bottom mb-4 fixed-top">
        <div class="container-fluid">
            <h1 class="h3 mb-0">{report_title}</h1>
        </div>
    </header>
    <main class="container-fluid py-4 flex-grow-1">
        {content_html}
    </main>
    <footer class="footer mt-auto py-3 bg-light">
        <div class="container text-center">
            <span class="text-muted">Report generated on {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</span>
        </div>
    </footer>
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
"""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html_template)
    print(f"Summary report saved to {output_path}")

def get_site_url_for_inspection(url):
    """
    Derives the GSC site property URL (e.g., https://example.com/) from a given URL.
    This is necessary for the URL Inspection API's 'siteUrl' parameter.
    """
    parsed = urlparse(url)
    # Reconstruct the base URL (scheme + netloc)
    base_url = f"{parsed.scheme}://{parsed.netloc}"
    # Add trailing slash if it's not a root domain without one
    if not base_url.endswith('/'):
        base_url += '/'
    return base_url

def main():
    parser = argparse.ArgumentParser(
        description='Generate a URL Inspection Report using Google Search Console API.',
        epilog='''Example usage:
  python url-inspection-report.py --url https://www.example.com/blog/article-a.html
  python url-inspection-report.py --sites-file site-lists/my-urls.txt'''
    )
    parser.add_argument('--url', type=str, help='A single URL to inspect.')
    parser.add_argument('--sites-file', type=str, help='Path to a text file containing a list of URLs (one per line) to inspect.')
    
    args = parser.parse_args()

    if not args.url and not args.sites_file:
        parser.error("Either --url or --sites-file must be provided.")

    service = get_gsc_service()
    if not service:
        print("Failed to authenticate with Google Search Console API. Exiting.")
        return

    current_date_str = datetime.now().strftime("%Y-%m-%d")

    if args.url:
        print(f"Inspecting single URL: {args.url}")
        site_url = get_site_url_for_inspection(args.url)
        hostname, path_filename = parse_url_for_paths(args.url)
        
        output_dir = os.path.join('output', hostname)
        output_filename = f"inspection-{path_filename}-{current_date_str}.html"
        output_path = os.path.join(output_dir, output_filename)
        
        inspection_data = get_url_inspection_data(service, site_url, args.url)
        create_single_url_html_report(args.url, inspection_data, output_path)

    elif args.sites_file:
        print(f"Inspecting URLs from file: {args.sites_file}")
        all_inspection_results = {}
        site_list_name = os.path.splitext(os.path.basename(args.sites_file))[0]
        
        
        file_path = args.sites_file
        if not os.path.isabs(file_path):
            file_path = os.path.join('site-lists', file_path)
            
        with open(file_path, 'r', encoding='utf-8') as f:
            urls = [line.strip() for line in f if line.strip() and not line.startswith('#')]

        if not urls:
            print(f"No valid URLs found in {args.sites_file}. Exiting.")
            return

        for url in urls:
            print(f"Inspecting: {url}")
            site_url = get_site_url_for_inspection(url)
            inspection_data = get_url_inspection_data(service, site_url, url)
            all_inspection_results[url] = inspection_data
        
        output_dir = os.path.join('output', 'account') # As per requirement for list output
        output_filename = f"inspection-{site_list_name}-{current_date_str}.html"
        output_path = os.path.join(output_dir, output_filename)
        
        create_list_url_html_report(site_list_name, all_inspection_results, output_path)

if __name__ == '__main__':
    main()
