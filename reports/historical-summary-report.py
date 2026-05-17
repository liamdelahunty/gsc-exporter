"""
Generates a historical summary report from existing monthly data.
Refactored for modular GSC Exporter.
"""
import os
import pandas as pd
import glob
import json
from datetime import datetime
from core.naming import get_output_dir, get_filename_slug

def create_historical_report(df, report_title, site_url, template_path='resources/report-blank.html'):
    """Generates a historical HTML report."""
    if not os.path.exists(template_path):
        # Fallback to a basic template if resources/report-blank.html is missing
        template_html = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8"><title>{{ title }}</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
</head>
<body>
    <div class="container py-4">
        <h1>{{ title }}</h1>
        <p class="lead">{{ site_url }}</p>
        {{ content|safe }}
    </div>
</body>
</html>
"""
    else:
        with open(template_path, 'r', encoding='utf-8') as f:
            template_html = f.read()

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

    chart_html = f"""
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

    # Inject content
    if 'This Report Name' in template_html:
        html_output = template_html.replace('This Report Name', report_title)
        html_output = html_output.replace('<span class="text-muted me-4">Domain name</span>', f'<span class="text-muted me-4">{site_url}</span>')
        html_output = html_output.replace('<span class="text-muted me-4">Date-range</span>', 'Historical Trend')
        
        main_placeholder = """    <main class="container py-4 flex-grow-1">
        <h1>Hello</h1>""" # Partial match for standard template
        
        # More robust replacement for the main block
        import re
        html_output = re.sub(r'<main class="container py-4 flex-grow-1">.*?</main>', 
                            f'<main class="container py-4 flex-grow-1">{chart_html}<div class="table-responsive mt-4">{table_html}</div></main>', 
                            html_output, flags=re.DOTALL)
    else:
        # Fallback template
        html_output = template_html.replace('{{ title }}', report_title).replace('{{ site_url }}', site_url).replace('{{ content|safe }}', chart_html + table_html)
    
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
    df = df.sort_values(by='month').reset_index(drop=True)

    # Define output paths
    file_prefix = f"historical-summary-{slug}"
    csv_path = os.path.join(output_dir, f'{file_prefix}.csv')
    html_path = os.path.join(output_dir, f'{file_prefix}.html')
    
    df.to_csv(csv_path, index=False)
    
    report_title = f"Historical Performance Trend for {site_url}"
    html_output = create_historical_report(df, report_title, site_url)
    
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(html_output)
        
    print(f"Report completed: {html_path}")
    return html_path

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Historical summary report.')
    parser.add_argument('site_url', help='The URL of the site.')
    args = parser.parse_args()
    run_report(args.site_url)
