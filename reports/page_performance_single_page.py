"""
Generates a report showing the performance of a single page over the last 16 months.
Adapted for the modular GSC Exporter.
"""
import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import pandas as pd
import re
from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta
from urllib.parse import urlparse
from core.naming import get_output_dir, get_filename_slug
from core.cache import fetch_with_cache
from core.date_utils import parse_standard_date_args

def find_covering_site(service, page_url):
    """
    Finds the most appropriate GSC site property that covers the given page_url.
    """
    sites = []
    try:
        site_list = service.sites().list().execute()
        if 'siteEntry' in site_list:
            sites = [s['siteUrl'] for s in site_list['siteEntry']]
    except Exception as e:
        print(f"Error fetching sites: {e}")
        return None

    parsed_page_url = urlparse(page_url)
    page_domain = parsed_page_url.netloc

    potential_matches = []
    for site in sites:
        if site.startswith('sc-domain:'):
            site_domain = site.replace('sc-domain:', '')
            if page_domain == site_domain or page_domain.endswith(f".{site_domain}"):
                potential_matches.append((site, len(site_domain), "domain"))
        else: # URL prefix property
            if page_url.startswith(site):
                potential_matches.append((site, len(site), "prefix"))
            elif page_domain == urlparse(site).netloc:
                 potential_matches.append((site, len(urlparse(site).netloc), "domain_fallback"))

    potential_matches.sort(key=lambda x: (x[2] == "prefix", x[1]), reverse=True)

    if potential_matches:
        return potential_matches[0][0]
    return None

def create_html_report(page_url, site_url, start_date, end_date, df_combined):
    """Generates an HTML report from the pivoted dataframes."""
    report_title = f"Page Performance Over Time Report for {page_url}"

    # Prepare data for the chart
    page_data_clicks = df_combined['clicks'].loc[page_url].to_dict()
    page_data_impressions = df_combined['impressions'].loc[page_url].to_dict()
    page_data_ctr = df_combined['ctr'].loc[page_url].to_dict()
    page_data_position = df_combined['position'].loc[page_url].to_dict()

    chart_data_list = []
    for month in sorted(page_data_clicks.keys()):
        chart_data_list.append({
            'month': month,
            'clicks': page_data_clicks.get(month, 0),
            'impressions': page_data_impressions.get(month, 0),
            'ctr': page_data_ctr.get(month, 0.0),
            'position': page_data_position.get(month, 0.0)
        })
    chart_data_json = pd.DataFrame(chart_data_list).to_json(orient='records')

    # Create table data
    df_table = df_combined.loc[page_url].unstack(level=0)
    df_table = df_table[['clicks', 'impressions', 'ctr', 'position']]
    df_table.index.name = 'Month'
    df_table = df_table.reset_index()

    # Format for display
    df_html = df_table.copy()
    df_html['clicks'] = df_html['clicks'].apply(lambda x: f"{int(x):,}")
    df_html['impressions'] = df_html['impressions'].apply(lambda x: f"{int(x):,}")
    df_html['ctr'] = df_html['ctr'].apply(lambda x: f"{x:.2%}")
    df_html['position'] = df_html['position'].apply(lambda x: f"{x:.2f}")

    table_html = df_html.to_html(classes="table table-striped table-hover", index=False, border=0)

    template = """
<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{0}</title><link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<style>
body {{ padding-top: 56px; background-color: #f8f9fa; }}
h2 {{ border-bottom: 2px solid #dee2e6; padding-bottom: .5rem; margin-top: 2rem; }}
.chart-container {{ position: relative; height: 300px; width: 100%; }}
footer {{ margin-top: 3rem; text-align: center; color: #6c757d; }}
</style></head>
<body>
    <header class="navbar navbar-expand-lg navbar-light bg-light border-bottom mb-4 fixed-top">
        <div class="container-fluid"><h1 class="h3 mb-0">{0}</h1></div>
    </header>
    <main class="container py-4">
        <p class="mb-3">Page: <a href="{4}" target="_blank">{4}</a></p>
        <p class="text-muted">Site: {1} | Period: {2} to {3}</p>
        
        <div class="row my-4">
            <div class="col-12"><div class="card"><div class="card-header">Clicks vs. Impressions</div>
            <div class="card-body chart-container"><canvas id="clicksChart"></canvas></div></div></div>
        </div>
        
        <div class="row my-4">
            <div class="col-md-6"><div class="card"><div class="card-header">CTR %</div>
            <div class="card-body chart-container"><canvas id="ctrChart"></canvas></div></div></div>
            <div class="col-md-6"><div class="card"><div class="card-header">Average Position</div>
            <div class="card-body chart-container"><canvas id="posChart"></canvas></div></div></div>
        </div>

        <h2>Monthly Performance Data</h2>
        <div class="table-responsive">{6}</div>
    </main>
    <footer><p>Report generated on {7}. <a href="https://github.com/liamdelahunty/gsc-exporter" target="_blank">gsc-exporter</a></p></footer>
    <script>
        const data = {5};
        const labels = data.map(row => row.month);
        
        new Chart(document.getElementById('clicksChart'), {{
            type: 'line',
            data: {{
                labels: labels,
                datasets: [
                    {{ label: 'Clicks', data: data.map(row => row.clicks), borderColor: '#4285F4', yAxisID: 'y' }},
                    {{ label: 'Impressions', data: data.map(row => row.impressions), borderColor: '#DB4437', yAxisID: 'y1' }}
                ]
            }},
            options: {{ responsive: true, maintainAspectRatio: false, scales: {{ y: {{ position: 'left' }}, y1: {{ position: 'right', grid: {{ drawOnChartArea: false }} }} }} }}
        }});

        new Chart(document.getElementById('ctrChart'), {{
            type: 'line',
            data: {{ labels: labels, datasets: [{{ label: 'CTR %', data: data.map(row => row.ctr * 100), borderColor: '#0F9D58' }}] }},
            options: {{ responsive: true, maintainAspectRatio: false }}
        }});

        new Chart(document.getElementById('posChart'), {{
            type: 'line',
            data: {{ labels: labels, datasets: [{{ label: 'Position', data: data.map(row => row.position), borderColor: '#F4B400' }}] }},
            options: {{ responsive: true, maintainAspectRatio: false, scales: {{ y: {{ reverse: true }} }} }}
        }});
    </script>
</body></html>
"""
    return template.format(
        report_title, site_url, start_date, end_date, page_url,
        chart_data_json, table_html, datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    )

def run_report(service, page_url, site_url=None, start_date=None, end_date=None, months=16):
    """Executes the single page performance report."""
    if not site_url:
        print(f"Finding GSC property for {page_url}...")
        site_url = find_covering_site(service, page_url)
        
    if not site_url:
        print(f"Could not find a property for {page_url}")
        return None
        
    print(f"Running Single Page Report for {page_url} (Site: {site_url}, {months} months ending {end_date})...")
    
    # 2. Fetch Historical Data
    all_monthly_data = []
    base_end_dt = datetime.strptime(end_date, '%Y-%m-%d')

    for i in range(months):
        month_dt = base_end_dt - relativedelta(months=i)
        m_start = month_dt.strftime('%Y-%m-01')
        m_end = (month_dt + relativedelta(months=1) - timedelta(days=1)).strftime('%Y-%m-%d')
        if i == 0:
            m_end = end_date # Respect exact end_date for the target month
        
        df_month = fetch_with_cache(service, site_url, m_start, m_end, ['page'])
        if not df_month.empty:
            df_page = df_month[df_month['page'] == page_url].copy()
            if not df_page.empty:
                df_page['month'] = month_dt.strftime('%Y-%m')
                all_monthly_data.append(df_page)

    if not all_monthly_data:
        print(f"No data found for {page_url}")
        return None

    df_historical = pd.concat(all_monthly_data, ignore_index=True)
    
    # Pivot for report
    df_pivot_clicks = df_historical.pivot_table(index='page', columns='month', values='clicks', aggfunc='sum').fillna(0)
    df_pivot_impressions = df_historical.pivot_table(index='page', columns='month', values='impressions', aggfunc='sum').fillna(0)
    df_pivot_ctr = df_historical.pivot_table(index='page', columns='month', values='ctr', aggfunc='mean').fillna(0)
    df_pivot_position = df_historical.pivot_table(index='page', columns='month', values='position', aggfunc='mean').fillna(0)

    df_combined = pd.concat([df_pivot_clicks, df_pivot_impressions, df_pivot_ctr, df_pivot_position], 
                            keys=['clicks', 'impressions', 'ctr', 'position'], axis=1)

    # 3. Define Output Paths
    output_dir = get_output_dir(site_url)
    os.makedirs(output_dir, exist_ok=True)
    
    # Slug for page
    page_path = urlparse(page_url).path.strip('/')
    page_slug = re.sub(r'[^a-zA-Z0-9_-]', '-', page_path) if page_path else 'index'
    page_slug = re.sub(r'-+', '-', page_slug).strip('-')
    
    file_prefix = f"page-performance-single-{page_slug}-{end_date}"
    csv_path = os.path.join(output_dir, f"{file_prefix}.csv")
    html_path = os.path.join(output_dir, f"{file_prefix}.html")
    
    df_combined.to_csv(csv_path, encoding='utf-8')
    
    # 4. Generate HTML
    html_content = create_html_report(page_url, site_url, start_date, end_date, df_combined)
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
        
    print(f"CSV saved to: {csv_path}")
    print(f"HTML saved to: {html_path}")
    return html_path

if __name__ == '__main__':
    import argparse
    from core.client import get_gsc_service
    
    parser = argparse.ArgumentParser(description='Performance of a single page over time.')
    parser.add_argument('site_url', nargs='?', help='The GSC property URL.')
    parser.add_argument('page_url', help='The URL of the page to analyse.')
    parser.add_argument('--site-url', dest='site_url_opt', help='The GSC property URL (optional flag).')
    
    parser.add_argument('--start-date', help='Start date (YYYY-MM-DD).')
    parser.add_argument('--end-date', help='End date (YYYY-MM-DD).')
    parser.add_argument('--last-month', action='store_true', help='Run for the last calendar month.')
    parser.add_argument('--months', type=int, default=16, help='Number of months for historical lookback.')
    
    args = parser.parse_args()
    start_date, end_date = parse_standard_date_args(args)
    
    # Determine the actual site_url and page_url from both positional and optional args
    final_site_url = args.site_url_opt if args.site_url_opt else args.site_url
    final_page_url = args.page_url

    service = get_gsc_service()
    if service:
        run_report(service, final_page_url, site_url=final_site_url, 
                   start_date=start_date, end_date=end_date, months=args.months)

