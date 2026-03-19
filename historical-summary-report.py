
import os
import argparse
import pandas as pd
from urllib.parse import urlparse
import glob
import json

def create_historical_report(df, report_title, site_url, template_path='resources/report-blank.html'):
    """Generates a historical HTML report from a DataFrame using a template."""
    if not os.path.exists(template_path):
        print(f"Error: Template file not found at {template_path}")
        return None

    with open(template_path, 'r', encoding='utf-8') as f:
        template_html = f.read()

    # --- Data Preparation ---
    report_df = df.copy()
    
    # Format numbers for display in the table
    report_df['clicks'] = report_df['clicks'].apply(lambda x: f"{x:,.0f}")
    report_df['impressions'] = report_df['impressions'].apply(lambda x: f"{x:,.0f}")
    report_df['ctr'] = report_df['ctr'].apply(lambda x: f"{x:.2%}")
    report_df['position'] = report_df['position'].apply(lambda x: f"{x:,.2f}")
    report_df['queries'] = report_df['queries'].apply(lambda x: f"{x:,.0f}")
    report_df['pages'] = report_df['pages'].apply(lambda x: f"{x:,.0f}")

    # Rename and select final columns for the report table
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
    
    # --- HTML Generation ---

    # Convert DataFrame to HTML table
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

    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <script>
        const labels = {chart_labels};

        // Clicks and Impressions Chart
        new Chart(document.getElementById('clicksImpressionsChart'), {{
            type: 'line',
            data: {{
                labels: labels,
                datasets: [
                    {{
                        label: 'Total Clicks',
                        data: {chart_data['clicks']},
                        borderColor: 'rgba(75, 192, 192, 1)',
                        yAxisID: 'y'
                    }},
                    {{
                        label: 'Impressions',
                        data: {chart_data['impressions']},
                        borderColor: 'rgba(255, 99, 132, 1)',
                        yAxisID: 'y1'
                    }}
                ]
            }},
            options: {{
                responsive: true,
                plugins: {{
                    title: {{
                        display: true,
                        text: 'Clicks and Impressions Over Time'
                    }}
                }},
                scales: {{
                    y: {{
                        type: 'linear',
                        display: true,
                        position: 'left',
                        title: {{
                            display: true,
                            text: 'Clicks'
                        }}
                    }},
                    y1: {{
                        type: 'linear',
                        display: true,
                        position: 'right',
                        title: {{
                            display: true,
                            text: 'Impressions'
                        }},
                        grid: {{
                            drawOnChartArea: false
                        }}
                    }}
                }}
            }}
        }});

        // CTR and Position Chart
        new Chart(document.getElementById('ctrPositionChart'), {{
            type: 'line',
            data: {{
                labels: labels,
                datasets: [
                    {{
                        label: 'CTR',
                        data: {chart_data['ctr']},
                        borderColor: 'rgba(54, 162, 235, 1)',
                        yAxisID: 'y'
                    }},
                    {{
                        label: 'Average Position',
                        data: {chart_data['position']},
                        borderColor: 'rgba(255, 206, 86, 1)',
                        yAxisID: 'y1'
                    }}
                ]
            }},
            options: {{
                responsive: true,
                plugins: {{
                    title: {{
                        display: true,
                        text: 'CTR and Average Position Over Time'
                    }}
                }},
                scales: {{
                    y: {{
                        type: 'linear',
                        display: true,
                        position: 'left',
                        title: {{
                            display: true,
                            text: 'CTR'
                        }}
                    }},
                    y1: {{
                        type: 'linear',
                        display: true,
                        position: 'right',
                        title: {{
                            display: true,
                            text: 'Average Position'
                        }},
                        grid: {{
                            drawOnChartArea: false
                        }},
                        reverse: true
                    }}
                }}
            }}
        }});

        // Queries and Pages Chart
        new Chart(document.getElementById('queriesPagesChart'), {{
            type: 'line',
            data: {{
                labels: labels,
                datasets: [
                    {{
                        label: '# Queries',
                        data: {chart_data['queries']},
                        borderColor: 'rgba(153, 102, 255, 1)',
                        yAxisID: 'y'
                    }},
                    {{
                        label: '# Pages',
                        data: {chart_data['pages']},
                        borderColor: 'rgba(255, 159, 64, 1)',
                        yAxisID: 'y1'
                    }}
                ]
            }},
            options: {{
                responsive: true,
                plugins: {{
                    title: {{
                        display: true,
                        text: 'Unique Queries and Pages Over Time'
                    }}
                }},
                scales: {{
                    y: {{
                        type: 'linear',
                        display: true,
                        position: 'left',
                        title: {{
                            display: true,
                            text: '# Queries'
                        }}
                    }},
                    y1: {{
                        type: 'linear',
                        display: true,
                        position: 'right',
                        title: {{
                            display: true,
                            text: '# Pages'
                        }},
                        grid: {{
                            drawOnChartArea: false
                        }}
                    }}
                }}
            }}
        }});

        // Queries Chart
        new Chart(document.getElementById('queriesChart'), {{
            type: 'line',
            data: {{
                labels: labels,
                datasets: [
                    {{
                        label: '# Queries',
                        data: {chart_data['queries']},
                        borderColor: 'rgba(153, 102, 255, 1)',
                        tension: 0.1
                    }}
                ]
            }},
            options: {{
                responsive: true,
                plugins: {{
                    title: {{
                        display: true,
                        text: 'Unique Queries Over Time'
                    }}
                }}
            }}
        }});
        
        // Pages Chart
        new Chart(document.getElementById('pagesChart'), {{
            type: 'line',
            data: {{
                labels: labels,
                datasets: [
                    {{
                        label: '# Pages',
                        data: {chart_data['pages']},
                        borderColor: 'rgba(255, 159, 64, 1)',
                        tension: 0.1
                    }}
                ]
            }},
            options: {{
                responsive: true,
                plugins: {{
                    title: {{
                        display: true,
                        text: 'Unique Pages Over Time'
                    }}
                }}
            }}
        }});
    </script>
    """

    # Inject content into the template
    html_output = template_html.replace('This Report Name', report_title)
    html_output = html_output.replace('<span class="text-muted me-4">Domain name</span>', f'<span class="text-muted me-4">{site_url}</span>')
    html_output = html_output.replace('<span class="text-muted me-4">Date-range</span>', 'Historical Trend')
    
    main_content_placeholder = """    <main class="container py-4 flex-grow-1">
        <h1>Hello</h1>
        <p>Lorem ipsum dolor sit amet, consectetur adipisicing elit, sed do eiusmod
            tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam,
            quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo
            consequat. Duis aute irure dolor in reprehenderit in voluptate velit esse
            cillum dolore eu fugiat nulla pariatur. Excepteur sint occaecat cupidatat non
        proident, sunt in culpa qui officia deserunt mollit anim id est laborum.</p>
        <div class="row">
            <div class="col">
                <p>Lorem ipsum dolor sit amet, consectetur adipisicing elit, sed do eiusmod
                    tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam,
                    quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo
                    consequat. Duis aute irure dolor in reprehenderit in voluptate velit esse
                    cillum dolore eu fugiat nulla pariatur. Excepteur sint occaecat cupidatat non
                proident, sunt in culpa qui officia deserunt mollit anim id est laborum.</p>
            </div>
            <div class="col">
                <p>Lorem ipsum dolor sit amet, consectetur adipisicing elit, sed do eiusmod
                    tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam,
                    quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo
                    consequat. Duis aute irure dolor in reprehenderit in voluptate velit esse
                    cillum dolore eu fugiat nulla pariatur. Excepteur sint occaecat cupidatat non
                proident, sunt in culpa qui officia deserunt mollit anim id est laborum.</p>
            </div>
        </div>
    </main>"""

    final_main_content = f"""    <main class="container py-4 flex-grow-1">
        {chart_html}
        <div class="table-responsive mt-4">
            {table_html}
        </div>
    </main>"""
    
    html_output = html_output.replace(main_content_placeholder, final_main_content)
    
    return html_output


def main():
    parser = argparse.ArgumentParser(
        description='Generate a historical summary report from monthly GSC data.',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument('site_url', help='The URL of the site to analyse.')
    args = parser.parse_args()

    site_url = args.site_url

    if site_url.startswith('sc-domain:'):
        host_plain = site_url.replace('sc-domain:', '')
    else:
        host_plain = urlparse(site_url).netloc
    
    host_dir = host_plain.replace('www.', '')
    output_dir = os.path.join('output', host_dir)

    if not os.path.isdir(output_dir):
        print(f"Error: Output directory not found at '{output_dir}'")
        print("Please run the `monthly-summary-report.py` script first to generate the monthly data.")
        return

    # Find and read the CSV files
    file_pattern = os.path.join(output_dir, f"monthly-summary-report-{host_dir.replace('.', '-')}-*.csv")
    csv_files = glob.glob(file_pattern)

    if not csv_files:
        print(f"No monthly summary CSV files found in '{output_dir}'")
        return

    df_list = []
    for f in csv_files:
        df_list.append(pd.read_csv(f))

    df = pd.concat(df_list, ignore_index=True)
    df = df.sort_values(by='month').reset_index(drop=True)

    # Define output paths
    file_prefix = f"historical-summary-report-{host_dir.replace('.', '-')}"
    csv_output_path = os.path.join(output_dir, f'{file_prefix}.csv')
    html_output_path = os.path.join(output_dir, f'{file_prefix}.html')
    
    # Save consolidated CSV
    df.to_csv(csv_output_path, index=False)
    print(f"Successfully exported consolidated CSV to {csv_output_path}")

    # Generate and save HTML report
    report_title = f"Historical Performance Trend for {site_url}"
    html_output = create_historical_report(df, report_title, site_url)
    if html_output:
        with open(html_output_path, 'w', encoding='utf-8') as f:
            f.write(html_output)
        print(f"Successfully created HTML report at {html_output_path}")


if __name__ == '__main__':
    main()
