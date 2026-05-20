"""
Generates a report that highlights keyword cannibalisation issues.
Refactored for modular GSC Exporter.
"""
import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import pandas as pd
import html
from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta
from core.naming import get_output_dir, get_filename_slug
from core.cache import fetch_with_cache

def generate_accordion_html(report_df, top_100_cannibalised):
    """Generates the Bootstrap accordion HTML for the report."""
    accordion_id = "cannibalisationAccordion"
    header = """
    <div class="row fw-bold border-bottom pb-2 mb-2">
        <div class="col-md-6">Keyword</div>
        <div class="col-md-2 text-end">Clicks</div>
        <div class="col-md-2 text-end">Impressions</div>
        <div class="col-md-2 text-end">Pages</div>
    </div>
    """
    html_parts = [header, f'<div class="accordion" id="{accordion_id}">']

    for index, summary_row in top_100_cannibalised.iterrows():
        query = summary_row['query']
        total_clicks = summary_row['total_clicks']
        total_impressions = summary_row['total_impressions']
        page_count = summary_row['page_count']

        collapse_id = f"collapse-{index}"
        header_id = f"header-{index}"
        
        pages_for_query_df = report_df[report_df['query'] == query].copy()
        pages_for_query_df.sort_values(by=['clicks', 'impressions'], ascending=[False, False], inplace=True)

        sub_group_html_df = pages_for_query_df.copy()
        sub_group_html_df['page'] = sub_group_html_df['page'].apply(lambda x: f'<a href="{x}" target="_blank">{x}</a>')
        sub_group_html_df['ctr'] = sub_group_html_df['ctr'].apply(lambda x: f"{x:.2%}")
        sub_group_html_df['position'] = sub_group_html_df['position'].apply(lambda x: f"{x:.2f}")
        sub_group_html_df['clicks'] = sub_group_html_df['clicks'].apply(lambda x: f"{x:,.0f}")
        sub_group_html_df['impressions'] = sub_group_html_df['impressions'].apply(lambda x: f"{x:,.0f}")

        sub_table_html = sub_group_html_df[['page', 'clicks', 'impressions', 'ctr', 'position']].to_html(
            classes="table table-sm table-striped", index=False, border=0, escape=False
        )

        accordion_item = f"""
        <div class="accordion-item">
            <h2 class="accordion-header" id="{header_id}">
                <button class="accordion-button collapsed" type="button" data-bs-toggle="collapse" data-bs-target="#{collapse_id}">
                    <div class="row w-100 align-items-center">
                        <div class="col-md-6 text-start"><strong>{html.escape(query)}</strong></div>
                        <div class="col-md-2 text-end">{total_clicks:,.0f}</div>
                        <div class="col-md-2 text-end">{total_impressions:,.0f}</div>
                        <div class="col-md-2 text-end">{page_count}</div>
                    </div>
                </button>
            </h2>
            <div id="{collapse_id}" class="accordion-collapse collapse" data-bs-parent="#{accordion_id}">
                <div class="accordion-body"><div class="table-responsive">{sub_table_html}</div></div>
            </div>
        </div>
        """
        html_parts.append(accordion_item)

    html_parts.append('</div>')
    return "".join(html_parts)

def create_html_report(site_url, start_date, end_date, report_df, top_100_cannibalised):
    """Generates the full HTML report."""
    report_title = "Keyword Cannibalisation Report"
    accordion_html = generate_accordion_html(report_df, top_100_cannibalised)

    return f"""
<!DOCTYPE html><html lang="en-GB"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{report_title}: {site_url}</title><link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
<style>body {{ padding-top: 5rem; }} .accordion-button:not(.collapsed) {{ background-color: #e7f1ff; }}</style></head>
<body><header class="navbar navbar-expand-lg navbar-light bg-light border-bottom mb-4 fixed-top"><div class="container-fluid">
<h1 class="h3 mb-0 me-4">{report_title}</h1><span class="text-muted me-4">{site_url}</span><span class="text-muted">{start_date} to {end_date}</span>
</div></header><main class="container-fluid py-4">{accordion_html}</main>
<footer class="footer mt-auto py-3 bg-light border-top text-center"><p class="text-muted mb-0">Report generated on {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p></footer>
<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"></script></body></html>"""

def run_report(service, site_url, start_date, end_date):
    """Executes the Keyword Cannibalisation report."""
    print(f"Running Keyword Cannibalisation Report for {site_url}...")
    
    df = fetch_with_cache(service, site_url, start_date, end_date, ['query', 'page'])
    
    if df.empty:
        print("No data found.")
        return None

    # Cannibalisation Logic
    query_summary = df.groupby('query').agg(
        page_count=('page', 'nunique'),
        total_clicks=('clicks', 'sum'),
        total_impressions=('impressions', 'sum')
    ).reset_index()

    cannibalised = query_summary[query_summary['page_count'] > 1].copy()
    if cannibalised.empty:
        print("No cannibalisation found.")
        return None

    top_100 = cannibalised.sort_values(by='total_impressions', ascending=False).head(100)
    top_queries = top_100['query'].tolist()
    report_df = df[df['query'].isin(top_queries)].copy()
    report_df['query'] = pd.Categorical(report_df['query'], categories=top_queries, ordered=True)
    report_df.sort_values(by=['query', 'clicks'], ascending=[True, False], inplace=True)

    output_dir = get_output_dir(site_url)
    os.makedirs(output_dir, exist_ok=True)
    slug = get_filename_slug(site_url)
    
    file_prefix = f"cannibalisation-{slug}-{start_date}-to-{end_date}"
    csv_path = os.path.join(output_dir, f"{file_prefix}.csv")
    html_path = os.path.join(output_dir, f"{file_prefix}.html")

    report_df.to_csv(csv_path, index=False)
    html_content = create_html_report(site_url, start_date, end_date, report_df, top_100)
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
        
    print(f"Report completed: {html_path}")
    return html_path

if __name__ == '__main__':
    import argparse
    from core.client import get_gsc_service
    parser = argparse.ArgumentParser(description='Keyword cannibalisation report.')
    parser.add_argument('site_url', help='The site URL.')
    parser.add_argument('--start-date', help='Start date.')
    parser.add_argument('--end-date', help='End date.')
    parser.add_argument('--last-month', action='store_true', help='Run for the last calendar month.')
    args = parser.parse_args()
    
    if args.last_month:
        today = date.today()
        # Last month
        end_date_dt = today.replace(day=1) - relativedelta(days=1)
        start_date_dt = end_date_dt.replace(day=1)
        start_date = start_date_dt.strftime('%Y-%m-%d')
        end_date = end_date_dt.strftime('%Y-%m-%d')
    else:
        start_date = args.start_date
        end_date = args.end_date

    service = get_gsc_service()
    if service:
        run_report(service, args.site_url, start_date, end_date)
