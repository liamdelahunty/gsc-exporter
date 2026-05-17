"""
Generates a page-level report with key performance metrics and unique query counts.
Adapted for the modular GSC Exporter.
"""
import os
import pandas as pd
from datetime import datetime
from core.naming import get_output_dir, get_filename_slug
from core.cache import fetch_with_cache

def create_html_report(df, report_title, period_str, summary_data, limit=None, total_rows=None, search_type='web'):
    """Generates an HTML report from the DataFrame."""
    df_html = df.copy()

    # Format numeric columns
    df_html['clicks'] = pd.to_numeric(df_html['clicks'], errors='coerce').fillna(0).astype(int)
    df_html['impressions'] = pd.to_numeric(df_html['impressions'], errors='coerce').fillna(0).astype(int)
    df_html['ctr'] = pd.to_numeric(df_html['ctr'], errors='coerce').fillna(0.0)
    df_html['position'] = pd.to_numeric(df_html['position'], errors='coerce').fillna(0.0)
    
    if 'Query #' in df_html.columns:
        df_html['Query #'] = pd.to_numeric(df_html['Query #'], errors='coerce').fillna(0).astype(int)

    df_html['clicks'] = df_html['clicks'].apply(lambda x: f"{x:,}") 
    df_html['impressions'] = df_html['impressions'].apply(lambda x: f"{x:,}") 
    df_html['ctr'] = df_html['ctr'].apply(lambda x: f"{x:.2%}") 
    df_html['position'] = df_html['position'].apply(lambda x: f"{x:.2f}") 

    if 'Query #' in df_html.columns:
        df_html['Query #'] = df_html['Query #'].apply(lambda x: f"{x:,}")

    truncation_alert_html = ""
    if limit is not None and total_rows is not None and total_rows > limit:
        truncation_alert_html = f"""
        <div class="alert alert-info">
            <strong>Report Truncated:</strong> This HTML report is showing the top <strong>{limit:,}</strong> pages out of a total of <strong>{total_rows:,}</strong>.
            The full, unfiltered data is available in the accompanying CSV file.
        </div>
        """

    header_cols_html = ['<div class="col-6">Page</div>']
    if search_type == 'discover':
        header_cols_html.extend([
            '<div class="col-2 text-end">Clicks</div>',
            '<div class="col-2 text-end">Impressions</div>',
            '<div class="col-2 text-end">CTR</div>'
        ])
    else:
        header_cols_html.extend([
            '<div class="col-1 text-end">Clicks</div>',
            '<div class="col-1 text-end">Impressions</div>',
            '<div class="col-1 text-end">CTR</div>',
            '<div class="col-1 text-end">Pos</div>',
            '<div class="col-2 text-end">Query #</div>'
        ])

    table_header = f"""
<div class="container-fluid px-4">
  <div class="row fw-bold py-2 bg-dark text-white rounded-top">
    {''.join(header_cols_html)}
  </div>
"""

    table_body = ""
    for i, row in df_html.reset_index(drop=True).iterrows():
        bg_class = "bg-light" if i % 2 == 0 else ""
        row_cols_html = []
        
        page_url = row["page"]
        row_cols_html.append(f'<div class="col-6" style="word-wrap: break-word; overflow-wrap: break-word;"><a href="{page_url}" target="_blank" class="text-break">{page_url}</a></div>')

        if search_type == 'discover':
            row_cols_html.extend([
                f'<div class="col-2 text-end">{row["clicks"]}</div>',
                f'<div class="col-2 text-end">{row["impressions"]}</div>',
                f'<div class="col-2 text-end">{row["ctr"]}</div>'
            ])
        else:
            row_cols_html.extend([
                f'<div class="col-1 text-end">{row["clicks"]}</div>',
                f'<div class="col-1 text-end">{row["impressions"]}</div>',
                f'<div class="col-1 text-end">{row["ctr"]}</div>',
                f'<div class="col-1 text-end">{row["position"]}</div>',
                f'<div class="col-2 text-end">{row.get("Query #", "0")}</div>'
            ])

        table_body += f"""
  <div class="row py-2 border-bottom {bg_class}">
    {''.join(row_cols_html)}
  </div>
"""

    summary_html = "<h2 class='mt-5'>Overall Summary</h2><table class='table table-bordered' style='max-width: 500px;'>"
    for key, value in summary_data.items():
        summary_html += f"<tr><th style='width: 50%;'>{key}</th><td>{value}</td></tr>"
    summary_html += "</table>"
    
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
        h2 {{ border-bottom: 2px solid #dee2e6; padding-bottom: .5rem; margin-top: 2rem; }}
        .text-break {{ word-break: break-all !important; }}
        footer {{ margin-top: 3rem; text-align: center; color: #6c757d; }}
    </style>
</head>
<body>
    <div class="container-fluid">
        <h1>{report_title}</h1>
        <p class="text-muted">Analysis for the period: {period_str}</p>
        {truncation_alert_html}
        {table_header + table_body + '</div>'}
        {summary_html}
    </div>
    <footer class="footer mt-auto py-3 bg-light">
        <div class="container text-center">
            <span class="text-muted">Report generated on {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}. <a href="https://github.com/liamdelahunty/gsc-exporter" target="_blank">gsc-exporter</a></span>
        </div>
    </footer>
</body>
</html>
"""

def run_report(service, site_url, start_date, end_date, search_type='web', limit=250, strip_query_strings=False):
    """Executes the page-level report."""
    print(f"Running Page-Level Report for {site_url} ({start_date} to {end_date})...")
    
    # 1. Fetch Page Data
    df_pages = fetch_with_cache(service, site_url, start_date, end_date, ['page'], search_type)
    if df_pages.empty:
        print("No page data found.")
        return None
        
    # 2. Fetch Page-Query Data for Unique Counts (if not Discover)
    df_page_query = pd.DataFrame()
    if search_type != 'discover':
        df_page_query = fetch_with_cache(service, site_url, start_date, end_date, ['page', 'query'], search_type)
    
    # 3. Handle Query String Stripping
    if strip_query_strings:
        df_pages['page'] = df_pages['page'].str.split('?').str[0]
        df_pages = df_pages.groupby('page').agg({
            'clicks': 'sum',
            'impressions': 'sum',
            'position': 'mean'
        }).reset_index()
        df_pages['ctr'] = df_pages['clicks'] / df_pages['impressions']
        
        if not df_page_query.empty:
            df_page_query['page'] = df_page_query['page'].str.split('?').str[0]

    # 4. Calculate Unique Query Counts
    if not df_page_query.empty:
        query_counts = df_page_query.groupby('page')['query'].nunique().reset_index()
        query_counts.rename(columns={'query': 'query_count'}, inplace=True)
        df_pages = pd.merge(df_pages, query_counts, on='page', how='left')
        df_pages['query_count'] = df_pages['query_count'].fillna(0)
    else:
        df_pages['query_count'] = 0

    # 5. Final Data Prep
    df_pages = df_pages.sort_values(by='clicks', ascending=False)
    
    # 6. Define Output Paths
    output_dir = get_output_dir(site_url)
    os.makedirs(output_dir, exist_ok=True)
    slug = get_filename_slug(site_url)
    
    filename_suffix = "-no-query" if strip_query_strings else ""
    search_type_suffix = f"-{search_type}" if search_type != 'web' else ""
    file_prefix = f"page-level-report-{slug}{search_type_suffix}-{start_date}-to-{end_date}{filename_suffix}"
    
    csv_path = os.path.join(output_dir, f"{file_prefix}.csv")
    html_path = os.path.join(output_dir, f"{file_prefix}.html")
    
    # 7. Save CSV
    df_pages.to_csv(csv_path, index=False)
    
    # 8. Summary Data
    total_clicks = df_pages['clicks'].sum()
    total_impressions = df_pages['impressions'].sum()
    avg_ctr = total_clicks / total_impressions if total_impressions > 0 else 0
    avg_pos = (df_pages['impressions'] * df_pages['position']).sum() / total_impressions if total_impressions > 0 else 0
    total_unique_queries = df_page_query['query'].nunique() if not df_page_query.empty else 0
    
    summary_data = {
        "Number of Pages": f"{len(df_pages):,}",
        "Total Clicks": f"{total_clicks:,.0f}",
        "Total Impressions": f"{total_impressions:,.0f}",
        "Average CTR": f"{avg_ctr:.2%}",
        "Average Position": f"{avg_pos:.2f}",
        "Total Unique Queries": f"{total_unique_queries:,}"
    }

    # 9. Generate HTML
    df_pages_renamed = df_pages.rename(columns={'query_count': 'Query #'})
    html_content = create_html_report(
        df=df_pages_renamed.head(limit),
        report_title=f"{search_type.capitalize()} Page-Level Report",
        period_str=f"{start_date} to {end_date}",
        summary_data=summary_data,
        limit=limit,
        total_rows=len(df_pages),
        search_type=search_type
    )
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
        
    print(f"Report completed: {html_path}")
    return html_path

if __name__ == '__main__':
    import argparse
    from core.client import get_gsc_service
    
    parser = argparse.ArgumentParser(description='Generate a page-level report.')
    parser.add_argument('site_url', help='The URL of the site to analyse.')
    parser.add_argument('--search-type', default='web', help='The search type (web, discover, etc.).')
    parser.add_argument('--start-date', help='Start date (YYYY-MM-DD).')
    parser.add_argument('--end-date', help='End date (YYYY-MM-DD).')
    parser.add_argument('--limit', type=int, default=250, help='Limit for HTML report.')
    parser.add_argument('--strip-query-strings', action='store_true', help='Remove query strings.')
    
    args = parser.parse_args()
    
    service = get_gsc_service()
    if service:
        # Default to last month if dates not provided
        if not args.start_date or not args.end_date:
            from datetime import date
            from dateutil.relativedelta import relativedelta
            today = date.today()
            end_date_dt = today.replace(day=1) - relativedelta(days=1)
            start_date_dt = end_date_dt.replace(day=1)
            start_date = start_date_dt.strftime('%Y-%m-%d')
            end_date = end_date_dt.strftime('%Y-%m-%d')
        else:
            start_date = args.start_date
            end_date = args.end_date
            
        run_report(service, args.site_url, start_date, end_date, 
                   args.search_type, args.limit, args.strip_query_strings)
