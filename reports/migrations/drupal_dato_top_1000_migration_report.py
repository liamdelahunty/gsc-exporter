"""
Top 1,000 Drupal to DatoCMS Migration Intelligence Report.
Selects, scores, and classifies the top 1,000 legacy Drupal (purple) URLs to migrate,
excluding cannibalised query competitors and already migrated Dato pages.
"""
import os
import sys
import re
import argparse
from datetime import datetime, date, timedelta
from urllib.parse import urlparse, unquote
import pandas as pd
import numpy as np
from jinja2 import Environment, FileSystemLoader

# Add parent directory to sys.path to allow importing core modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from core.naming import get_output_dir, get_filename_slug
from core.cache import fetch_with_cache
from core.client import get_gsc_service
from core.date_utils import parse_standard_date_args, get_month_range_lookback, get_latest_available_date

# Known mappings / overrides from legacy Drupal to new Dato structures
LEGACY_MAPPINGS = {
    "https://www.hr-inform.co.uk/comment-and-analysis/legislative-changes": "https://www.hr-inform.co.uk/features/webinars",
    "https://www.hr-inform.co.uk/templates-and-tools/medical-checks": "https://www.hr-inform.co.uk/resources/employee-health-questionnaire-template",
    "https://www.hr-inform.co.uk/news-article/action-on-gender-diversity-led-to-resignation-of-bbc-dj": "https://www.hr-inform.co.uk/features/simon-mayo-illness",
    "https://www.hr-inform.co.uk/templates-and-tools/probationary-periods": "https://www.hr-inform.co.uk/resources/probation-review-template",
    "https://www.hr-inform.co.uk/case-law?field_category_target_id=15": "https://www.hr-inform.co.uk/guides/unfair-dismissal-cases",
    "https://www.hr-inform.co.uk/employment_law/employment-law-in-canada": "https://www.hr-inform.co.uk/guides/canadian-labour-laws",
    "https://www.hr-inform.co.uk/system/files/downloads/2017-09/Template%20payslips.docx": "https://www.hr-inform.co.uk/resources/free-payslip-template"
}

# Patterns for non-content or utility URLs to ignore
UTILITY_PATTERNS = [
    r'^/(user|login|logout|admin|search|taxonomy|batch|node/add|filter/tips)',
    r'^/system/files/.*(css|js|png|jpg|jpeg|gif|ico|svg)$',
    r'/feed/?$',
    r'/rss/?$'
]

# Supported downloadable document extensions
DOCUMENT_EXTENSIONS = (
    '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.csv',
    '.ppt', '.pptx', '.odt', '.ods', '.rtf', '.zip'
)

def is_download_document(url):
    """Checks whether a URL targets a downloadable document asset (PDF, DOC, XLS, CSV etc.)."""
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

def clean_and_strip_url(url):
    """
    Normalises URLs by stripping query parameters, anchor fragments,
    converting to lowercase, and removing trailing slashes.
    """
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

def is_utility_url(url, site_url=None):
    """
    Checks whether a URL is a utility, non-content, or root home page endpoint.
    Root home pages and login/admin endpoints are excluded from legacy content migration.
    """
    if not isinstance(url, str) or not url:
        return True
    parsed = urlparse(url.strip())
    path = parsed.path.lower().rstrip('/')
    # Root home page is not legacy content to migrate
    if not path or path == "":
        return True
    if site_url:
        clean_site = clean_and_strip_url(site_url)
        clean_u = clean_and_strip_url(url)
        if clean_u == clean_site:
            return True
    for pattern in UTILITY_PATTERNS:
        if re.search(pattern, path):
            return True
    return False

def load_dato_urls(slug="hr-inform"):
    """
    Loads Dato (new platform) URLs from configuration.
    Falls back to a standard default list if the file is absent.
    """
    dato_urls = set()
    possible_paths = [
        os.path.join('config', f"dato-urls-{slug}.txt"),
        os.path.join('config', "dato-urls-hr-inform.txt"),
        os.path.join(os.path.dirname(__file__), '..', '..', 'config', "dato-urls-hr-inform.txt")
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                for line in f:
                    u = clean_and_strip_url(line)
                    if u:
                        dato_urls.add(u)
            break

    if not dato_urls:
        # Fallback default Dato list
        default_list = [
            "https://www.hr-inform.co.uk/employment-rights-act",
            "https://www.hr-inform.co.uk/employment-rights-act/absences-and-leave-overview",
            "https://www.hr-inform.co.uk/employment-rights-act/bereavement-leave",
            "https://www.hr-inform.co.uk/employment-rights-act/fair-work-agency",
            "https://www.hr-inform.co.uk/employment-rights-act/fire-and-rehire",
            "https://www.hr-inform.co.uk/employment-rights-act/flexible-working",
            "https://www.hr-inform.co.uk/employment-rights-act/large-employers",
            "https://www.hr-inform.co.uk/employment-rights-act/parental-leave",
            "https://www.hr-inform.co.uk/employment-rights-act/parental-vs-paternity-leave-explained",
            "https://www.hr-inform.co.uk/employment-rights-act/paternity-leave",
            "https://www.hr-inform.co.uk/employment-rights-act/probation-periods",
            "https://www.hr-inform.co.uk/employment-rights-act/redundancy-consultation",
            "https://www.hr-inform.co.uk/employment-rights-act/sexual-harassment",
            "https://www.hr-inform.co.uk/employment-rights-act/sick-pay",
            "https://www.hr-inform.co.uk/employment-rights-act/unfair-dismissal",
            "https://www.hr-inform.co.uk/employment-rights-act/union-access",
            "https://www.hr-inform.co.uk/employment-rights-act/zero-hour-contract",
            "https://www.hr-inform.co.uk/features",
            "https://www.hr-inform.co.uk/features/working-during-heatwave",
            "https://www.hr-inform.co.uk/policies",
            "https://www.hr-inform.co.uk/policies/major-sporting-events-template",
            "https://www.hr-inform.co.uk/resources",
            "https://www.hr-inform.co.uk/resources/free-payslip-template"
        ]
        dato_urls = {clean_and_strip_url(u) for u in default_list}
        
    return dato_urls

def get_url_display(url):
    """Returns a shortened relative path or cleaner URL for table display."""
    if not isinstance(url, str):
        return ""
    parsed = urlparse(url)
    path = parsed.path
    if not path:
        return "/"
    return path

def run_report(service, site_url="https://www.hr-inform.co.uk", start_date=None, end_date=None,
               limit=1000, min_impressions_opp=500, max_position_opp=20.0, max_ctr_opp=0.015):
    """
    Executes the Top 1,000 Drupal to DatoCMS migration selection and classification report.
    Generates CSV outputs and an interactive HTML dashboard.
    """
    print(f"\n[+] Running Top 1,000 Drupal to Dato Migration Report for {site_url}")
    print(f"    Date Period: {start_date} to {end_date}")

    # 1. Load Dato (New) URLs
    slug = get_filename_slug(site_url)
    dato_clean_urls = load_dato_urls(slug)
    print(f"    Loaded {len(dato_clean_urls)} active DatoCMS URLs.")

    # 2. Fetch GSC Data (query, page)
    df = fetch_with_cache(service, site_url, start_date, end_date, ['query', 'page'])
    if df is None or df.empty:
        print("[!] No search query or page data found for the selected property and period.")
        return None, None, None, None

    # Normalise numeric columns
    df['clicks'] = pd.to_numeric(df['clicks'], errors='coerce').fillna(0).astype(int)
    df['impressions'] = pd.to_numeric(df['impressions'], errors='coerce').fillna(0).astype(int)
    df['position'] = pd.to_numeric(df['position'], errors='coerce').fillna(0.0)
    df['clean_url'] = df['page'].apply(clean_and_strip_url)

    # Filter out empty or home page root, and utility pages
    df['is_utility'] = df['clean_url'].apply(lambda u: is_utility_url(u, site_url))
    df_valid = df[~df['is_utility']].copy()

    # Separate downloadable document assets (PDF, DOC, XLS, CSV etc.) into their own dedicated dataset
    df_valid['is_download'] = df_valid['clean_url'].apply(is_download_document)
    df_downloads_raw = df_valid[df_valid['is_download']].copy()
    df_content = df_valid[~df_valid['is_download']].copy()

    # Process Download Documents
    download_docs_summary = []
    if not df_downloads_raw.empty:
        for u, group in df_downloads_raw.groupby('clean_url'):
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

            download_docs_summary.append({
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
        download_docs_summary.sort(key=lambda x: (x['clicks'], x['impressions']), reverse=True)
    print(f"    Identified {len(download_docs_summary):,} downloadable document assets (PDF, DOC, XLS, CSV).")

    # Classify platform (Dato vs Drupal)
    df_content['is_dato'] = df_content['clean_url'].isin(dato_clean_urls)

    # 3. Process Already Migrated Dato Pages
    df_dato_raw = df_content[df_content['is_dato']].copy()
    dato_pages_summary = []
    
    # Inverted legacy mapping for lookup
    dato_to_legacy = {}
    for leg, dat in LEGACY_MAPPINGS.items():
        dato_to_legacy[clean_and_strip_url(dat)] = clean_and_strip_url(leg)

    if not df_dato_raw.empty:
        for u, group in df_dato_raw.groupby('clean_url'):
            clicks = int(group['clicks'].sum())
            impressions = int(group['impressions'].sum())
            ctr = (clicks / impressions) if impressions > 0 else 0.0
            avg_pos = float(group['position'].mean()) if impressions == 0 else float((group['position'] * group['impressions']).sum() / impressions)
            top_query = group.sort_values(by='clicks', ascending=False).iloc[0]['query'] if not group.empty else 'N/A'
            legacy_counterpart = dato_to_legacy.get(u, "")
            needs_review = bool(legacy_counterpart and legacy_counterpart != u)
            
            dato_pages_summary.append({
                'url': u,
                'url_display': get_url_display(u),
                'legacy_url': legacy_counterpart,
                'legacy_url_display': get_url_display(legacy_counterpart) if legacy_counterpart else "",
                'clicks': clicks,
                'clicks_formatted': f"{clicks:,}",
                'impressions': impressions,
                'impressions_formatted': f"{impressions:,}",
                'ctr': ctr,
                'ctr_formatted': f"{ctr:.2%}",
                'position': avg_pos,
                'position_formatted': f"{avg_pos:.1f}",
                'top_query': top_query,
                'needs_review': needs_review
            })
    # Add any Dato URL in the config that received 0 GSC traffic
    existing_dato_summary_urls = {item['url'] for item in dato_pages_summary}
    for u in dato_clean_urls:
        if u not in existing_dato_summary_urls:
            legacy_counterpart = dato_to_legacy.get(u, "")
            dato_pages_summary.append({
                'url': u,
                'url_display': get_url_display(u),
                'legacy_url': legacy_counterpart,
                'legacy_url_display': get_url_display(legacy_counterpart) if legacy_counterpart else "",
                'clicks': 0,
                'clicks_formatted': "0",
                'impressions': 0,
                'impressions_formatted': "0",
                'ctr': 0.0,
                'ctr_formatted': "0.00%",
                'position': 0.0,
                'position_formatted': "N/A",
                'top_query': "N/A",
                'needs_review': bool(legacy_counterpart and legacy_counterpart != u)
            })

    dato_pages_summary.sort(key=lambda x: x['clicks'], reverse=True)

    # 4. Filter Legacy Drupal Pages
    df_drupal = df_content[~df_content['is_dato']].copy()
    if df_drupal.empty:
        print("[!] No legacy Drupal pages found.")
        return None, None, None, None

    # Aggregate metrics at the clean legacy URL level
    grouped_drupal = []
    for u, group in df_drupal.groupby('clean_url'):
        clicks = int(group['clicks'].sum())
        impressions = int(group['impressions'].sum())
        ctr = (clicks / impressions) if impressions > 0 else 0.0
        avg_pos = float(group['position'].mean()) if impressions == 0 else float((group['position'] * group['impressions']).sum() / impressions)
        # Top query driving the page
        sorted_group = group.sort_values(by=['clicks', 'impressions'], ascending=[False, False])
        top_query_row = sorted_group.iloc[0]
        top_query = top_query_row['query']
        top_query_clicks = int(top_query_row['clicks'])
        top_query_impressions = int(top_query_row['impressions'])

        grouped_drupal.append({
            'url': u,
            'url_display': get_url_display(u),
            'clicks': clicks,
            'impressions': impressions,
            'ctr': ctr,
            'position': avg_pos,
            'top_query': top_query,
            'top_query_clicks': top_query_clicks,
            'top_query_impressions': top_query_impressions
        })

    df_drupal_pages = pd.DataFrame(grouped_drupal)
    total_drupal_urls = len(df_drupal_pages)
    print(f"    Aggregated {total_drupal_urls:,} unique legacy Drupal content URLs.")

    # 5. Cannibalisation Identification
    # Identify queries where multiple legacy pages compete for the identical top query
    query_leaders = {}
    for _, row in df_drupal_pages.iterrows():
        q = row['top_query']
        if q not in query_leaders:
            query_leaders[q] = row
        else:
            # Compare clicks, then impressions
            curr = query_leaders[q]
            if (row['clicks'] > curr['clicks']) or (row['clicks'] == curr['clicks'] and row['impressions'] > curr['impressions']):
                query_leaders[q] = row

    cannibalised_list = []
    candidates_list = []

    for _, row in df_drupal_pages.iterrows():
        q = row['top_query']
        leader = query_leaders[q]
        if leader['url'] != row['url']:
            # This is a secondary competing page -> Cannibalised
            source_parsed = urlparse(row['url'])
            target_parsed = urlparse(leader['url'])
            cannibalised_list.append({
                'source_url': row['url'],
                'source_url_display': get_url_display(row['url']),
                'source_path': source_parsed.path or '/',
                'target_url': leader['url'],
                'target_url_display': get_url_display(leader['url']),
                'target_path': target_parsed.path or '/',
                'query': q,
                'source_clicks': row['clicks'],
                'target_clicks': leader['clicks'],
                'source_impressions': row['impressions'],
                'target_impressions': leader['impressions']
            })
        else:
            # Primary winning page -> candidate for top 1,000
            candidates_list.append(row.to_dict())

    df_candidates = pd.DataFrame(candidates_list)
    print(f"    Identified {len(cannibalised_list):,} cannibalised secondary pages (excluded from candidate quota).")
    print(f"    Remaining candidate pool: {len(df_candidates):,} unique pages.")

    # 6. Scoring Calculations for Candidates
    # Method A: Composite Score
    # Clicks + (Impressions / 50.0)
    df_candidates['composite_score'] = df_candidates['clicks'] + (df_candidates['impressions'] / 50.0)

    # Method B: Combined Rank Sum
    df_candidates['rank_clicks'] = df_candidates['clicks'].rank(ascending=False, method='min').astype(int)
    df_candidates['rank_impressions'] = df_candidates['impressions'].rank(ascending=False, method='min').astype(int)
    df_candidates['combined_rank'] = df_candidates['rank_clicks'] + df_candidates['rank_impressions']

    # Method C: Tiered Allocation
    # Top 700 by Clicks -> Tier 1
    # Top 300 by Impressions (from remaining) -> Tier 2
    # Remainder -> Tier 3
    df_candidates['tier'] = 'Tier 3 (Long Tail)'
    tier1_indices = df_candidates.sort_values(by='clicks', ascending=False).head(700).index
    df_candidates.loc[tier1_indices, 'tier'] = 'Tier 1 (Top Clicks)'

    remaining_for_tier2 = df_candidates[df_candidates['tier'] == 'Tier 3 (Long Tail)']
    tier2_indices = remaining_for_tier2.sort_values(by='impressions', ascending=False).head(300).index
    df_candidates.loc[tier2_indices, 'tier'] = 'Tier 2 (Top Impressions)'

    # 7. Metadata / CTR Opportunity Flagging
    # Criteria: Impressions >= min_impressions_opp, Position <= max_position_opp, CTR < max_ctr_opp
    df_candidates['is_opp'] = (
        (df_candidates['impressions'] >= min_impressions_opp) &
        (df_candidates['position'] <= max_position_opp) &
        (df_candidates['ctr'] < max_ctr_opp)
    )
    df_candidates['opp_reason'] = df_candidates.apply(
        lambda r: f"High search volume ({r['impressions']:,} impr) ranking at position {r['position']:.1f} with underperforming CTR ({r['ctr']:.2%})" if r['is_opp'] else "",
        axis=1
    )

    # 8. Multi-Mechanism Comprehensive Candidate Selection
    # To enable comparative analysis across all 3 mechanisms (Composite Score,
    # Combined Rank Sum, and Tiered Allocation) and decide what to migrate and avoid:
    # Pull top N by clicks, top N by impressions, top N by composite score,
    # top N by combined rank sum, all Tier 1 & 2 URLs, and all CTR opportunities.
    pool_size = len(df_candidates)
    if pool_size <= limit:
        df_top_1000 = df_candidates.copy()
    else:
        top_clicks_idx = set(df_candidates.sort_values(by=['clicks', 'impressions'], ascending=[False, False]).head(limit).index)
        top_impr_idx = set(df_candidates.sort_values(by=['impressions', 'clicks'], ascending=[False, False]).head(limit).index)
        top_comp_idx = set(df_candidates.sort_values(by=['composite_score', 'clicks'], ascending=[False, False]).head(limit).index)
        top_rank_idx = set(df_candidates.sort_values(by=['combined_rank', 'composite_score'], ascending=[True, False]).head(limit).index)
        tier_idx = set(df_candidates[df_candidates['tier'].isin(['Tier 1 (Top Clicks)', 'Tier 2 (Top Impressions)'])].index)
        opp_idx = set(df_candidates[df_candidates['is_opp'] | (df_candidates['clicks'] >= 100)].index)

        selected_indices = top_clicks_idx | top_impr_idx | top_comp_idx | top_rank_idx | tier_idx | opp_idx
        df_top_1000 = df_candidates.loc[sorted(list(selected_indices))].copy()

    # Sort candidates list primarily by Composite Score
    df_top_1000.sort_values(by=['composite_score', 'clicks'], ascending=[False, False], inplace=True)

    # Opportunities subset
    df_opportunities = df_top_1000[df_top_1000['is_opp']].sort_values(by='impressions', ascending=False).copy()

    # Format candidates for presentation
    candidate_records = []
    for _, r in df_top_1000.iterrows():
        candidate_records.append({
            'url': r['url'],
            'url_display': r['url_display'],
            'top_query': r['top_query'],
            'clicks': r['clicks'],
            'clicks_formatted': f"{r['clicks']:,}",
            'impressions': r['impressions'],
            'impressions_formatted': f"{r['impressions']:,}",
            'ctr': r['ctr'],
            'ctr_formatted': f"{r['ctr']:.2%}",
            'position': r['position'],
            'position_formatted': f"{r['position']:.1f}",
            'composite_score': r['composite_score'],
            'composite_score_formatted': f"{r['composite_score']:,.1f}",
            'combined_rank': r['combined_rank'],
            'combined_rank_formatted': f"{r['combined_rank']:,}",
            'tier': r['tier'],
            'is_opp': r['is_opp'],
            'opp_reason': r['opp_reason']
        })

    opp_records = []
    for _, r in df_opportunities.iterrows():
        opp_records.append({
            'url': r['url'],
            'url_display': r['url_display'],
            'top_query': r['top_query'],
            'clicks': r['clicks'],
            'clicks_formatted': f"{r['clicks']:,}",
            'impressions': r['impressions'],
            'impressions_formatted': f"{r['impressions']:,}",
            'ctr': r['ctr'],
            'ctr_formatted': f"{r['ctr']:.2%}",
            'position': r['position'],
            'position_formatted': f"{r['position']:.1f}",
            'opp_reason': r['opp_reason']
        })

    # 8. Setup Output Paths
    output_dir = get_output_dir(site_url)
    os.makedirs(output_dir, exist_ok=True)

    candidates_csv_name = f"top-1000-migration-candidates-{slug}-{start_date}-to-{end_date}.csv"
    cannibal_csv_name = f"cannibalised-redirects-{slug}-{start_date}-to-{end_date}.csv"
    dato_csv_name = f"already-migrated-dato-pages-{slug}-{start_date}-to-{end_date}.csv"
    downloads_csv_name = f"download-documents-{slug}-{start_date}-to-{end_date}.csv"
    html_name = f"top-1000-migration-report-{slug}-{start_date}-to-{end_date}.html"

    candidates_csv_path = os.path.join(output_dir, candidates_csv_name)
    cannibal_csv_path = os.path.join(output_dir, cannibal_csv_name)
    dato_csv_path = os.path.join(output_dir, dato_csv_name)
    downloads_csv_path = os.path.join(output_dir, downloads_csv_name)
    html_path = os.path.join(output_dir, html_name)

    # 9. Save CSV Files
    # Candidate CSV
    export_candidates_df = df_top_1000[[
        'url', 'top_query', 'clicks', 'impressions', 'ctr', 'position',
        'rank_clicks', 'rank_impressions',
        'composite_score', 'combined_rank', 'tier', 'is_opp', 'opp_reason'
    ]].copy()
    export_candidates_df.rename(columns={
        'url': 'Legacy Drupal URL',
        'top_query': 'Primary Query',
        'clicks': 'Organic Clicks',
        'impressions': 'Organic Impressions',
        'ctr': 'CTR',
        'position': 'Average Position',
        'rank_clicks': 'Clicks Rank',
        'rank_impressions': 'Impressions Rank',
        'composite_score': 'Method A (Composite Score)',
        'combined_rank': 'Method B (Combined Rank Sum)',
        'tier': 'Method C (Tiered Allocation)',
        'is_opp': 'Is CTR Opportunity',
        'opp_reason': 'SEO Recommendation'
    }, inplace=True)
    export_candidates_df.to_csv(candidates_csv_path, index=False, encoding='utf-8')

    # Cannibalised CSV
    df_cannibal = pd.DataFrame(cannibalised_list)
    if not df_cannibal.empty:
        df_cannibal_export = df_cannibal[[
            'source_url', 'target_url', 'query', 'source_clicks', 'target_clicks',
            'source_impressions', 'target_impressions', 'source_path', 'target_path'
        ]].copy()
        df_cannibal_export['Apache 301 Directive'] = df_cannibal_export.apply(
            lambda r: f"Redirect 301 {r['source_path']} {r['target_path']}", axis=1
        )
        df_cannibal_export.rename(columns={
            'source_url': 'Cannibalised Secondary URL (Source)',
            'target_url': 'Primary Winning URL (Target)',
            'query': 'Competing Search Query',
            'source_clicks': 'Secondary Clicks',
            'target_clicks': 'Winning Clicks',
            'source_impressions': 'Secondary Impressions',
            'target_impressions': 'Winning Impressions'
        }, inplace=True)
        df_cannibal_export.to_csv(cannibal_csv_path, index=False, encoding='utf-8')
    else:
        pd.DataFrame(columns=['Source URL', 'Target URL', 'Query']).to_csv(cannibal_csv_path, index=False)

    # Dato Reconciliation CSV
    df_dato_summary = pd.DataFrame(dato_pages_summary)
    if not df_dato_summary.empty:
        df_dato_export = df_dato_summary[[
            'url', 'legacy_url', 'top_query', 'clicks', 'impressions', 'ctr', 'position', 'needs_review'
        ]].copy()
        df_dato_export.rename(columns={
            'url': 'Live Dato URL',
            'legacy_url': 'Reconciled Legacy URL',
            'top_query': 'Top Query',
            'clicks': 'Clicks',
            'impressions': 'Impressions',
            'ctr': 'CTR',
            'position': 'Average Position',
            'needs_review': 'Altered from Legacy'
        }, inplace=True)
        df_dato_export.to_csv(dato_csv_path, index=False, encoding='utf-8')
    else:
        pd.DataFrame(columns=['Live Dato URL']).to_csv(dato_csv_path, index=False)

    # Download Documents CSV (PDF, DOC, XLS, CSV etc.)
    if download_docs_summary:
        df_downloads_export = pd.DataFrame(download_docs_summary)[[
            'url', 'file_type', 'filename', 'top_query',
            'clicks', 'impressions', 'ctr', 'position'
        ]].copy()
        df_downloads_export.rename(columns={
            'url': 'Document URL',
            'file_type': 'File Type',
            'filename': 'Document Filename',
            'top_query': 'Primary Search Query',
            'clicks': 'Organic Clicks',
            'impressions': 'Organic Impressions',
            'ctr': 'CTR',
            'position': 'Average Position'
        }, inplace=True)
        df_downloads_export.to_csv(downloads_csv_path, index=False, encoding='utf-8')
    else:
        pd.DataFrame(columns=[
            'Document URL', 'File Type', 'Document Filename', 'Primary Search Query',
            'Organic Clicks', 'Organic Impressions', 'CTR', 'Average Position'
        ]).to_csv(downloads_csv_path, index=False, encoding='utf-8')

    # 10. Render HTML Report
    templates_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'templates'))
    env = Environment(loader=FileSystemLoader(templates_dir))
    template = env.get_template('drupal-dato-top-1000-migration-template.html')

    candidate_clicks = int(df_top_1000['clicks'].sum())
    total_site_clicks = int(df_content['clicks'].sum())
    dato_clicks = int(df_dato_raw['clicks'].sum()) if not df_dato_raw.empty else 0
    download_clicks = sum(d['clicks'] for d in download_docs_summary)

    candidate_clicks_pct = (candidate_clicks / total_site_clicks) if total_site_clicks > 0 else 0.0
    dato_clicks_pct = (dato_clicks / total_site_clicks) if total_site_clicks > 0 else 0.0

    html_content = template.render(
        page_title=f"Top 1,000 Drupal to Dato Migration Report - {site_url}",
        site_url=site_url,
        period_str=f"{start_date} to {end_date}",
        generation_date=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        candidate_count_formatted=f"{len(df_top_1000):,}",
        candidate_clicks_formatted=f"{candidate_clicks:,}",
        candidate_clicks_pct=f"{candidate_clicks_pct:.1%}",
        opp_count_formatted=f"{len(df_opportunities):,}",
        opp_impressions_formatted=f"{int(df_opportunities['impressions'].sum()):,}",
        cannibal_count_formatted=f"{len(cannibalised_list):,}",
        dato_count_formatted=f"{len(dato_pages_summary):,}",
        dato_clicks_formatted=f"{dato_clicks:,}",
        dato_clicks_pct=f"{dato_clicks_pct:.1%}",
        downloads_count_formatted=f"{len(download_docs_summary):,}",
        downloads_clicks_formatted=f"{download_clicks:,}",
        total_drupal_urls_formatted=f"{total_drupal_urls:,}",
        candidates_csv_filename=candidates_csv_name,
        cannibal_csv_filename=cannibal_csv_name,
        dato_csv_filename=dato_csv_name,
        downloads_csv_filename=downloads_csv_name,
        candidates=candidate_records,
        opportunities=opp_records,
        cannibalised=cannibalised_list,
        dato_pages=dato_pages_summary,
        download_documents=download_docs_summary
    )

    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(html_content)

    # 11. Console Summary Printout
    print("\n" + "=" * 75)
    print("TOP 1,000 DRUPAL TO DATOCMS MIGRATION INTELLIGENCE SUMMARY")
    print("=" * 75)
    print(f"Total Unique Legacy Drupal URLs Evaluated: {total_drupal_urls:,}")
    print(f"Priority Migration Candidates Selected:    {len(df_top_1000):,} ({candidate_clicks:,} clicks, {candidate_clicks_pct:.1%} of total)")
    print(f"CTR / Title & Meta Opportunities:          {len(df_opportunities):,} ({int(df_opportunities['impressions'].sum()):,} impr)")
    print(f"Cannibalised Secondary URLs (Excluded):    {len(cannibalised_list):,} (mapped to 301 redirects)")
    print(f"Already Migrated DatoCMS URLs:             {len(dato_pages_summary):,} ({dato_clicks:,} clicks)")
    print(f"Download Documents Identified:             {len(download_docs_summary):,} ({download_clicks:,} clicks)")
    print("-" * 75)
    print(f"Candidates CSV:   file://{os.path.abspath(candidates_csv_path)}")
    print(f"Redirects CSV:    file://{os.path.abspath(cannibal_csv_path)}")
    print(f"Dato Reconciled:  file://{os.path.abspath(dato_csv_path)}")
    print(f"Download Docs:    file://{os.path.abspath(downloads_csv_path)}")
    print(f"HTML Dashboard:   file://{os.path.abspath(html_path)}")
    print("=" * 75 + "\n")

    return candidates_csv_path, cannibal_csv_path, dato_csv_path, downloads_csv_path, html_path

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Run Top 1,000 Drupal to Dato migration classification report.')
    parser.add_argument('site_url', nargs='?', default='https://www.hr-inform.co.uk', help='The site URL or GSC property.')
    parser.add_argument('--start-date', help='Start date (YYYY-MM-DD).')
    parser.add_argument('--end-date', help='End date (YYYY-MM-DD).')
    parser.add_argument('--last-month', action='store_true', help='Anchor to the last complete month.')
    parser.add_argument('--months', type=int, default=12, help='Number of lookback months (defaults to 12).')
    parser.add_argument('--limit', type=int, default=1000, help='Maximum candidate URLs to select (default: 1000).')

    args = parser.parse_args()

    service = get_gsc_service()
    if service:
        if args.start_date and args.end_date:
            start_date, end_date = args.start_date, args.end_date
        else:
            latest_date = get_latest_available_date(service, args.site_url)
            # Find last complete month end date
            first_of_month = latest_date.replace(day=1)
            end_dt = first_of_month - timedelta(days=1)
            end_date = end_dt.strftime('%Y-%m-%d')
            start_date, end_date = get_month_range_lookback(end_date, months=args.months)

        run_report(service, args.site_url, start_date, end_date, limit=args.limit)
