"""
Generates a daily analysis matrix of Google Search Console performance data (such as Discover, Web, or News traffic),
showing daily trends, daily clicks/impressions matrices, and popular days tracking.
"""
import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import json
import pandas as pd
from datetime import datetime, timedelta
from core.naming import get_output_dir, get_filename_slug
from core.cache import fetch_with_cache
from core.date_utils import (
    get_latest_available_date,
    get_last_month_range,
    get_last_7_days_range
)

def format_cell_value(val):
    """Formats values for matrix cells. Displays as blank if missing/NaN."""
    if pd.isna(val) or val is None:
        return ""
    return f"{int(val):,}"

def generate_matrix_headers(df_matrix, value_col_name):
    """Generates the HTML table headers for the matrix table."""
    headers = []
    # Sticky page column
    headers.append('<th class="col-sticky-page">Page URL</th>')
    # Popular Days
    headers.append('<th class="text-center" title="Number of days this page was in the top X stories">Popular Days</th>')
    # Total Clicks / Total Impressions
    headers.append(f'<th class="text-end">{value_col_name}</th>')
    
    # Date headers
    date_cols = [col for col in df_matrix.columns if col not in ['page', 'Popular Days', value_col_name]]
    for date_col in date_cols:
        try:
            dt = datetime.strptime(date_col, "%Y-%m-%d")
            formatted_date = dt.strftime("%d<br>%b")
        except Exception:
            formatted_date = date_col
        headers.append(f'<th class="text-end font-monospace date-header" title="Full date: {date_col}">{formatted_date}</th>')
        
    return f'<tr>{"".join(headers)}</tr>'

def generate_matrix_rows(df_matrix, value_col_name):
    """Generates the HTML table body rows for the matrix table."""
    rows_html = []
    for _, row in df_matrix.iterrows():
        page = row['page']
        pop_days = int(row['Popular Days'])
        total_val = int(row[value_col_name])
        
        display_page = page.replace("https://", "").replace("http://", "")
        if len(display_page) > 75:
            display_page = display_page[:72] + "..."
            
        cells = []
        # Page cell (sticky)
        cells.append(f"""
        <td class="col-sticky-page">
            <a href="{page}" target="_blank" title="{page}" class="story-link">
                {display_page}
                <svg class="external-link-icon" xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"></path><polyline points="15 3 21 3 21 9"></polyline><line x1="10" y1="14" x2="21" y2="3"></line></svg>
            </a>
        </td>
        """)
        # Popular Days
        cells.append(f'<td class="text-center fw-semibold text-accent">{pop_days}</td>')
        # Total Value
        cells.append(f'<td class="text-end fw-semibold">{total_val:,}</td>')
        
        # Date cells
        date_cols = [col for col in df_matrix.columns if col not in ['page', 'Popular Days', value_col_name]]
        for date_col in date_cols:
            val = row[date_col]
            formatted_val = format_cell_value(val)
            cell_class = "cell-empty" if formatted_val == "" else "cell-value"
            cells.append(f'<td class="text-end {cell_class}">{formatted_val}</td>')
            
        rows_html.append(f'<tr class="matrix-row">{"".join(cells)}</tr>')
        
    return "\n".join(rows_html)

def create_html_report(site_url, start_date, end_date, df_daily_complete, df_clicks_matrix, df_impressions_matrix, search_type):
    """Generates a premium light-mode HTML dashboard displaying daily GSC trends and matrices."""
    # Global KPIs
    total_clicks = int(df_daily_complete['clicks'].sum())
    total_impressions = int(df_daily_complete['impressions'].sum())
    avg_ctr = total_clicks / total_impressions if total_impressions > 0 else 0
    collated_stories_count = len(df_clicks_matrix)

    clicks_str = f"{total_clicks:,}"
    impressions_str = f"{total_impressions:,}"
    ctr_str = f"{avg_ctr:.2%}"

    # Trend Chart Data
    chart_data = df_daily_complete.sort_values('date_dt').copy()
    chart_dates = chart_data['date'].tolist()
    chart_clicks = chart_data['clicks'].tolist()
    chart_impressions = chart_data['impressions'].tolist()

    # Generate matrix HTML contents
    clicks_headers = generate_matrix_headers(df_clicks_matrix, 'Total Clicks')
    clicks_rows = generate_matrix_rows(df_clicks_matrix, 'Total Clicks')
    impressions_headers = generate_matrix_headers(df_impressions_matrix, 'Total Impressions')
    impressions_rows = generate_matrix_rows(df_impressions_matrix, 'Total Impressions')

    # Dynamic titles based on search type
    report_title = f"{search_type.capitalize()} Daily Performance Matrix" if search_type != 'discover' else "Google Discover Daily Analysis"

    # Reconstruct the command line used to generate this report
    script_name = os.path.basename(sys.argv[0]) if (hasattr(sys, 'argv') and sys.argv) else "discover_daily_analysis.py"
    cmd_args = sys.argv[1:] if (hasattr(sys, 'argv') and len(sys.argv) > 1) else []
    command_line = f"python reports/{script_name} {' '.join(cmd_args)}"

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{report_title} for {site_url}</title>
    
    <!-- Google Fonts -->
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Outfit:wght@400;500;600;700;800&display=swap" rel="stylesheet">
    
    <!-- Bootstrap CSS -->
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
    
    <!-- Chart.js -->
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>

    <style>
        :root {{
            --bg-primary: #f8fafc;
            --bg-secondary: #f1f5f9;
            --bg-card: #ffffff;
            --border-color: #e2e8f0;
            --text-main: #0f172a;
            --text-muted: #64748b;
            --text-muted-light: #475569;
            --accent-blue: #0284c7;
            --accent-blue-rgb: 2, 132, 199;
            --accent-purple: #7c3aed;
            --accent-purple-rgb: 124, 58, 237;
            --accent-green: #059669;
            --accent-green-rgb: 5, 150, 105;
            --shadow-sm: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
            --shadow-md: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -2px rgba(0, 0, 0, 0.05);
            --shadow-lg: 0 10px 15px -3px rgba(0, 0, 0, 0.04), 0 4px 6px -4px rgba(0, 0, 0, 0.04);
            --font-outfit: 'Outfit', sans-serif;
            --font-inter: 'Inter', sans-serif;
        }}

        body {{
            background-color: var(--bg-primary);
            color: var(--text-main);
            font-family: var(--font-inter);
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            overflow-x: hidden;
        }}

        .dashboard-header {{
            background: linear-gradient(180deg, #ffffff 0%, var(--bg-primary) 100%);
            border-bottom: 1px solid var(--border-color);
            padding: 2.5rem 0;
            position: relative;
        }}

        .site-title {{
            font-family: var(--font-outfit);
            font-weight: 800;
            letter-spacing: -0.025em;
            background: linear-gradient(135deg, #0f172a 30%, #0284c7 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            font-size: 2.25rem;
            margin-bottom: 0.5rem;
        }}

        .date-range-pill {{
            background: #ffffff;
            border: 1px solid var(--border-color);
            color: var(--accent-blue);
            font-weight: 600;
            font-size: 0.875rem;
            padding: 0.4rem 1rem;
            border-radius: 9999px;
            display: inline-flex;
            align-items: center;
            gap: 0.5rem;
            font-family: var(--font-outfit);
            box-shadow: var(--shadow-sm);
        }}

        .kpi-card {{
            background-color: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 1rem;
            padding: 1.5rem;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            position: relative;
            overflow: hidden;
            box-shadow: var(--shadow-sm);
        }}

        .kpi-card:hover {{
            transform: translateY(-4px);
            box-shadow: var(--shadow-md);
        }}

        .kpi-card.clicks-card {{
            background-color: #f0f9ff;
            border-color: #bae6fd;
        }}

        .kpi-card.impressions-card {{
            background-color: #f5f3ff;
            border-color: #ddd6fe;
        }}

        .kpi-card.ctr-card {{
            background-color: #ecfdf5;
            border-color: #a7f3d0;
        }}

        .kpi-label {{
            color: var(--text-muted);
            font-size: 0.875rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            margin-bottom: 0.5rem;
            font-family: var(--font-outfit);
        }}

        .kpi-value {{
            font-family: var(--font-outfit);
            font-size: 2.25rem;
            font-weight: 700;
            line-height: 1.2;
        }}

        .text-clicks {{ color: var(--accent-blue); }}
        .text-impressions {{ color: var(--accent-purple); }}
        .text-ctr {{ color: var(--accent-green); }}

        .chart-card {{
            background-color: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 1rem;
            padding: 1.75rem;
            box-shadow: var(--shadow-sm);
        }}

        .chart-card-header {{
            margin-bottom: 1.5rem;
        }}

        .chart-card-title {{
            font-family: var(--font-outfit);
            font-weight: 700;
            font-size: 1.25rem;
            color: var(--text-main);
        }}

        .chart-container {{
            position: relative;
            height: 350px;
            width: 100%;
        }}

        /* Tabs and Tables */
        .matrix-section {{
            margin-top: 3.5rem;
        }}

        .matrix-controls-bar {{
            display: flex;
            flex-wrap: wrap;
            justify-content: space-between;
            align-items: center;
            gap: 1.5rem;
            margin-bottom: 1.5rem;
            border-bottom: 1px solid var(--border-color);
            padding-bottom: 1rem;
        }}

        .nav-tabs-custom {{
            border-bottom: none;
            display: flex;
            gap: 0.5rem;
        }}

        .tab-btn {{
            background: transparent;
            border: 1px solid transparent;
            color: var(--text-muted-light);
            font-family: var(--font-outfit);
            font-weight: 600;
            font-size: 0.95rem;
            padding: 0.5rem 1.25rem;
            border-radius: 0.5rem;
            transition: all 0.2s;
            cursor: pointer;
        }}

        .tab-btn:hover {{
            color: var(--text-main);
            background: rgba(0, 0, 0, 0.05);
        }}

        .tab-btn.active {{
            background: var(--bg-secondary);
            border-color: var(--border-color);
            color: var(--accent-blue);
            box-shadow: var(--shadow-sm);
        }}

        .search-bar {{
            max-width: 360px;
            width: 100%;
        }}

        .search-input {{
            background: #ffffff;
            border: 1px solid var(--border-color);
            border-radius: 0.5rem;
            color: var(--text-main);
            font-size: 0.875rem;
            padding: 0.5rem 1.25rem;
            width: 100%;
            transition: all 0.2s;
        }}

        .search-input:focus {{
            outline: none;
            border-color: var(--accent-blue);
            box-shadow: 0 0 0 2px rgba(2, 132, 199, 0.15);
        }}

        .matrix-table-wrapper {{
            background-color: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 1rem;
            overflow-x: auto;
            max-height: 650px;
            overflow-y: auto;
            box-shadow: var(--shadow-sm);
        }}

        .matrix-table {{
            width: max-content;
            min-width: 100%;
            margin-bottom: 0;
            border-collapse: separate;
            border-spacing: 0;
        }}

        .matrix-table th {{
            position: sticky;
            top: 0;
            z-index: 10;
            background-color: #f8fafc;
            color: var(--text-muted);
            font-size: 0.75rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            font-weight: 700;
            padding: 1rem 0.85rem;
            border-bottom: 2px solid var(--border-color);
        }}

        .matrix-table td {{
            padding: 0.75rem 0.85rem;
            vertical-align: middle;
            border-bottom: 1px solid #f1f5f9;
            font-size: 0.825rem;
        }}

        .matrix-row {{
            transition: background-color 0.15s;
        }}

        .matrix-row:hover {{
            background-color: #f8fafc;
        }}

        /* Sticky Columns */
        .matrix-table th.col-sticky-page,
        .matrix-table td.col-sticky-page {{
            position: sticky;
            left: 0;
            z-index: 2;
            background-color: #ffffff;
            border-right: 2px solid var(--border-color);
            box-shadow: 4px 0 8px rgba(0, 0, 0, 0.03);
            max-width: 320px;
            min-width: 280px;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }}

        .matrix-table th.col-sticky-page {{
            background-color: #f8fafc;
            z-index: 11;
        }}

        .matrix-table tr:hover td.col-sticky-page {{
            background-color: #f8fafc;
        }}

        .story-link {{
            color: #0284c7;
            text-decoration: none;
            transition: color 0.15s;
            display: inline-flex;
            align-items: center;
            gap: 0.35rem;
        }}

        .story-link:hover {{
            color: #0369a1;
            text-decoration: underline;
        }}

        .external-link-icon {{
            opacity: 0;
            transition: opacity 0.15s;
            color: var(--accent-blue);
        }}

        .story-link:hover .external-link-icon {{
            opacity: 0.8;
        }}

        .text-accent {{
            color: var(--accent-blue);
        }}

        .cell-empty {{
            color: #cbd5e1;
            font-weight: 300;
        }}

        .cell-value {{
            font-weight: 500;
        }}

        .tab-content-panel {{
            display: none;
        }}

        .tab-content-panel.show {{
            display: block;
        }}

        .date-header {{
            min-width: 65px;
            line-height: 1.2;
        }}

        /* Command Line Display */
        .command-card {{
            background-color: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 0.75rem;
            padding: 1.25rem 1.5rem;
            box-shadow: var(--shadow-sm);
        }}
        .command-label {{
            font-size: 0.75rem;
            font-weight: 700;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 0.05em;
            margin-bottom: 0.5rem;
            font-family: var(--font-outfit);
        }}
        .command-box {{
            background-color: var(--bg-secondary);
            border: 1px solid var(--border-color);
            border-radius: 0.5rem;
            padding: 0.75rem 1rem;
            overflow-x: auto;
        }}
        .command-text {{
            color: var(--accent-blue);
            font-family: monospace;
            font-size: 0.85rem;
            white-space: nowrap;
        }}

        /* Footer */
        footer {{
            margin-top: auto;
            padding: 2.5rem 0;
            border-top: 1px solid var(--border-color);
            background-color: #ffffff;
            font-size: 0.825rem;
            color: var(--text-muted);
            font-family: var(--font-outfit);
        }}

        footer a {{
            color: var(--accent-blue);
            text-decoration: none;
        }}

        footer a:hover {{
            text-decoration: underline;
        }}

        @media (max-width: 768px) {{
            .site-title {{
                font-size: 1.75rem;
            }}
            .kpi-value {{
                font-size: 1.75rem;
            }}
            .chart-container {{
                height: 280px;
            }}
        }}
    </style>
</head>
<body>

    <!-- Header -->
    <header class="dashboard-header">
        <div class="container">
            <div class="row align-items-center">
                <div class="col-lg-8 text-center text-lg-start">
                    <h1 class="site-title">{report_title}</h1>
                    <p class="text-muted mb-0">Daily performance metrics matrix for <span class="fw-semibold text-dark">{site_url}</span></p>
                </div>
                <div class="col-lg-4 text-center text-lg-end mt-3 mt-lg-0">
                    <div class="date-range-pill">
                        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="4" width="18" height="18" rx="2" ry="2"></rect><line x1="16" y1="2" x2="16" y2="6"></line><line x1="8" y1="2" x2="8" y2="6"></line><line x1="3" y1="10" x2="21" y2="10"></line></svg>
                        {start_date} to {end_date}
                    </div>
                </div>
            </div>
        </div>
    </header>

    <!-- Main Content -->
    <main class="container py-5">
        
        <!-- KPIs Row -->
        <div class="row g-4 mb-5">
            <div class="col-md-3">
                <div class="kpi-card clicks-card">
                    <div class="kpi-label">Total Clicks</div>
                    <div class="kpi-value text-clicks">{clicks_str}</div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="kpi-card impressions-card">
                    <div class="kpi-label">Total Impressions</div>
                    <div class="kpi-value text-impressions">{impressions_str}</div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="kpi-card ctr-card">
                    <div class="kpi-label">Average CTR</div>
                    <div class="kpi-value text-ctr">{ctr_str}</div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="kpi-card">
                    <div class="kpi-label">Collated Stories</div>
                    <div class="kpi-value text-dark">{collated_stories_count}</div>
                </div>
            </div>
        </div>

        <!-- Chart Card -->
        <div class="row mb-5">
            <div class="col-12">
                <div class="chart-card">
                    <div class="chart-card-header d-flex justify-content-between align-items-center">
                        <h2 class="chart-card-title mb-0">Daily Trends</h2>
                        <span class="text-muted small">Hover on lines to view details</span>
                    </div>
                    <div class="chart-container">
                        <canvas id="dailyPerformanceChart"></canvas>
                    </div>
                </div>
            </div>
        </div>

        <!-- Matrix Breakdown Section -->
        <div class="matrix-section">
            <div class="matrix-controls-bar">
                <div class="nav-tabs-custom">
                    <button class="tab-btn active" onclick="switchTab('clicksPanel', this)">Clicks Matrix</button>
                    <button class="tab-btn" onclick="switchTab('impressionsPanel', this)">Impressions Matrix</button>
                </div>
                <div class="search-bar">
                    <input type="text" id="matrixSearch" class="search-input" placeholder="Search pages..." oninput="filterMatrix()">
                </div>
            </div>

            <!-- Clicks Matrix Panel -->
            <div id="clicksPanel" class="tab-content-panel show">
                <div class="matrix-table-wrapper">
                    <table class="table table-borderless matrix-table">
                        <thead>
                            {clicks_headers}
                        </thead>
                        <tbody>
                            {clicks_rows}
                        </tbody>
                    </table>
                </div>
            </div>

            <!-- Impressions Matrix Panel -->
            <div id="impressionsPanel" class="tab-content-panel">
                <div class="matrix-table-wrapper">
                    <table class="table table-borderless matrix-table">
                        <thead>
                            {impressions_headers}
                        </thead>
                        <tbody>
                            {impressions_rows}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>

        <!-- Command Line Info -->
        <div class="row mt-5 mb-4">
            <div class="col-12">
                <div class="command-card">
                    <div class="command-label">Command used to generate this report:</div>
                    <div class="command-box">
                        <code class="command-text">{command_line}</code>
                    </div>
                </div>
            </div>
        </div>

    </main>

    <!-- Footer -->
    <footer class="footer">
        <div class="container text-center">
            <span>Report generated on {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}. Powered by <a href="https://github.com/liamdelahunty/gsc-exporter" target="_blank">gsc-exporter</a></span>
        </div>
    </footer>

    <!-- Interactive Scripts -->
    <script>
        // Tab switching
        function switchTab(panelId, btn) {{
            document.querySelectorAll('.tab-content-panel').forEach(p => p.classList.remove('show'));
            document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
            
            document.getElementById(panelId).classList.add('show');
            btn.classList.add('active');
        }}

        // Row filtering
        function filterMatrix() {{
            const query = document.getElementById('matrixSearch').value.toLowerCase().trim();
            const rows = document.querySelectorAll('.matrix-row');
            
            rows.forEach(row => {{
                const pageLink = row.querySelector('.story-link');
                if (pageLink) {{
                    const title = pageLink.getAttribute('title').toLowerCase();
                    if (title.includes(query)) {{
                        row.style.display = '';
                    }} else {{
                        row.style.display = 'none';
                    }}
                }}
            }});
        }}

        // Chart.js Setup
        const chartCtx = document.getElementById('dailyPerformanceChart').getContext('2d');
        
        const blueGradient = chartCtx.createLinearGradient(0, 0, 0, 320);
        blueGradient.addColorStop(0, 'rgba(2, 132, 199, 0.10)');
        blueGradient.addColorStop(1, 'rgba(2, 132, 199, 0.00)');

        const purpleGradient = chartCtx.createLinearGradient(0, 0, 0, 320);
        purpleGradient.addColorStop(0, 'rgba(124, 58, 237, 0.08)');
        purpleGradient.addColorStop(1, 'rgba(124, 58, 237, 0.00)');

        const chartLabels = {json.dumps(chart_dates)};
        const clicksData = {json.dumps(chart_clicks)};
        const impressionsData = {json.dumps(chart_impressions)};

        new Chart(chartCtx, {{
            type: 'line',
            data: {{
                labels: chartLabels.map(d => {{
                    const dateObj = new Date(d);
                    return dateObj.toLocaleDateString('en-GB', {{ day: 'numeric', month: 'short' }});
                }}),
                datasets: [
                    {{
                        label: 'Clicks',
                        data: clicksData,
                        borderColor: '#0284c7',
                        backgroundColor: blueGradient,
                        borderWidth: 3,
                        pointBackgroundColor: '#0284c7',
                        pointBorderColor: '#ffffff',
                        pointHoverBackgroundColor: '#ffffff',
                        pointHoverBorderColor: '#0284c7',
                        pointRadius: 4,
                        pointHoverRadius: 6,
                        yAxisID: 'yClicks',
                        fill: true,
                        tension: 0.35
                    }},
                    {{
                        label: 'Impressions',
                        data: impressionsData,
                        borderColor: '#7c3aed',
                        backgroundColor: purpleGradient,
                        borderWidth: 3,
                        pointBackgroundColor: '#7c3aed',
                        pointBorderColor: '#ffffff',
                        pointHoverBackgroundColor: '#ffffff',
                        pointHoverBorderColor: '#7c3aed',
                        pointRadius: 4,
                        pointHoverRadius: 6,
                        yAxisID: 'yImpressions',
                        fill: true,
                        tension: 0.35
                    }}
                ]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                interaction: {{
                    mode: 'index',
                    intersect: false
                }},
                plugins: {{
                    legend: {{
                        position: 'top',
                        labels: {{
                            color: '#475569',
                            font: {{
                                family: "'Outfit', sans-serif",
                                size: 12,
                                weight: '500'
                            }},
                            boxWidth: 15,
                            usePointStyle: true,
                            pointStyle: 'circle'
                        }}
                    }},
                    tooltip: {{
                        backgroundColor: '#ffffff',
                        titleColor: '#0f172a',
                        bodyColor: '#334155',
                        borderColor: '#e2e8f0',
                        borderWidth: 1,
                        padding: 12,
                        boxPadding: 6,
                        cornerRadius: 8,
                        titleFont: {{
                            family: "'Outfit', sans-serif",
                            weight: 'bold'
                        }},
                        bodyFont: {{
                            family: "'Inter', sans-serif"
                        }},
                        callbacks: {{
                            label: function(context) {{
                                let label = context.dataset.label || '';
                                if (label) {{
                                    label += ': ';
                                }}
                                if (context.parsed.y !== null) {{
                                    label += new Intl.NumberFormat('en-GB').format(context.parsed.y);
                                }}
                                return label;
                            }}
                        }}
                    }}
                }},
                scales: {{
                    x: {{
                        grid: {{
                            color: 'rgba(226, 232, 240, 0.8)',
                            tickColor: 'rgba(226, 232, 240, 0.8)'
                        }},
                        ticks: {{
                            color: '#64748b',
                            font: {{
                                family: "'Inter', sans-serif",
                                size: 11
                            }}
                        }}
                    }},
                    yClicks: {{
                        type: 'linear',
                        display: true,
                        position: 'left',
                        grid: {{
                            color: 'rgba(226, 232, 240, 0.8)'
                        }},
                        ticks: {{
                            color: '#0284c7',
                            font: {{
                                family: "'Outfit', sans-serif",
                                weight: '500'
                            }},
                            callback: function(value) {{
                                return new Intl.NumberFormat('en-GB', {{ notation: 'compact' }}).format(value);
                            }}
                        }},
                        title: {{
                            display: true,
                            text: 'Clicks',
                            color: '#0284c7',
                            font: {{
                                family: "'Outfit', sans-serif",
                                size: 12,
                                weight: 'bold'
                            }}
                        }}
                    }},
                    yImpressions: {{
                        type: 'linear',
                        display: true,
                        position: 'right',
                        grid: {{
                            drawOnChartArea: false
                        }},
                        ticks: {{
                            color: '#7c3aed',
                            font: {{
                                family: "'Outfit', sans-serif",
                                weight: '500'
                            }},
                            callback: function(value) {{
                                return new Intl.NumberFormat('en-GB', {{ notation: 'compact' }}).format(value);
                            }}
                        }},
                        title: {{
                            display: true,
                            text: 'Impressions',
                            color: '#7c3aed',
                            font: {{
                                family: "'Outfit', sans-serif",
                                size: 12,
                                weight: 'bold'
                            }}
                        }}
                    }}
                }}
            }}
        }});
    </script>
</body>
</html>
"""
    return html_content

def run_report(service, site_url, start_date, end_date, search_type='discover', top_stories=10, max_rows=10000):
    """
    Executes the Daily Performance Matrix Report.
    Queries GSC performance data, computes rankings, collates popular pages,
    pivots daily clicks/impressions into matrices, and saves CSV and HTML outputs.
    """
    print(f"Running Daily Performance Matrix ({search_type}) for {site_url} ({start_date} to {end_date})...")
    
    # 1. Fetch daily performance data for page dimension
    df = fetch_with_cache(service, site_url, start_date, end_date, ['date', 'page'], search_type, max_rows=max_rows)
    
    if df.empty:
        print(f"No {search_type} data found for {site_url} during the period {start_date} to {end_date}.")
        return None

    # Sort and compute daily rankings
    df['date_dt'] = pd.to_datetime(df['date'])
    df_sorted = df.sort_values(by=['date_dt', 'clicks'], ascending=[True, False])
    df_sorted['rank'] = df_sorted.groupby('date').cumcount() + 1
    
    # 2. Extract unique pages that hit the top X popular list on at least one day
    df_popular_only = df_sorted[df_sorted['rank'] <= top_stories].copy()
    popular_pages = df_popular_only['page'].unique()
    
    # Count how many days each page was "popular" (rank <= top_stories)
    popular_days_count = df_popular_only.groupby('page')['date'].nunique().to_dict()

    # Filter original data to include only the popular pages
    df_matrix_source = df[df['page'].isin(popular_pages)].copy()
    
    # 3. Create Daily Totals for Chart
    df_daily = df.groupby('date').agg({
        'clicks': 'sum',
        'impressions': 'sum'
    }).reset_index()
    df_daily['ctr'] = df_daily['clicks'] / df_daily['impressions']
    df_daily['date_dt'] = pd.to_datetime(df_daily['date'])
    
    # Backfill missing dates to ensure smooth chronological lines
    start_dt = pd.to_datetime(start_date)
    end_dt = pd.to_datetime(end_date)
    all_dates = pd.date_range(start=start_dt, end=end_dt, freq='D')
    
    df_dates = pd.DataFrame({'date_dt': all_dates})
    df_dates['date'] = df_dates['date_dt'].dt.strftime('%Y-%m-%d')
    
    df_daily_complete = pd.merge(df_dates, df_daily, on=['date_dt', 'date'], how='left')
    df_daily_complete['clicks'] = df_daily_complete['clicks'].fillna(0).astype(int)
    df_daily_complete['impressions'] = df_daily_complete['impressions'].fillna(0).astype(int)
    df_daily_complete['ctr'] = df_daily_complete['ctr'].fillna(0.0)
    df_daily_complete = df_daily_complete.sort_values('date_dt', ascending=True)

    # 4. Construct Clicks and Impressions Matrices
    # Pivot dates into columns
    clicks_pivot = df_matrix_source.pivot(index='page', columns='date', values='clicks')
    impressions_pivot = df_matrix_source.pivot(index='page', columns='date', values='impressions')
    
    # Map Popular Days count and Total clicks/impressions
    clicks_pivot['Popular Days'] = clicks_pivot.index.map(popular_days_count).fillna(0).astype(int)
    clicks_pivot['Total Clicks'] = df_matrix_source.groupby('page')['clicks'].sum()
    
    impressions_pivot['Popular Days'] = impressions_pivot.index.map(popular_days_count).fillna(0).astype(int)
    impressions_pivot['Total Impressions'] = df_matrix_source.groupby('page')['impressions'].sum()
    
    # Sort by popularity days count (descending) then by metric totals
    clicks_pivot = clicks_pivot.sort_values(by=['Popular Days', 'Total Clicks'], ascending=[False, False])
    impressions_pivot = impressions_pivot.sort_values(by=['Popular Days', 'Total Impressions'], ascending=[False, False])

    # Reorder columns: Page URL (index), Popular Days, Total, followed by sorted Date columns
    date_cols = sorted([c for c in clicks_pivot.columns if c not in ['Popular Days', 'Total Clicks']])
    
    df_clicks_matrix = clicks_pivot[['Popular Days', 'Total Clicks'] + date_cols].reset_index()
    df_impressions_matrix = impressions_pivot[['Popular Days', 'Total Impressions'] + date_cols].reset_index()

    # 5. Output Paths
    output_dir = get_output_dir(site_url)
    os.makedirs(output_dir, exist_ok=True)
    slug = get_filename_slug(site_url)
    
    search_suffix = f"-{search_type}" if search_type != "discover" else ""
    file_prefix = f"discover-daily-analysis-{slug}{search_suffix}-{start_date}-to-{end_date}"
    
    clicks_csv_path = os.path.join(output_dir, f"{file_prefix}-clicks.csv")
    impressions_csv_path = os.path.join(output_dir, f"{file_prefix}-impressions.csv")
    html_path = os.path.join(output_dir, f"{file_prefix}.html")

    # 6. Save CSV Outputs
    df_clicks_matrix.to_csv(clicks_csv_path, index=False, encoding='utf-8')
    df_impressions_matrix.to_csv(impressions_csv_path, index=False, encoding='utf-8')

    # 7. Save HTML Output
    html_content = create_html_report(
        site_url=site_url,
        start_date=start_date,
        end_date=end_date,
        df_daily_complete=df_daily_complete,
        df_clicks_matrix=df_clicks_matrix,
        df_impressions_matrix=df_impressions_matrix,
        search_type=search_type
    )
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(html_content)

    print(f"Clicks CSV saved to: {clicks_csv_path}")
    print(f"Impressions CSV saved to: {impressions_csv_path}")
    print(f"HTML saved to: {html_path}")
    return html_path

if __name__ == '__main__':
    import argparse
    from core.client import get_gsc_service
    
    parser = argparse.ArgumentParser(description='Daily GSC performance matrix report.')
    parser.add_argument('site_url', help='The URL of the site to analyse.')
    parser.add_argument('--search-type', default='discover', choices=['web', 'news', 'discover'], help='GSC search type (default: discover).')
    parser.add_argument('--start-date', help='Start date (YYYY-MM-DD).')
    parser.add_argument('--end-date', help='End date (YYYY-MM-DD).')
    parser.add_argument('--last-7-days', action='store_true', help='Run for the last 7 available days.')
    parser.add_argument('--last-month', action='store_true', help='Run for the last calendar month.')
    parser.add_argument('--last-28-days', action='store_true', help='Run for the last 28 available days.')
    parser.add_argument('--top-stories', type=int, default=10, help='Number of top stories to retrieve for each day.')
    parser.add_argument('--max-rows', type=int, default=10000, help='Maximum number of rows to fetch from GSC API (default: 10000).')
    
    args = parser.parse_args()
    
    service = get_gsc_service()
    if service:
        # Resolve dates
        if args.start_date and args.end_date:
            start_date, end_date = args.start_date, args.end_date
        else:
            latest_date = get_latest_available_date(service, args.site_url)
            if args.last_7_days:
                start_date, end_date = get_last_7_days_range(latest_date)
            elif args.last_month:
                start_date, end_date = get_last_month_range(latest_date)
            else:
                # Default to last 28 available days
                start_dt = latest_date - timedelta(days=27)
                start_date = start_dt.strftime('%Y-%m-%d')
                end_date = latest_date.strftime('%Y-%m-%d')
                
        run_report(service, args.site_url, start_date, end_date, args.search_type, args.top_stories, args.max_rows)
