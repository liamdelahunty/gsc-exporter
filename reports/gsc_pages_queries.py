"""
Exports a report of queries and their corresponding pages from a Google 
Search Console property.
Refactored for modular GSC Exporter.
"""
import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import pandas as pd
from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta
from core.naming import get_output_dir, get_filename_slug
from core.cache import fetch_with_cache
from core.brand import get_brand_terms, classify_query

def generate_accordion_html(df, primary_dim, secondary_dim, report_limit, sub_table_limit, accordion_suffix=""):
    """Generates the accordion HTML for the report."""
    accordion_id = f"accordion-{primary_dim}{accordion_suffix}"
    html_parts = [f'<div class="accordion mt-3" id="{accordion_id}">']

    primary_totals = df.groupby(primary_dim).agg(
        total_clicks=('clicks', 'sum'),
        total_impressions=('impressions', 'sum')
    ).sort_values(by='total_clicks', ascending=False).head(report_limit).reset_index()

    for i, row in primary_totals.iterrows():
        primary_val = row[primary_dim]
        
        sub_df = df[df[primary_dim] == primary_val].head(sub_table_limit).copy()
        
        # Format for table display
        if secondary_dim == 'page':
            sub_df['page'] = sub_df['page'].apply(lambda x: f'<a href="{x}" target="_blank" class="text-break">{x}</a>')

        sub_df['ctr'] = sub_df['ctr'].apply(lambda x: f"{x:.2%}")
        sub_df['position'] = sub_df['position'].apply(lambda x: f"{x:.2f}")

        table_html = sub_df[[secondary_dim, 'clicks', 'impressions', 'ctr', 'position']].to_html(
            classes="table table-sm table-striped", index=False, border=0, escape=False
        )

        html_parts.append(f"""
        <div class="accordion-item">
            <h2 class="accordion-header">
                <button class="accordion-button collapsed" type="button" data-bs-toggle="collapse" data-bs-target="#collapse-{primary_dim}{accordion_suffix}-{i}">
                    <div class="d-flex w-100 align-items-center">
                        <span class="text-truncate" style="max-width: 60%;">{primary_val}</span>
                        <div class="ms-auto me-5 text-nowrap">
                            <span class="me-4">Clicks: <strong>{row['total_clicks']:,}</strong></span>
                            <span>Impressions: <strong>{row['total_impressions']:,}</strong></span>
                        </div>
                    </div>
                </button>
            </h2>
            <div id="collapse-{primary_dim}{accordion_suffix}-{i}" class="accordion-collapse collapse" data-bs-parent="#{accordion_id}">
                <div class="accordion-body">
                    {table_html}
                </div>
            </div>
        </div>
        """)
    
    html_parts.append('</div>')
    return "".join(html_parts)

def create_html_report(data_df, site_url, start_date, end_date, report_limit, sub_table_limit, brand_terms=None):
    """Generates the interactive HTML report."""
    
    # Reconstruct the command for display
    import sys
    command_str = " ".join(os.path.basename(arg) if i == 0 else arg for i, arg in enumerate(sys.argv))
    
    has_brands = brand_terms is not None and len(brand_terms) > 0
    
    brand_summary_html = ""
    brand_details_html = f"""
    <div class="alert alert-secondary">
        <strong>Report Details:</strong>
        <ul>
            <li><strong>Command:</strong> <code>{command_str}</code></li>
            <li><strong>Brand Terms Used:</strong> {', '.join(sorted(list(brand_terms))) if has_brands else 'None'}</li>
        </ul>
    </div>
    """
    
    truncation_alert_html = f"""
    <div class="alert alert-info">
        <strong>Report Truncated:</strong> To improve performance, this HTML report has been shortened.
        <ul>
            <li>The report is limited to the top <strong>{report_limit}</strong> primary items (queries/pages) by clicks.</li>
            <li>Each table within an item is limited to its top <strong>{sub_table_limit}</strong> rows.</li>
        </ul>
        The full, unfiltered data is available in the accompanying CSV file. You can adjust these limits using the <code>--report-limit</code> and <code>--sub-table-limit</code> flags.
    </div>
    """

    if has_brands:
        data_df['is_brand'] = data_df['query'].apply(lambda x: classify_query(x, brand_terms))
        brand_df = data_df[data_df['is_brand']].copy()
        non_brand_df = data_df[~data_df['is_brand']].copy()
        
        def format_ctr(clicks, impressions):
            if impressions > 0:
                return f"{clicks / impressions:.2%}"
            return "0.00%"
        
        brand_summary_html = f"""
        <div class="card mb-4">
            <div class="card-header bg-primary text-white">Brand vs. Non-Brand Performance</div>
            <div class="card-body">
                <table class="table table-sm table-bordered mb-0">
                    <thead class="table-light">
                        <tr>
                            <th>Segment</th>
                            <th class="text-end">Clicks</th>
                            <th class="text-end">Impressions</th>
                            <th class="text-end">CTR</th>
                            <th class="text-end">Unique Queries</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td><strong>Non-Brand</strong></td>
                            <td class="text-end">{non_brand_df['clicks'].sum():,}</td>
                            <td class="text-end">{non_brand_df['impressions'].sum():,}</td>
                            <td class="text-end">{format_ctr(non_brand_df['clicks'].sum(), non_brand_df['impressions'].sum())}</td>
                            <td class="text-end">{non_brand_df['query'].nunique():,}</td>
                        </tr>
                        <tr>
                            <td><strong>Brand</strong></td>
                            <td class="text-end">{brand_df['clicks'].sum():,}</td>
                            <td class="text-end">{brand_df['impressions'].sum():,}</td>
                            <td class="text-end">{format_ctr(brand_df['clicks'].sum(), brand_df['impressions'].sum())}</td>
                            <td class="text-end">{brand_df['query'].nunique():,}</td>
                        </tr>
                        <tr class="table-group-divider fw-bold">
                            <td>Total</td>
                            <td class="text-end">{data_df['clicks'].sum():,}</td>
                            <td class="text-end">{data_df['impressions'].sum():,}</td>
                            <td class="text-end">{format_ctr(data_df['clicks'].sum(), data_df['impressions'].sum())}</td>
                            <td class="text-end">{data_df['query'].nunique():,}</td>
                        </tr>
                    </tbody>
                </table>
            </div>
        </div>
        """
        
        brand_tab_html = generate_accordion_html(brand_df, 'query', 'page', report_limit, sub_table_limit, "-brand")
        non_brand_tab_html = generate_accordion_html(non_brand_df, 'query', 'page', report_limit, sub_table_limit, "-non-brand")
        
        tabs_header = """
            <li class="nav-item">
                <button class="nav-link active" id="non-brand-tab" data-bs-toggle="tab" data-bs-target="#non-brand" type="button">Non-Brand Queries</button>
            </li>
            <li class="nav-item">
                <button class="nav-link" id="brand-tab" data-bs-toggle="tab" data-bs-target="#brand" type="button">Brand Queries</button>
            </li>
            <li class="nav-item">
                <button class="nav-link" id="queries-tab" data-bs-toggle="tab" data-bs-target="#queries" type="button">All Queries</button>
            </li>
        """
        tabs_content = f"""
            <div class="tab-pane fade show active" id="non-brand" role="tabpanel">
                {non_brand_tab_html}
            </div>
            <div class="tab-pane fade" id="brand" role="tabpanel">
                {brand_tab_html}
            </div>
            <div class="tab-pane fade" id="queries" role="tabpanel">
                {generate_accordion_html(data_df, 'query', 'page', report_limit, sub_table_limit, "-all")}
            </div>
        """
    else:
        tabs_header = """
            <li class="nav-item">
                <button class="nav-link active" id="queries-tab" data-bs-toggle="tab" data-bs-target="#queries" type="button">Queries to Pages</button>
            </li>
        """
        tabs_content = f"""
            <div class="tab-pane fade show active" id="queries" role="tabpanel">
                {generate_accordion_html(data_df, 'query', 'page', report_limit, sub_table_limit)}
            </div>
        """

    html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Google Organic Pages & Queries Report: {site_url}</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"></script>
    <style>
        body {{ padding: 2rem; background-color: #f8f9fa; }}
        h1 {{ border-bottom: 2px solid #dee2e6; padding-bottom: .5rem; }}
        .table td {{ word-wrap: break-word; max-width: 500px; }}
        .text-break {{ word-break: break-all !important; }}
        .accordion-button:not(.collapsed) {{ background-color: #e7f1ff; }}
    </style>
</head>
<body>
    <div class="container-fluid">
        <h1>Google Organic Pages & Queries Report</h1>
        <p class="lead">{site_url} ({start_date} to {end_date})</p>

        {brand_summary_html}
        {brand_details_html}

        <ul class="nav nav-tabs" id="myTab" role="tablist">
            {tabs_header}
            <li class="nav-item">
                <button class="nav-link" id="pages-tab" data-bs-toggle="tab" data-bs-target="#pages" type="button">Pages to Queries</button>
            </li>
        </ul>

        <div class="tab-content" id="myTabContent">
            {tabs_content}
            <div class="tab-pane fade" id="pages" role="tabpanel">
                {generate_accordion_html(data_df, 'page', 'query', report_limit, sub_table_limit)}
            </div>
        </div>

        {truncation_alert_html}
    </div>
    <footer class="mt-5 text-center text-muted">
        <p>Generated by <a href="https://github.com/liamdelahunty/gsc-exporter" target="_blank">gsc-exporter</a></p>
    </footer>
</body>
</html>
    """
    return html_content

def run_report(service, site_url, start_date, end_date, report_limit=250, sub_table_limit=100, brand_terms=None, brand_terms_file=None, no_brand_detection=False):
    """Executes the Pages & Queries Detailed report."""
    print(f"Running GSC Pages & Queries Detailed for {site_url}...")
    
    # 1. Determine Brand Terms
    brand_terms_set = get_brand_terms(site_url, brand_terms, brand_terms_file, no_brand_detection)
    if brand_terms_set:
        print(f"  - Brand detection active. Terms: {', '.join(sorted(list(brand_terms_set))[:5])}{'...' if len(brand_terms_set) > 5 else ''}")
    
    # 2. Fetch Data
    # Dimensions: query, page
    df = fetch_with_cache(service, site_url, start_date, end_date, ['query', 'page'])
    
    if df.empty:
        print("No data found.")
        return None

    # 3. Output Paths
    output_dir = get_output_dir(site_url)
    os.makedirs(output_dir, exist_ok=True)
    slug = get_filename_slug(site_url)
    
    file_prefix = f"gsc-pages-queries-{slug}-{start_date}-to-{end_date}"
    csv_path = os.path.join(output_dir, f"{file_prefix}.csv")
    html_path = os.path.join(output_dir, f"{file_prefix}.html")

    # 4. Save CSV
    df.to_csv(csv_path, index=False, encoding='utf-8')
    
    # 5. Generate HTML
    html_content = create_html_report(df, site_url, start_date, end_date, report_limit, sub_table_limit, brand_terms_set)
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
        
    print(f"CSV saved to: {csv_path}")
    print(f"HTML saved to: {html_path}")
    return html_path

if __name__ == '__main__':
    import argparse
    from core.client import get_gsc_service
    
    parser = argparse.ArgumentParser(description='Export GSC pages and queries.')
    parser.add_argument('site_url', help='The URL of the site.')
    parser.add_argument('--start-date', help='Start date.')
    parser.add_argument('--end-date', help='End date.')
    parser.add_argument('--last-month', action='store_true', help='Run for the last calendar month.')
    parser.add_argument('--report-limit', type=int, default=250)
    parser.add_argument('--sub-table-limit', type=int, default=100)
    
    # Brand arguments
    parser.add_argument('--brand-terms', nargs='+', help='Custom brand terms.')
    parser.add_argument('--brand-terms-file', help='Path to a file containing brand terms.')
    parser.add_argument('--no-brand-detection', action='store_true', help='Disable brand detection.')
    
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
        run_report(service, args.site_url, start_date, end_date, args.report_limit, args.sub_table_limit, args.brand_terms, args.brand_terms_file, args.no_brand_detection)

