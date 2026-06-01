import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import pandas as pd
import glob
import json
from datetime import datetime
from core.naming import get_output_dir, get_filename_slug
from core.date_utils import parse_standard_date_args
from jinja2 import Environment, FileSystemLoader

def create_historical_report(df, report_title, site_url):
    """Generates a historical HTML report."""
    
    # --- Data Preparation ---
    report_df = df.copy()
    report_df['clicks'] = report_df['clicks'].apply(lambda x: f"{x:,.0f}")
    report_df['impressions'] = report_df['impressions'].apply(lambda x: f"{x:,.0f}")
    report_df['ctr'] = report_df['ctr'].apply(lambda x: f"{x:.2%}")
    report_df['position'] = report_df['position'].apply(lambda x: f"{x:,.2f}")
    report_df['queries'] = report_df['queries'].apply(lambda x: f"{x:,.0f}")
    report_df['pages'] = report_df['pages'].apply(lambda x: f"{x:,.0f}")

    report_df = report_df.rename(columns={
        'month': 'Month',
        'clicks': 'Total Clicks',
        'impressions': 'Impressions',
        'ctr': 'CTR',
        'position': 'Avg. Position',
        'queries': '# Queries',
        'pages': '# Pages'
    })

    final_columns = ['Month', 'Total Clicks', 'Impressions', 'CTR', 'Avg. Position', '# Queries', '# Pages']
    report_df = report_df[final_columns]
    
    table_html = report_df.to_html(classes="table table-striped table-hover", index=False, border=0)

    # --- Chart Generation ---
    chart_labels = json.dumps(df['month'].tolist())
    chart_data = {
        'clicks': json.dumps(df['clicks'].tolist()),
        'impressions': json.dumps(df['impressions'].tolist()),
        'ctr': json.dumps(df['ctr'].tolist()),
        'position': json.dumps(df['position'].tolist()),
        'queries': json.dumps(df['queries'].tolist()),
        'pages': json.dumps(df['pages'].tolist()),
    }

    chart_html_content = f"""
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <div class="row">
        <div class="col-md-6"><canvas id="clicksImpressionsChart"></canvas></div>
        <div class="col-md-6"><canvas id="ctrPositionChart"></canvas></div>
    </div>
    <div class="row mt-4">
        <div class="col-md-6"><canvas id="queriesPagesChart"></canvas></div>
        <div class="col-md-6"><canvas id="queriesChart"></canvas></div>
    </div>
    <div class="row mt-4">
        <div class="col-md-6"><canvas id="pagesChart"></canvas></div>
    </div>

    <script>
        const labels = {chart_labels};
        new Chart(document.getElementById('clicksImpressionsChart'), {{
            type: 'line',
            data: {{
                labels: labels,
                datasets: [
                    {{ label: 'Total Clicks', data: {chart_data['clicks']}, borderColor: 'rgba(75, 192, 192, 1)', yAxisID: 'y' }},
                    {{ label: 'Impressions', data: {chart_data['impressions']}, borderColor: 'rgba(255, 99, 132, 1)', yAxisID: 'y1' }}
                ]
            }},
            options: {{
                responsive: true,
                scales: {{
                    y: {{ type: 'linear', display: true, position: 'left', title: {{ display: true, text: 'Clicks' }} }},
                    y1: {{ type: 'linear', display: true, position: 'right', title: {{ display: true, text: 'Impressions' }}, grid: {{ drawOnChartArea: false }} }}
                }}
            }}
        }});

        new Chart(document.getElementById('ctrPositionChart'), {{
            type: 'line',
            data: {{
                labels: labels,
                datasets: [
                    {{ label: 'CTR', data: {chart_data['ctr']}, borderColor: 'rgba(54, 162, 235, 1)', yAxisID: 'y' }},
                    {{ label: 'Avg. Position', data: {chart_data['position']}, borderColor: 'rgba(255, 206, 86, 1)', yAxisID: 'y1' }}
                ]
            }},
            options: {{
                responsive: true,
                scales: {{
                    y: {{ type: 'linear', display: true, position: 'left', title: {{ display: true, text: 'CTR' }} }},
                    y1: {{ type: 'linear', display: true, position: 'right', title: {{ display: true, text: 'Avg. Position' }}, grid: {{ drawOnChartArea: false }}, reverse: true }}
                }}
            }}
        }});
        
        new Chart(document.getElementById('queriesPagesChart'), {{
            type: 'line',
            data: {{
                labels: labels,
                datasets: [
                    {{ label: '# Queries', data: {chart_data['queries']}, borderColor: 'rgba(153, 102, 255, 1)', yAxisID: 'y' }},
                    {{ label: '# Pages', data: {chart_data['pages']}, borderColor: 'rgba(255, 159, 64, 1)', yAxisID: 'y1' }}
                ]
            }},
            options: {{
                responsive: true,
                scales: {{
                    y: {{ type: 'linear', display: true, position: 'left', title: {{ display: true, text: '# Queries' }} }},
                    y1: {{ type: 'linear', display: true, position: 'right', title: {{ display: true, text: '# Pages' }}, grid: {{ drawOnChartArea: false }} }}
                }}
            }}
        }});
    </script>
    """

    template_loader = FileSystemLoader('resources')
    env = Environment(loader=template_loader)
    template = env.get_template('report-blank.html')

    html_output = template.render(
        title=report_title,
        report_name=report_title,
        domain_name=site_url,
        date_range="Historical Trend",
        main_content=chart_html_content + f'<div class="table-responsive mt-4">{table_html}</div>'
    )
    
    return html_output

def run_report(site_url):
    """Executes the historical summary report."""
    print(f"Running Historical Summary Report for {site_url}...")
    
    output_dir = get_output_dir(site_url)
    slug = get_filename_slug(site_url)

    if not os.path.isdir(output_dir):
        print(f"Error: Output directory not found at '{output_dir}'")
        return None

    # Find and read the monthly summary CSV files
    # Note: This depends on the naming convention of the monthly summary report
    file_pattern = os.path.join(output_dir, f"monthly-summary-report-{slug}-*.csv")
    csv_files = glob.glob(file_pattern)

    if not csv_files:
        print(f"No monthly summary CSV files found in '{output_dir}'")
        return None

    df_list = []
    for f in csv_files:
        try:
            df_list.append(pd.read_csv(f))
        except Exception as e:
            print(f"Warning: Could not read {f}: {e}")

    if not df_list:
        return None

    df = pd.concat(df_list, ignore_index=True)
    
    # Ensure 'month' column exists before sorting
    if 'month' not in df.columns:
        # Try to extract month from filename if it's missing in CSV
        # This is a fallback for older versions of the monthly summary
        print("Warning: 'month' column missing. Attempting to derive from data...")
        # (Assuming the monthly summary has at least one date or we can infer it)
        # For now, let's just fail gracefully with a better message if we can't find it.
        if 'date' in df.columns:
            df['month'] = pd.to_datetime(df['date']).dt.strftime('%Y-%m')
        else:
             print("Error: Could not find 'month' or 'date' column in CSV files.")
             return None

    df = df.sort_values(by='month').reset_index(drop=True)

    # Define output paths
    file_prefix = f"historical-summary-{slug}"
    csv_path = os.path.join(output_dir, f'{file_prefix}.csv')
    html_path = os.path.join(output_dir, f'{file_prefix}.html')
    
    df.to_csv(csv_path, index=False, encoding='utf-8')
    
    report_title = f"Historical Performance Trend for {site_url}"
    html_output = create_historical_report(df, report_title, site_url)
    
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(html_output)
        
    print(f"CSV saved to: {csv_path}")
    print(f"HTML saved to: {html_path}")
    return html_path

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Historical summary report.')
    parser.add_argument('site_url', help='The URL of the site.')
    parser.add_argument('--start-date', help='Start date (YYYY-MM-DD).')
    parser.add_argument('--end-date', help='End date (YYYY-MM-DD).')
    parser.add_argument('--last-7-days', action='store_true', help='Run for the last 7 available days.')
    parser.add_argument('--last-month', action='store_true', help='Run for the last calendar month.')
    
    args = parser.parse_args()
    # Parse dates for compatibility, even if not used for filtering yet
    parse_standard_date_args(args, service, args.site_url)
    
    run_report(args.site_url)
