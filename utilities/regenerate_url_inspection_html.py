#!/usr/bin/env python3
"""
Regenerates a highly interactive, premium designed HTML report from a URL inspection CSV file.
Usage:
    .venv/bin/python utilities/regenerate_url_inspection_html.py <csv_path> [output_html_path]
"""
import os
import sys
import json
import argparse
import pandas as pd
from jinja2 import Template

def main():
    parser = argparse.ArgumentParser(description='Regenerate HTML report from URL inspection CSV.')
    parser.add_argument('csv_path', help='Path to the URL inspection CSV file')
    parser.add_argument('output_html', nargs='?', help='Path to write the redesigned HTML report')
    args = parser.parse_args()

    csv_path = os.path.abspath(args.csv_path)
    if not os.path.exists(csv_path):
        print(f"Error: File not found: {csv_path}")
        sys.exit(1)

    print(f"Reading CSV from: {csv_path}")
    try:
        df = pd.read_csv(csv_path)
    except Exception as e:
        print(f"Error reading CSV: {e}")
        sys.exit(1)

    # Clean up df missing values
    df = df.fillna('N/A')

    # Convert dataframe to list of records
    records = []
    for _, row in df.iterrows():
        records.append({
            'timestamp': str(row.get('Request Timestamp', 'N/A')),
            'url': str(row.get('URL', 'N/A')),
            'is_redirect': str(row.get('Is Redirect', 'No')),
            'final_destination_url': str(row.get('Final Destination URL', row.get('URL', 'N/A'))),
            'verdict': str(row.get('Verdict', 'N/A')),
            'indexing_state': str(row.get('Indexing State', 'N/A')),
            'fetch_state': str(row.get('Page Fetch State', 'N/A')),
            'crawl_time': str(row.get('Last Crawl Time', 'N/A')),
            'google_canonical': str(row.get('Google Canonical', 'N/A')),
            'user_canonical': str(row.get('User Canonical', 'N/A')),
            'final_user_canonical': str(row.get('Final User Canonical', row.get('User Canonical', 'N/A'))),
            'final_google_canonical': str(row.get('Final Google Canonical', row.get('Google Canonical', 'N/A'))),
            'canonical_differs_from_destination': str(row.get('Canonical Differs From Destination', 'No')),
            'robots_state': str(row.get('Robots.txt State', 'N/A')),
            'sitemap': str(row.get('In Sitemap', 'N/A')),
            'crawled_as': str(row.get('Crawled As', 'N/A')),
            'coverage_state': str(row.get('Coverage State', 'N/A')),
            'referring_urls': str(row.get('Referring URLs', 'N/A')),
            'mobile_verdict': str(row.get('Mobile Usability Verdict', 'N/A')),
            'mobile_issues': str(row.get('Mobile Usability Issues', 'N/A')),
            'rich_results': str(row.get('Rich Results Status', 'N/A'))
        })

    # Prepare metadata
    first_row_timestamp = df.iloc[0].get('Request Timestamp', 'N/A') if not df.empty else 'N/A'
    
    # Infer site URL from first URL if possible
    site_url = "croner.co.uk"
    if not df.empty and 'URL' in df.columns:
        first_url = df.iloc[0]['URL']
        try:
            from urllib.parse import urlparse
            parsed = urlparse(first_url)
            if parsed.netloc:
                site_url = parsed.netloc
        except Exception:
            pass

    report_title = f"URL Inspection Report: {site_url}"
    
    # Find template
    script_dir = os.path.dirname(os.path.abspath(__file__))
    workspace_dir = os.path.dirname(script_dir)
    template_path = os.path.join(workspace_dir, 'templates', 'url-inspection-template.html')
    
    if not os.path.exists(template_path):
        template_path = os.path.join(os.getcwd(), 'templates', 'url-inspection-template.html')
        
    if not os.path.exists(template_path):
        print(f"Error: Template file not found at: {template_path}")
        sys.exit(1)
        
    print(f"Loading template from: {template_path}")
    with open(template_path, 'r', encoding='utf-8') as tf:
        template_content = tf.read()

    # Render template using Jinja2
    template = Template(template_content)
    rendered_html = template.render(
        report_title=report_title,
        request_timestamp=str(first_row_timestamp),
        data_json=json.dumps(records)
    )

    # Determine output path
    if args.output_html:
        output_path = os.path.abspath(args.output_html)
    else:
        # Default: replace extension of CSV to -redesigned.html or just overwrite .html in output dir
        base, _ = os.path.splitext(csv_path)
        output_path = f"{base}-redesigned.html"

    # Write file
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(rendered_html)

    print(f"Successfully generated redesigned HTML report at:\n{output_path}")

if __name__ == '__main__':
    main()
