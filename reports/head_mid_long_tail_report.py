"""
Head, Mid Tail & Long Tail Search Traffic Report for Google Search Console.

Analyses organic search queries segmented into:
1. Lexical Word-Count Tiers:
   - Head: 1-2 words
   - Mid Tail: 3-4 words
   - Long Tail: 5+ words
2. Demand Curve Volume Tiers:
   - Head (High Volume): 50+ clicks
   - Mid Tail (Moderate Volume): 5-49 clicks
   - Long Tail (Low Volume): 1-4 clicks
   - Zero-Click: 0 clicks (impressions only)
3. Brand vs Non-Brand Query Classification across all tiers.

Generates comprehensive summary and query-level CSVs along with an interactive HTML dashboard.
"""
import os
import sys
import json
import argparse
from datetime import datetime
import pandas as pd
import numpy as np
from jinja2 import Environment, FileSystemLoader

# Add parent directory to sys.path to allow importing core modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.naming import get_output_dir, get_filename_slug
from core.cache import fetch_with_cache
from core.client import get_gsc_service
from core.date_utils import parse_standard_date_args
from core.brand import get_brand_terms, classify_query


def classify_word_segment(word_count: int) -> str:
    """Categorises query length into Head, Mid Tail, or Long Tail."""
    if word_count <= 2:
        return 'Head'
    elif word_count <= 4:
        return 'Mid Tail'
    else:
        return 'Long Tail'


def classify_volume_tier(clicks: int) -> str:
    """Categorises query click volume into demand curve tiers."""
    if clicks >= 50:
        return 'Head (>= 50 clicks)'
    elif clicks >= 5:
        return 'Mid Tail (5-49 clicks)'
    elif clicks >= 1:
        return 'Long Tail (1-4 clicks)'
    else:
        return 'Zero-Click (0 clicks)'


def format_int(value) -> str:
    """Formats an integer with thousands separator."""
    try:
        return f"{int(value):,}"
    except (ValueError, TypeError):
        return "0"


def format_pct(value) -> str:
    """Formats a float as a percentage."""
    try:
        return f"{float(value):.2%}"
    except (ValueError, TypeError):
        return "0.00%"


def format_float(value) -> str:
    """Formats a float to two decimal places."""
    try:
        return f"{float(value):.2f}"
    except (ValueError, TypeError):
        return "0.00"


def calculate_segment_metrics(df_subset, total_clicks, total_impressions, total_queries, segment_name, extra_fields=None):
    """Calculates aggregate metrics for a subset of queries."""
    extra_fields = extra_fields or {}
    q_count = len(df_subset)
    clicks = int(df_subset['clicks'].sum()) if q_count > 0 else 0
    impressions = int(df_subset['impressions'].sum()) if q_count > 0 else 0
    ctr = (clicks / impressions) if impressions > 0 else 0.0
    
    # Weighted average position by impressions if available, else mean
    if impressions > 0:
        avg_pos = (df_subset['position'] * df_subset['impressions']).sum() / impressions
    elif q_count > 0:
        avg_pos = df_subset['position'].mean()
    else:
        avg_pos = 0.0

    # Brand metrics
    brand_df = df_subset[df_subset['is_brand']] if q_count > 0 else pd.DataFrame()
    brand_clicks = int(brand_df['clicks'].sum()) if not brand_df.empty else 0
    brand_clicks_pct = (brand_clicks / clicks) if clicks > 0 else 0.0

    return {
        'segment': segment_name,
        'query_count': format_int(q_count),
        'query_count_raw': q_count,
        'query_pct': format_pct(q_count / total_queries if total_queries > 0 else 0),
        'clicks': format_int(clicks),
        'clicks_raw': clicks,
        'clicks_pct': format_pct(clicks / total_clicks if total_clicks > 0 else 0),
        'impressions': format_int(impressions),
        'impressions_raw': impressions,
        'impressions_pct': format_pct(impressions / total_impressions if total_impressions > 0 else 0),
        'ctr': format_pct(ctr),
        'ctr_raw': ctr,
        'position': format_float(avg_pos),
        'position_raw': avg_pos,
        'brand_clicks_pct': format_pct(brand_clicks_pct),
        'brand_clicks_raw': brand_clicks,
        **extra_fields
    }


def run_report(service, site_url, start_date, end_date, limit=500):
    """
    Executes the Head, Mid Tail & Long Tail report for a given property and period.
    """
    print(f"\nRunning Head, Mid & Long Tail Search Traffic Report for {site_url}")
    print(f"Period: {start_date} to {end_date}")

    # 1. Fetch query-level data from GSC
    df = fetch_with_cache(service, site_url, start_date, end_date, dimensions=['query'])

    if df is None or df.empty:
        print("[!] No search query data found for the selected property and period.")
        return None, None, None

    # Fetch site-level totals to identify anonymised query volume
    df_site = fetch_with_cache(service, site_url, start_date, end_date, dimensions=[])
    if df_site is not None and not df_site.empty and 'clicks' in df_site.columns:
        site_total_clicks = int(df_site['clicks'].sum())
        site_total_impressions = int(df_site['impressions'].sum())
        site_overall_ctr = (site_total_clicks / site_total_impressions) if site_total_impressions > 0 else 0.0
        site_avg_pos = float(df_site['position'].mean()) if 'position' in df_site.columns else 0.0
    else:
        site_total_clicks = int(df['clicks'].sum())
        site_total_impressions = int(df['impressions'].sum())
        site_overall_ctr = (site_total_clicks / site_total_impressions) if site_total_impressions > 0 else 0.0
        site_avg_pos = 0.0

    # Ensure numeric columns are properly typed
    df['clicks'] = pd.to_numeric(df['clicks'], errors='coerce').fillna(0).astype(int)
    df['impressions'] = pd.to_numeric(df['impressions'], errors='coerce').fillna(0).astype(int)
    df['ctr'] = pd.to_numeric(df['ctr'], errors='coerce').fillna(0.0)
    df['position'] = pd.to_numeric(df['position'], errors='coerce').fillna(0.0)
    df['query'] = df['query'].astype(str)

    # 2. Enrich queries with word count and tail classifications
    df['word_count'] = df['query'].apply(lambda q: len(q.strip().split()))
    df['word_segment'] = df['word_count'].apply(classify_word_segment)
    df['volume_tier'] = df['clicks'].apply(classify_volume_tier)

    # Brand classification
    brand_terms = get_brand_terms(site_url)
    df['is_brand'] = df['query'].apply(lambda q: classify_query(q, brand_terms))

    # Overall totals
    total_queries = len(df)
    analysed_clicks = int(df['clicks'].sum())
    analysed_impressions = int(df['impressions'].sum())
    overall_ctr = (analysed_clicks / analysed_impressions) if analysed_impressions > 0 else 0.0

    anonymised_clicks = max(0, site_total_clicks - analysed_clicks)
    anonymised_impressions = max(0, site_total_impressions - analysed_impressions)
    anonymised_ctr = (anonymised_clicks / anonymised_impressions) if anonymised_impressions > 0 else 0.0
    anonymised_clicks_pct = (anonymised_clicks / site_total_clicks) if site_total_clicks > 0 else 0.0
    anonymised_impressions_pct = (anonymised_impressions / site_total_impressions) if site_total_impressions > 0 else 0.0

    # 3. Word-count segment summaries
    word_segments = ['Head', 'Mid Tail', 'Long Tail']
    word_definitions = {
        'Head': '1-2 words',
        'Mid Tail': '3-4 words',
        'Long Tail': '5+ words'
    }
    word_segments_summary = []
    for seg in word_segments:
        subset = df[df['word_segment'] == seg]
        summary_row = calculate_segment_metrics(
            subset, analysed_clicks, analysed_impressions, total_queries, seg,
            extra_fields={'words_def': word_definitions[seg]}
        )
        word_segments_summary.append(summary_row)

    # 4. Volume tier summaries (Demand curve)
    volume_tiers = [
        ('Head (High Volume)', '>= 50 clicks', df[df['clicks'] >= 50]),
        ('Mid Tail (Moderate Volume)', '5-49 clicks', df[(df['clicks'] >= 5) & (df['clicks'] < 50)]),
        ('Long Tail (Low Volume)', '1-4 clicks', df[(df['clicks'] >= 1) & (df['clicks'] < 5)]),
        ('Zero-Click Queries', '0 clicks', df[df['clicks'] == 0])
    ]
    volume_tiers_summary = []
    for tier_name, thresh_def, subset in volume_tiers:
        summary_row = calculate_segment_metrics(
            subset, analysed_clicks, analysed_impressions, total_queries, tier_name,
            extra_fields={'tier': tier_name, 'threshold_def': thresh_def}
        )
        volume_tiers_summary.append(summary_row)

    if anonymised_clicks > 0:
        volume_tiers_summary.append({
            'segment': 'Anonymised Queries',
            'tier': 'Anonymised Queries',
            'threshold_def': 'Below GSC privacy threshold',
            'query_count': 'N/A',
            'query_count_raw': 0,
            'query_pct': 'N/A',
            'clicks': format_int(anonymised_clicks),
            'clicks_raw': anonymised_clicks,
            'clicks_pct': format_pct(anonymised_clicks / site_total_clicks if site_total_clicks > 0 else 0),
            'impressions': format_int(anonymised_impressions),
            'impressions_raw': anonymised_impressions,
            'impressions_pct': format_pct(anonymised_impressions / site_total_impressions if site_total_impressions > 0 else 0),
            'ctr': format_pct(anonymised_ctr),
            'ctr_raw': anonymised_ctr,
            'position': 'N/A',
            'position_raw': 0.0,
            'brand_clicks_pct': 'N/A',
            'brand_clicks_raw': 0
        })

    # 5. Exact word length distribution (1, 2, 3, 4, 5, 6, 7+)
    exact_words_summary = []
    for w in range(1, 8):
        if w < 7:
            subset = df[df['word_count'] == w]
            label = f"{w} word{'s' if w > 1 else ''}"
            seg_name = classify_word_segment(w)
        else:
            subset = df[df['word_count'] >= 7]
            label = "7+ words"
            seg_name = "Long Tail"
        
        row_metrics = calculate_segment_metrics(
            subset, analysed_clicks, analysed_impressions, total_queries, seg_name,
            extra_fields={'label': label}
        )
        exact_words_summary.append(row_metrics)

    # 6. Top queries for interactive explorer
    df_sorted = df.sort_values(by=['clicks', 'impressions'], ascending=[False, False])
    top_queries_subset = df_sorted.head(limit).copy()
    top_queries_list = []
    for _, r in top_queries_subset.iterrows():
        top_queries_list.append({
            'query': r['query'],
            'word_count': r['word_count'],
            'word_segment': r['word_segment'],
            'volume_tier': r['volume_tier'],
            'is_brand': bool(r['is_brand']),
            'clicks': int(r['clicks']),
            'clicks_formatted': format_int(r['clicks']),
            'impressions': int(r['impressions']),
            'impressions_formatted': format_int(r['impressions']),
            'ctr_formatted': format_pct(r['ctr']),
            'position_formatted': format_float(r['position'])
        })

    # 7. Chart Data JSON
    # Word count clicks & impressions
    head_metrics = next(item for item in word_segments_summary if item['segment'] == 'Head')
    mid_metrics = next(item for item in word_segments_summary if item['segment'] == 'Mid Tail')
    long_metrics = next(item for item in word_segments_summary if item['segment'] == 'Long Tail')

    brand_head_clicks = head_metrics['brand_clicks_raw']
    nonbrand_head_clicks = max(0, head_metrics['clicks_raw'] - brand_head_clicks)
    brand_mid_clicks = mid_metrics['brand_clicks_raw']
    nonbrand_mid_clicks = max(0, mid_metrics['clicks_raw'] - brand_mid_clicks)
    brand_long_clicks = long_metrics['brand_clicks_raw']
    nonbrand_long_clicks = max(0, long_metrics['clicks_raw'] - brand_long_clicks)

    chart_data = {
        'head_clicks': head_metrics['clicks_raw'],
        'mid_clicks': mid_metrics['clicks_raw'],
        'long_clicks': long_metrics['clicks_raw'],
        'head_impressions': head_metrics['impressions_raw'],
        'mid_impressions': mid_metrics['impressions_raw'],
        'long_impressions': long_metrics['impressions_raw'],
        'brand_head_clicks': brand_head_clicks,
        'nonbrand_head_clicks': nonbrand_head_clicks,
        'brand_mid_clicks': brand_mid_clicks,
        'nonbrand_mid_clicks': nonbrand_mid_clicks,
        'brand_long_clicks': brand_long_clicks,
        'nonbrand_long_clicks': nonbrand_long_clicks,
        'word_length_labels': [row['label'] for row in exact_words_summary],
        'word_length_clicks': [row['clicks_raw'] for row in exact_words_summary],
        'word_length_impressions': [row['impressions_raw'] for row in exact_words_summary]
    }

    # 8. Setup Output Directories & File Paths
    output_dir = get_output_dir(site_url)
    os.makedirs(output_dir, exist_ok=True)
    slug = get_filename_slug(site_url)

    summary_csv_path = os.path.join(output_dir, f"head-mid-long-tail-{slug}-{start_date}-to-{end_date}-summary.csv")
    queries_csv_path = os.path.join(output_dir, f"head-mid-long-tail-{slug}-{start_date}-to-{end_date}-queries.csv")
    html_path = os.path.join(output_dir, f"head-mid-long-tail-{slug}-{start_date}-to-{end_date}.html")

    # 9. Save CSV Files
    # Summary CSV
    summary_export_rows = []
    for r in word_segments_summary:
        summary_export_rows.append({
            'Category Type': 'Lexical Word Count',
            'Segment': r['segment'],
            'Definition': r['words_def'],
            'Queries': r['query_count_raw'],
            '% of Total Queries': r['query_pct'],
            'Clicks': r['clicks_raw'],
            '% of Total Clicks': r['clicks_pct'],
            'Impressions': r['impressions_raw'],
            '% of Total Impressions': r['impressions_pct'],
            'CTR': r['ctr'],
            'Avg Position': r['position'],
            'Brand Clicks %': r['brand_clicks_pct']
        })
    for r in volume_tiers_summary:
        summary_export_rows.append({
            'Category Type': 'Demand Curve Volume Tier',
            'Segment': r['tier'],
            'Definition': r['threshold_def'],
            'Queries': r['query_count_raw'] if r.get('query_count_raw') else 'N/A',
            '% of Total Queries': r['query_pct'],
            'Clicks': r['clicks_raw'],
            '% of Total Clicks': r['clicks_pct'],
            'Impressions': r['impressions_raw'],
            '% of Total Impressions': r['impressions_pct'],
            'CTR': r['ctr'],
            'Avg Position': r['position'],
            'Brand Clicks %': r['brand_clicks_pct']
        })
    if anonymised_clicks > 0:
        summary_export_rows.append({
            'Category Type': 'Property Reconciliation',
            'Segment': 'Total Property Traffic (GSC Scorecard)',
            'Definition': 'All queries including privacy-filtered anonymised searches',
            'Queries': 'N/A',
            '% of Total Queries': '100.00%',
            'Clicks': site_total_clicks,
            '% of Total Clicks': '100.00%',
            'Impressions': site_total_impressions,
            '% of Total Impressions': '100.00%',
            'CTR': format_pct(site_overall_ctr),
            'Avg Position': format_float(site_avg_pos),
            'Brand Clicks %': 'N/A'
        })
    pd.DataFrame(summary_export_rows).to_csv(summary_csv_path, index=False, encoding='utf-8')

    # Queries CSV
    df_export = df[['query', 'word_count', 'word_segment', 'volume_tier', 'is_brand', 'clicks', 'impressions', 'ctr', 'position']].copy()
    df_export.sort_values(by=['clicks', 'impressions'], ascending=[False, False], inplace=True)
    df_export.to_csv(queries_csv_path, index=False, encoding='utf-8')

    # 10. Render and Save HTML Dashboard
    templates_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'templates'))
    env = Environment(loader=FileSystemLoader(templates_dir))
    template = env.get_template('head-mid-long-tail-template.html')

    html_content = template.render(
        page_title=f"Head, Mid & Long Tail Search Traffic - {site_url}",
        site_url=site_url,
        period_str=f"{start_date} to {end_date}",
        generation_date=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        site_total_clicks_formatted=format_int(site_total_clicks),
        site_total_impressions_formatted=format_int(site_total_impressions),
        site_overall_ctr=format_pct(site_overall_ctr),
        anonymised_clicks_raw=anonymised_clicks,
        anonymised_clicks_formatted=format_int(anonymised_clicks),
        anonymised_clicks_pct=format_pct(anonymised_clicks_pct),
        anonymised_impressions_formatted=format_int(anonymised_impressions),
        anonymised_impressions_pct=format_pct(anonymised_impressions_pct),
        analysed_clicks_formatted=format_int(analysed_clicks),
        analysed_impressions_formatted=format_int(analysed_impressions),
        total_queries_formatted=format_int(total_queries),
        total_clicks_formatted=format_int(analysed_clicks),
        total_impressions_formatted=format_int(analysed_impressions),
        overall_ctr=format_pct(overall_ctr),
        head_clicks_formatted=head_metrics['clicks'],
        head_clicks_pct=head_metrics['clicks_pct'],
        head_queries_formatted=head_metrics['query_count'],
        mid_clicks_formatted=mid_metrics['clicks'],
        mid_clicks_pct=mid_metrics['clicks_pct'],
        mid_queries_formatted=mid_metrics['query_count'],
        long_clicks_formatted=long_metrics['clicks'],
        long_clicks_pct=long_metrics['clicks_pct'],
        long_queries_formatted=long_metrics['query_count'],
        word_segments_summary=word_segments_summary,
        volume_tiers_summary=volume_tiers_summary,
        exact_words_summary=exact_words_summary,
        top_queries=top_queries_list,
        queries_display_limit=min(limit, len(top_queries_list)),
        chart_data_json=json.dumps(chart_data)
    )

    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(html_content)

    # 11. Console Output Summary
    print("\n" + "=" * 70)
    print("SEARCH TRAFFIC TAIL DISTRIBUTION SUMMARY")
    print("=" * 70)
    print(f"{'Segment':<12} {'Words':<11} {'Queries':<10} {'Clicks':<10} {'% Clicks':<10} {'CTR':<8} {'Avg Pos'}")
    print("-" * 70)
    for r in word_segments_summary:
        print(f"{r['segment']:<12} {r['words_def']:<11} {r['query_count']:<10} {r['clicks']:<10} {r['clicks_pct']:<10} {r['ctr']:<8} {r['position']}")
    print("-" * 70)
    print(f"{'Analysed':<12} {'Queries':<11} {format_int(total_queries):<10} {format_int(analysed_clicks):<10} {'100.0%':<10} {format_pct(overall_ctr):<8}")
    if anonymised_clicks > 0:
        print(f"{'Anonymised':<12} {'Privacy':<11} {'N/A':<10} {format_int(anonymised_clicks):<10} {format_pct(anonymised_clicks_pct):<10} {format_pct(anonymised_ctr):<8}")
        print(f"{'Site Total':<12} {'All Traffic':<11} {'-':<10} {format_int(site_total_clicks):<10} {'100.0%':<10} {format_pct(site_overall_ctr):<8}")
    print("=" * 70)
    print(f"Summary CSV saved to:   file://{os.path.abspath(summary_csv_path)}")
    print(f"Full Queries CSV saved: file://{os.path.abspath(queries_csv_path)}")
    print(f"HTML Dashboard saved:   file://{os.path.abspath(html_path)}")
    print("=" * 70 + "\n")

    return summary_csv_path, queries_csv_path, html_path


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Generates a Head, Mid Tail & Long Tail Search Traffic Report.')
    parser.add_argument('site_url', help='The URL/property of the site to analyse (e.g. sc-domain:example.com).')
    parser.add_argument('--start-date', help='Start date (YYYY-MM-DD).')
    parser.add_argument('--end-date', help='End date (YYYY-MM-DD).')
    parser.add_argument('--last-month', action='store_true', help='Run for the last complete calendar month.')
    parser.add_argument('--last-7-days', action='store_true', help='Run for the last 7 available days.')
    parser.add_argument('--limit', type=int, default=500, help='Limit for queries rendered in the HTML table (default: 500).')

    args = parser.parse_args()

    service = get_gsc_service()
    if service:
        start_date, end_date = parse_standard_date_args(args, service, args.site_url)
        run_report(service, args.site_url, start_date, end_date, limit=args.limit)
