"""
Generates a monthly Google Search Console performance report by search type.
Adapted for the modular GSC Exporter.
"""
import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import pandas as pd
from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta
from functools import reduce
from jinja2 import Environment
from core.naming import get_output_dir, get_filename_slug
from core.cache import fetch_with_cache

SEARCH_TYPES = ['web', 'image', 'video', 'news', 'discover', 'googleNews']

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ report_title }}</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body { padding-top: 56px; }
        h1, h2, h3 { padding-bottom: .5rem; }
        h2 { border-bottom: 2px solid #dee2e6; padding-bottom: .5rem; margin-top: 2rem; }
        .table thead th { background-color: #434343; color: #ffffff; text-align: left; }
        footer { margin-top: 3rem; text-align: center; color: #6c757d; }
    </style>
</head>
<body>
    <header class="navbar navbar-expand-lg navbar-light bg-light border-bottom mb-4 fixed-top">
        <div class="container-fluid">
            <h1 class="h3 mb-0">{{ report_title }}</h1>
        </div>
    </header>
    <main class="container-fluid py-4 flex-grow-1">
        <p class="text-muted">Analysis for the period: {{ date_range }}</p>

        <div class="card my-4">
            <div class="card-header"><h3>Total Clicks vs. Total Impressions</h3></div>
            <div class="card-body" style="height: 400px;"><canvas id="performanceChart"></canvas></div>
        </div>

        <div class="card my-4">
            <div class="card-header"><h3>Clicks by Search Type Over Time (Stacked)</h3></div>
            <div class="card-body" style="height: 400px;"><canvas id="clicksStackedChart"></canvas></div>
        </div>
        <div class="card my-4">
            <div class="card-header"><h3>Impressions by Search Type Over Time (Stacked)</h3></div>
            <div class="card-body" style="height: 400px;"><canvas id="impressionsStackedChart"></canvas></div>
        </div>
        
        <h2 class="mt-5">Overall Summary</h2>
        <div class="card mb-4">
            <div class="card-header"><h3>Performance Overview</h3></div>
            <div class="card-body">
                {{ summary_table|safe }}
            </div>
        </div>

        <h2>Monthly Data Table</h2>
        <div class="table-responsive">{{ data_table|safe }}</div>
    </main>
    <footer class="footer mt-auto py-3 bg-light">
        <div class="container text-center">
            <span class="text-muted">Report generated on {{ generation_date }}. <a href="https://github.com/liamdelahunty/gsc-exporter" target="_blank">gsc-exporter</a></span>
        </div>
    </footer>
    <script>
        const chartData = {{ chart_data|safe }};
        const labels = chartData.map(row => row.month);
        const searchTypes = {{ search_types|tojson }};
        const colors = [
            'rgba(54, 162, 235, 1)', 'rgba(255, 99, 132, 1)', 'rgba(75, 192, 192, 1)',
            'rgba(153, 102, 255, 1)', 'rgba(255, 159, 64, 1)', 'rgba(255, 205, 86, 1)'
        ];

        // Clicks vs Impressions Chart
        new Chart(document.getElementById('performanceChart'), {
            type: 'line',
            data: {
                labels: labels,
                datasets: [
                    {
                        label: 'Total Clicks',
                        data: chartData.map(row => row.total_clicks),
                        borderColor: 'rgba(54, 162, 235, 1)',
                        backgroundColor: 'rgba(54, 162, 235, 0.2)',
                        yAxisID: 'yClicks',
                        fill: false,
                        tension: 0.1
                    },
                    {
                        label: 'Total Impressions',
                        data: chartData.map(row => row.total_impressions),
                        borderColor: 'rgba(255, 99, 132, 1)',
                        backgroundColor: 'rgba(255, 99, 132, 0.2)',
                        yAxisID: 'yImpressions',
                        fill: false,
                        tension: 0.1
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: { mode: 'index', intersect: false },
                scales: {
                    yClicks: {
                        type: 'linear',
                        display: true,
                        position: 'left',
                        title: { display: true, text: 'Total Clicks' }
                    },
                    yImpressions: {
                        type: 'linear',
                        display: true,
                        position: 'right',
                        title: { display: true, text: 'Total Impressions' },
                        grid: { drawOnChartArea: false }
                    }
                }
            }
        });

        // Stacked Area Charts
        const stackedClicksDatasets = searchTypes.map((st, index) => ({
            label: st + ' Clicks',
            data: chartData.map(row => row[st + '_clicks'] || 0),
            borderColor: colors[index % colors.length],
            backgroundColor: colors[index % colors.length],
            fill: true,
            tension: 0.1
        }));

        new Chart(document.getElementById('clicksStackedChart'), {
            type: 'line',
            data: { labels: labels, datasets: stackedClicksDatasets },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: { mode: 'index', intersect: false },
                scales: { y: { stacked: true, beginAtZero: true } }
            }
        });

        const stackedImpressionsDatasets = searchTypes.map((st, index) => ({
            label: st + ' Impressions',
            data: chartData.map(row => row[st + '_impressions'] || 0),
            borderColor: colors[index % colors.length],
            backgroundColor: colors[index % colors.length],
            fill: true,
            tension: 0.1
        }));

        new Chart(document.getElementById('impressionsStackedChart'), {
            type: 'line',
            data: { labels: labels, datasets: stackedImpressionsDatasets },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: { mode: 'index', intersect: false },
                scales: { y: { stacked: true, beginAtZero: true } }
            }
        });
    </script>
</body>
</html>
"""

def create_search_type_report_html(df, report_title, date_range, site_url):
    """Generates a search type performance HTML report from a DataFrame."""
    df_html = df.copy()
    df_html.fillna(0, inplace=True)
    
    styles = [dict(selector="td", props=[("text-align", "right")])]

    # Overall Summary Table
    summary_data = []
    grand_total_clicks = 0
    grand_total_impressions = 0

    available_search_types = [st for st in SEARCH_TYPES if f'{st}_clicks' in df_html.columns]

    for st in available_search_types:
        clicks = df_html[f'{st}_clicks'].sum()
        impressions = df_html[f'{st}_impressions'].sum()
        ctr = (clicks / impressions) if impressions else 0
        summary_data.append({
            'Metric': st,
            'Clicks': f"{clicks:,.0f}",
            'Impressions': f"{impressions:,.0f}",
            'CTR': f"{ctr:.2%}"
        })
        grand_total_clicks += clicks
        grand_total_impressions += impressions
    
    total_ctr = (grand_total_clicks / grand_total_impressions) if grand_total_impressions else 0
    summary_data.append({
        'Metric': 'Total',
        'Clicks': f"{grand_total_clicks:,.0f}",
        'Impressions': f"{grand_total_impressions:,.0f}",
        'CTR': f"{total_ctr:.2%}"
    })
    
    summary_df = pd.DataFrame(summary_data)
    summary_table = summary_df.style.set_table_attributes('class="table table-bordered table-sm"').set_table_styles(styles).hide(axis='index').to_html()

    # Format numeric columns for display
    data_table_df = df_html.copy()
    for col in data_table_df.columns:
        if 'clicks' in col or 'impressions' in col:
            data_table_df[col] = data_table_df[col].apply(lambda x: f"{int(x):,}")
        elif 'ctr' in col:
            data_table_df[col] = data_table_df[col].apply(lambda x: f"{x:.2%}" if pd.notnull(x) and x != 0 else '0.00%')

    # Rename columns for presentation
    column_rename_map = {
        'month': 'Month',
        'web_clicks': 'Web Clicks', 'web_impressions': 'Web Impressions', 'web_ctr': 'Web CTR',
        'image_clicks': 'Image Clicks', 'image_impressions': 'Image Impressions', 'image_ctr': 'Image CTR',
        'video_clicks': 'Video Clicks', 'video_impressions': 'Video Impressions', 'video_ctr': 'Video CTR',
        'news_clicks': 'News Clicks', 'news_impressions': 'News Impressions', 'news_ctr': 'News CTR',
        'discover_clicks': 'Discover Clicks', 'discover_impressions': 'Discover Impressions', 'discover_ctr': 'Discover CTR',
        'googleNews_clicks': 'Google News Clicks', 'googleNews_impressions': 'Google News Impressions', 'googleNews_ctr': 'Google News CTR',
        'total_clicks': 'Total Clicks', 'total_impressions': 'Total Impressions', 'total_ctr': 'Total CTR',
    }
    
    existing_columns_to_rename = {k: v for k, v in column_rename_map.items() if k in data_table_df.columns}
    data_table_df = data_table_df.rename(columns=existing_columns_to_rename)
    data_table = data_table_df.to_html(classes="dataframe table table-striped table-hover", index=False, border=0)

    chart_df = df_html.sort_values('month').copy()
    chart_data = chart_df.to_json(orient='records')
    
    template = Environment().from_string(HTML_TEMPLATE)
    html_content = template.render(
        report_title=report_title,
        site_url=site_url,
        date_range=date_range,
        summary_table=summary_table,
        data_table=data_table,
        chart_data=chart_data,
        search_types=available_search_types,
        generation_date=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    )
    
    return html_content

def run_report(service, site_url, start_date, end_date):
    """Executes the monthly search type performance report."""
    print(f"Running Monthly Search Type Performance Report for {site_url}...")
    
    all_monthly_dfs = []
    for st in SEARCH_TYPES:
        # Use fetch_with_cache which handles monthly fragmentation and date dimensions
        # Note: fetch_with_cache aggregates by the provided dimensions. 
        # Here we want a monthly breakdown, so we need 'date' in dimensions to group by month later.
        df_st = fetch_with_cache(service, site_url, start_date, end_date, ['date'], st)
        if not df_st.empty:
            df_st['month'] = pd.to_datetime(df_st['date']).dt.strftime('%Y-%m')
            # Aggregate by month
            monthly_df = df_st.groupby('month').agg({
                'clicks': 'sum',
                'impressions': 'sum'
            }).reset_index()
            monthly_df.rename(columns={
                'clicks': f'{st}_clicks',
                'impressions': f'{st}_impressions'
            }, inplace=True)
            monthly_df[f'{st}_ctr'] = monthly_df[f'{st}_clicks'] / monthly_df[f'{st}_impressions']
            all_monthly_dfs.append(monthly_df)
            
    if not all_monthly_dfs:
        print("No data found for any search type.")
        return None

    # 2. Merge all dataframes on month
    merged_df = reduce(lambda left, right: pd.merge(left, right, on='month', how='outer'), all_monthly_dfs)
    merged_df.fillna(0, inplace=True)
    
    # Calculate totals
    for col_type in ['clicks', 'impressions']:
        cols_to_sum = [f'{st}_{col_type}' for st in SEARCH_TYPES if f'{st}_{col_type}' in merged_df.columns]
        merged_df[f'total_{col_type}'] = merged_df[cols_to_sum].sum(axis=1)

    merged_df['total_ctr'] = merged_df['total_clicks'] / merged_df['total_impressions']
    merged_df = merged_df.sort_values('month', ascending=False)

    # 3. Define Output Paths
    output_dir = get_output_dir(site_url)
    os.makedirs(output_dir, exist_ok=True)
    slug = get_filename_slug(site_url)
    
    file_prefix = f"monthly-search-type-performance-{slug}-{start_date[:7]}-to-{end_date[:7]}"
    csv_path = os.path.join(output_dir, f"{file_prefix}.csv")
    html_path = os.path.join(output_dir, f"{file_prefix}.html")
    
    # 4. Save CSV
    merged_df.to_csv(csv_path, index=False, encoding='utf-8')
    
    # 5. Generate HTML
    report_title = f"Monthly Search Type Performance for {site_url}"
    date_range_str = f"{start_date[:7]} to {end_date[:7]}"
    html_content = create_search_type_report_html(merged_df, report_title, date_range_str, site_url)
    
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
        
    print(f"CSV saved to: {csv_path}")
    print(f"HTML saved to: {html_path}")
    return html_path

if __name__ == '__main__':
    import argparse
    from core.client import get_gsc_service
    
    parser = argparse.ArgumentParser(description='Generate a monthly performance report by search type.')
    parser.add_argument('site_url', help='The URL of the site to analyse.')
    parser.add_argument('--start-date', help='Start date (YYYY-MM-DD).')
    parser.add_argument('--end-date', help='End date (YYYY-MM-DD).')
    parser.add_argument('--last-month', action='store_true', help='Run for the last calendar month.')
    
    args = parser.parse_args()
    
    if args.last_month:
        today = date.today()
        # Last month
        end_date_dt = today.replace(day=1) - relativedelta(days=1)
        start_date_dt = end_date_dt.replace(day=1) - relativedelta(months=15)
        start_date = start_date_dt.strftime('%Y-%m-%d')
        end_date = end_date_dt.strftime('%Y-%m-%d')
    else:
        start_date = args.start_date
        end_date = args.end_date
    
    service = get_gsc_service()
    if service:
        run_report(service, args.site_url, start_date, end_date)
