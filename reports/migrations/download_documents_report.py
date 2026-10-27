"""
Download Documents Audit Report.
Identifies, details, and extracts all downloadable document assets (PDF, Word, Excel, CSV etc.)
from Google Search Console data for migration planning and asset governance.
"""
import os
import sys
import argparse
from datetime import datetime, timedelta
from urllib.parse import urlparse, unquote
import pandas as pd
from jinja2 import Environment, FileSystemLoader

# Add parent directory to sys.path to allow importing core modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from core.naming import get_output_dir, get_filename_slug
from core.cache import fetch_with_cache
from core.client import get_gsc_service
from core.date_utils import get_month_range_lookback, get_latest_available_date

DOCUMENT_EXTENSIONS = (
    '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.csv',
    '.ppt', '.pptx', '.odt', '.ods', '.rtf', '.zip'
)

def clean_and_strip_url(url):
    """Normalises URLs by stripping query parameters, anchor fragments, and trailing slashes."""
    if not isinstance(url, str) or not url:
        return ""
    parsed = urlparse(url.strip())
    path = parsed.path.rstrip('/')
    if not path:
        path = ""
    netloc = parsed.netloc.lower()
    scheme = parsed.scheme.lower() or "https"
    clean_url = f"{scheme}://{netloc}{path}"
    return clean_url.rstrip('/')

def is_download_document(url):
    """Checks whether a URL targets a downloadable document asset."""
    if not isinstance(url, str) or not url:
        return False
    parsed = urlparse(url.strip())
    path = parsed.path.lower()
    return any(path.endswith(ext) for ext in DOCUMENT_EXTENSIONS)

def get_document_type(url):
    """Extracts uppercase document extension or 'DOC'."""
    parsed = urlparse(url.strip())
    path = parsed.path.lower()
    for ext in DOCUMENT_EXTENSIONS:
        if path.endswith(ext):
            return ext.lstrip('.').upper()
    return "DOC"

def get_url_display(url):
    """Returns a shortened relative path for table display."""
    if not isinstance(url, str):
        return ""
    parsed = urlparse(url)
    return parsed.path or "/"

def run_report(service, site_url="https://www.hr-inform.co.uk", start_date=None, end_date=None):
    """
    Executes the Download Documents Audit Report for the given property and date period.
    Generates a granular CSV and an interactive HTML dashboard.
    """
    print(f"\n[+] Running Download Documents Report for {site_url}")
    print(f"    Date Period: {start_date} to {end_date}")

    slug = get_filename_slug(site_url)
    output_dir = get_output_dir(site_url)
    os.makedirs(output_dir, exist_ok=True)

    # 1. Fetch GSC Data (query, page)
    df = fetch_with_cache(service, site_url, start_date, end_date, ['query', 'page'])
    if df is None or df.empty:
        print("[!] No search query or page data found for the selected property and period.")
        return None, None

    # Normalise numeric columns
    df['clicks'] = pd.to_numeric(df['clicks'], errors='coerce').fillna(0).astype(int)
    df['impressions'] = pd.to_numeric(df['impressions'], errors='coerce').fillna(0).astype(int)
    df['position'] = pd.to_numeric(df['position'], errors='coerce').fillna(0.0)
    df['clean_url'] = df['page'].apply(clean_and_strip_url)

    # Filter for downloadable documents
    df['is_document'] = df['clean_url'].apply(is_download_document)
    df_docs = df[df['is_document']].copy()

    # 2. Aggregate metrics by clean document URL
    doc_records = []
    if not df_docs.empty:
        for u, group in df_docs.groupby('clean_url'):
            clicks = int(group['clicks'].sum())
            impressions = int(group['impressions'].sum())
            ctr = (clicks / impressions) if impressions > 0 else 0.0
            avg_pos = float(group['position'].mean()) if impressions == 0 else float((group['position'] * group['impressions']).sum() / impressions)
            sorted_group = group.sort_values(by=['clicks', 'impressions'], ascending=[False, False])
            top_query_row = sorted_group.iloc[0]
            top_query = top_query_row['query']
            file_type = get_document_type(u)
            raw_filename = os.path.basename(urlparse(u).path)
            doc_filename = unquote(raw_filename) if raw_filename else u

            doc_records.append({
                'url': u,
                'url_display': get_url_display(u),
                'file_type': file_type,
                'filename': doc_filename,
                'top_query': top_query,
                'clicks': clicks,
                'clicks_formatted': f"{clicks:,}",
                'impressions': impressions,
                'impressions_formatted': f"{impressions:,}",
                'ctr': ctr,
                'ctr_formatted': f"{ctr:.2%}",
                'position': avg_pos,
                'position_formatted': f"{avg_pos:.1f}"
            })

        doc_records.sort(key=lambda x: (x['clicks'], x['impressions']), reverse=True)

    print(f"    Identified {len(doc_records):,} unique downloadable document assets.")

    # 3. Save CSV
    csv_filename = f"download-documents-{slug}-{start_date}-to-{end_date}.csv"
    csv_path = os.path.join(output_dir, csv_filename)
    if doc_records:
        df_export = pd.DataFrame(doc_records)[[
            'url', 'file_type', 'filename', 'top_query',
            'clicks', 'impressions', 'ctr', 'position'
        ]].copy()
        df_export.rename(columns={
            'url': 'Document URL',
            'file_type': 'File Type',
            'filename': 'Document Filename',
            'top_query': 'Primary Search Query',
            'clicks': 'Organic Clicks',
            'impressions': 'Organic Impressions',
            'ctr': 'CTR',
            'position': 'Average Position'
        }, inplace=True)
        df_export.to_csv(csv_path, index=False, encoding='utf-8')
    else:
        pd.DataFrame(columns=[
            'Document URL', 'File Type', 'Document Filename', 'Primary Search Query',
            'Organic Clicks', 'Organic Impressions', 'CTR', 'Average Position'
        ]).to_csv(csv_path, index=False, encoding='utf-8')

    # 4. Render HTML Report
    html_filename = f"download-documents-report-{slug}-{start_date}-to-{end_date}.html"
    html_path = os.path.join(output_dir, html_filename)

    templates_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'templates'))
    env = Environment(loader=FileSystemLoader(templates_dir))
    template = env.get_template('download-documents-template.html')

    total_clicks = sum(d['clicks'] for d in doc_records)
    total_impressions = sum(d['impressions'] for d in doc_records)
    
    # Type counts
    type_counts = {}
    for d in doc_records:
        t = d['file_type']
        type_counts[t] = type_counts.get(t, 0) + 1
    type_summary_parts = [f"{t} ({cnt})" for t, cnt in sorted(type_counts.items(), key=lambda x: x[1], reverse=True)[:3]]
    file_types_summary = ", ".join(type_summary_parts) if type_summary_parts else "None"

    html_content = template.render(
        page_title=f"Download Documents Audit Report - {site_url}",
        site_url=site_url,
        period_str=f"{start_date} to {end_date}",
        generation_date=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        doc_count_formatted=f"{len(doc_records):,}",
        total_clicks_formatted=f"{total_clicks:,}",
        total_impressions_formatted=f"{total_impressions:,}",
        file_types_summary=file_types_summary,
        csv_filename=csv_filename,
        documents=doc_records
    )

    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(html_content)

    # 5. Console Output
    print("\n" + "=" * 75)
    print("DOWNLOAD DOCUMENTS AUDIT REPORT SUMMARY")
    print("=" * 75)
    print(f"Total Unique Download Documents: {len(doc_records):,}")
    print(f"Total Organic Clicks:            {total_clicks:,}")
    print(f"Total Organic Impressions:       {total_impressions:,}")
    print(f"File Type Breakdown:             {file_types_summary}")
    print("-" * 75)
    print(f"Documents CSV:  file://{os.path.abspath(csv_path)}")
    print(f"HTML Dashboard: file://{os.path.abspath(html_path)}")
    print("=" * 75 + "\n")

    return csv_path, html_path

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Run Download Documents audit report.')
    parser.add_argument('site_url', nargs='?', default='https://www.hr-inform.co.uk', help='The site URL or GSC property.')
    parser.add_argument('--start-date', help='Start date (YYYY-MM-DD).')
    parser.add_argument('--end-date', help='End date (YYYY-MM-DD).')
    parser.add_argument('--last-month', action='store_true', help='Anchor to the last complete month.')
    parser.add_argument('--months', type=int, default=12, help='Number of lookback months (defaults to 12).')

    args = parser.parse_args()

    service = get_gsc_service()
    if service:
        if args.start_date and args.end_date:
            start_date, end_date = args.start_date, args.end_date
        else:
            latest_date = get_latest_available_date(service, args.site_url)
            first_of_month = latest_date.replace(day=1)
            end_dt = first_of_month - timedelta(days=1)
            end_date = end_dt.strftime('%Y-%m-%d')
            start_date, end_date = get_month_range_lookback(end_date, months=args.months)

        run_report(service, args.site_url, start_date, end_date)
