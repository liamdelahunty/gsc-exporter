"""
Generates a daily analysis of Google Discover Traffic, showing performance trends and top daily stories.
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

def create_html_report(site_url, start_date, end_date, df_daily_complete, df_top_stories, top_stories_limit):
    """
    Generates a premium, highly interactive HTML dashboard of Discover Traffic.
    """
    # Calculate global KPIs
    total_clicks = int(df_daily_complete['clicks'].sum())
    total_impressions = int(df_daily_complete['impressions'].sum())
    avg_ctr = total_clicks / total_impressions if total_impressions > 0 else 0
    days_count = len(df_daily_complete)

    # Format KPI values
    clicks_str = f"{total_clicks:,}"
    impressions_str = f"{total_impressions:,}"
    ctr_str = f"{avg_ctr:.2%}"

    # Prepare chart data (chronological)
    chart_data = df_daily_complete.sort_values('date_dt').copy()
    chart_dates = chart_data['date'].tolist()
    chart_clicks = chart_data['clicks'].tolist()
    chart_impressions = chart_data['impressions'].tolist()

    # Generate daily top stories HTML
    # We sort days in reverse chronological order for display
    unique_days = sorted(df_daily_complete['date'].unique(), reverse=True)
    daily_cards_html = []

    for day_str in unique_days:
        day_dt = pd.to_datetime(day_str)
        day_formatted = day_dt.strftime("%A, %d %B %Y")
        
        # Get daily totals
        day_total_row = df_daily_complete[df_daily_complete['date'] == day_str]
        if not day_total_row.empty:
            day_clicks = int(day_total_row.iloc[0]['clicks'])
            day_impressions = int(day_total_row.iloc[0]['impressions'])
            day_ctr = day_total_row.iloc[0]['ctr']
        else:
            day_clicks, day_impressions, day_ctr = 0, 0, 0.0

        day_clicks_str = f"{day_clicks:,}"
        day_impressions_str = f"{day_impressions:,}"
        day_ctr_str = f"{day_ctr:.2%}"

        # Get top stories for this day
        day_stories = df_top_stories[df_top_stories['date'] == day_str].sort_values('clicks', ascending=False)
        
        if day_stories.empty:
            table_rows_html = """
            <tr>
                <td colspan="5" class="text-center text-muted py-4">No Discover stories recorded on this day.</td>
            </tr>
            """
        else:
            rows = []
            for _, row in day_stories.iterrows():
                rank = int(row['rank'])
                page_url = row['page']
                clicks = int(row['clicks'])
                impressions = int(row['impressions'])
                ctr = float(row['ctr'])
                
                # Truncate page URL for display but keep full in link
                display_url = page_url.replace("https://", "").replace("http://", "")
                if len(display_url) > 85:
                    display_url = display_url[:82] + "..."

                rows.append(f"""
                <tr class="story-row">
                    <td class="col-rank">#{rank}</td>
                    <td class="col-page">
                        <a href="{page_url}" target="_blank" title="{page_url}" class="story-link text-break">
                            {display_url}
                            <svg class="external-link-icon" xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"></path><polyline points="15 3 21 3 21 9"></polyline><line x1="10" y1="14" x2="21" y2="3"></line></svg>
                        </a>
                    </td>
                    <td class="col-clicks text-end fw-semibold text-clicks">{clicks:,}</td>
                    <td class="col-impressions text-end text-impressions">{impressions:,}</td>
                    <td class="col-ctr text-end text-ctr">{ctr:.2%}</td>
                </tr>
                """)
            table_rows_html = "\n".join(rows)

        # Generate unique ID for accordion/collapsible
        day_id = f"day-{day_str}"
        
        daily_cards_html.append(f"""
        <div class="card daily-card mb-4" data-date="{day_str}">
            <div class="card-header d-flex flex-wrap justify-content-between align-items-center cursor-pointer" onclick="toggleCard('{day_id}')">
                <div class="d-flex align-items-center">
                    <span class="collapse-icon me-3" id="icon-{day_id}">
                        <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="6 9 12 15 18 9"></polyline></svg>
                    </span>
                    <h3 class="h5 mb-0 text-main fw-bold">{day_formatted}</h3>
                </div>
                <div class="d-flex align-items-center gap-3 mt-2 mt-sm-0 daily-badges-container">
                    <span class="badge badge-clicks py-2 px-3">
                        <span class="badge-label">Clicks</span>
                        <span class="badge-value">{day_clicks_str}</span>
                    </span>
                    <span class="badge badge-impressions py-2 px-3">
                        <span class="badge-label">Impressions</span>
                        <span class="badge-value">{day_impressions_str}</span>
                    </span>
                    <span class="badge badge-ctr py-2 px-3">
                        <span class="badge-label">CTR</span>
                        <span class="badge-value">{day_ctr_str}</span>
                    </span>
                </div>
            </div>
            <div class="card-body collapsible-body" id="{day_id}">
                <div class="table-responsive">
                    <table class="table table-borderless story-table mb-0">
                        <thead>
                            <tr>
                                <th class="col-rank">Rank</th>
                                <th class="col-page">Story URL</th>
                                <th class="col-clicks text-end">Clicks</th>
                                <th class="col-impressions text-end">Impressions</th>
                                <th class="col-ctr text-end">CTR</th>
                            </tr>
                        </thead>
                        <tbody>
                            {table_rows_html}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
        """)

    daily_cards_joined = "\n".join(daily_cards_html)

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Google Discover Daily Analysis for {site_url}</title>
    
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
            --bg-primary: #0b0f19;
            --bg-secondary: #131a2d;
            --bg-card: rgba(22, 30, 49, 0.7);
            --border-color: rgba(38, 52, 85, 0.6);
            --text-main: #f8fafc;
            --text-muted: #64748b;
            --text-muted-light: #94a3b8;
            --accent-blue: #0ea5e9;
            --accent-blue-rgb: 14, 165, 233;
            --accent-purple: #d946ef;
            --accent-purple-rgb: 217, 70, 239;
            --accent-green: #10b981;
            --accent-green-rgb: 16, 185, 129;
            --shadow-sm: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
            --shadow-md: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -2px rgba(0, 0, 0, 0.1);
            --shadow-lg: 0 10px 15px -3px rgba(0, 0, 0, 0.15), 0 4px 6px -4px rgba(0, 0, 0, 0.15);
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
            padding-bottom: 0;
            overflow-x: hidden;
        }}

        /* Header Style */
        .dashboard-header {{
            background: linear-gradient(180deg, #111827 0%, var(--bg-primary) 100%);
            border-bottom: 1px solid var(--border-color);
            padding: 2.5rem 0;
            position: relative;
        }}

        .dashboard-header::after {{
            content: '';
            position: absolute;
            bottom: 0;
            left: 50%;
            transform: translateX(-50%);
            width: 80%;
            height: 1px;
            background: linear-gradient(90deg, rgba(14, 165, 233, 0) 0%, rgba(14, 165, 233, 0.4) 50%, rgba(14, 165, 233, 0) 100%);
        }}

        .site-title {{
            font-family: var(--font-outfit);
            font-weight: 800;
            letter-spacing: -0.025em;
            background: linear-gradient(135deg, #fff 30%, #93c5fd 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            font-size: 2.25rem;
            margin-bottom: 0.5rem;
        }}

        .date-range-pill {{
            background: rgba(30, 41, 59, 0.8);
            border: 1px solid var(--border-color);
            color: var(--accent-blue);
            font-weight: 500;
            font-size: 0.875rem;
            padding: 0.4rem 1rem;
            border-radius: 9999px;
            display: inline-flex;
            align-items: center;
            gap: 0.5rem;
            font-family: var(--font-outfit);
        }}

        /* Cards and Layout */
        .kpi-card {{
            background-color: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 1rem;
            padding: 1.5rem;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            position: relative;
            overflow: hidden;
            backdrop-filter: blur(12px);
        }}

        .kpi-card:hover {{
            transform: translateY(-4px);
            border-color: rgba(14, 165, 233, 0.4);
            box-shadow: 0 10px 20px -10px rgba(14, 165, 233, 0.2);
        }}

        .kpi-card.clicks-card:hover {{
            border-color: var(--accent-blue);
            box-shadow: 0 10px 20px -10px rgba(var(--accent-blue-rgb), 0.25);
        }}

        .kpi-card.impressions-card:hover {{
            border-color: var(--accent-purple);
            box-shadow: 0 10px 20px -10px rgba(var(--accent-purple-rgb), 0.25);
        }}

        .kpi-card.ctr-card:hover {{
            border-color: var(--accent-green);
            box-shadow: 0 10px 20px -10px rgba(var(--accent-green-rgb), 0.25);
        }}

        .kpi-label {{
            color: var(--text-muted-light);
            font-size: 0.875rem;
            font-weight: 500;
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

        /* Glow Elements */
        .kpi-card::before {{
            content: '';
            position: absolute;
            top: 0;
            right: 0;
            width: 100px;
            height: 100px;
            border-radius: 50%;
            pointer-events: none;
            transition: all 0.3s;
        }}

        .clicks-card::before {{
            background: radial-gradient(circle, rgba(14, 165, 233, 0.12) 0%, rgba(14, 165, 233, 0) 70%);
        }}

        .impressions-card::before {{
            background: radial-gradient(circle, rgba(217, 70, 239, 0.12) 0%, rgba(217, 70, 239, 0) 70%);
        }}

        .ctr-card::before {{
            background: radial-gradient(circle, rgba(16, 185, 129, 0.12) 0%, rgba(16, 185, 129, 0) 70%);
        }}

        /* Chart container */
        .chart-card {{
            background-color: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 1rem;
            padding: 1.75rem;
            box-shadow: var(--shadow-lg);
            backdrop-filter: blur(12px);
        }}

        .chart-card-header {{
            margin-bottom: 1.5rem;
        }}

        .chart-card-title {{
            font-family: var(--font-outfit);
            font-weight: 700;
            font-size: 1.25rem;
        }}

        .chart-container {{
            position: relative;
            height: 380px;
            width: 100%;
        }}

        /* Daily Cards Breakdown */
        .section-title-bar {{
            margin-top: 3.5rem;
            margin-bottom: 1.5rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid var(--border-color);
            padding-bottom: 0.75rem;
        }}

        .section-title {{
            font-family: var(--font-outfit);
            font-weight: 700;
            font-size: 1.5rem;
            margin-bottom: 0;
            background: linear-gradient(135deg, #fff 60%, #94a3b8 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }}

        .control-btn {{
            background: rgba(30, 41, 59, 0.6);
            border: 1px solid var(--border-color);
            color: var(--text-muted-light);
            font-size: 0.825rem;
            font-weight: 500;
            padding: 0.35rem 0.85rem;
            border-radius: 0.5rem;
            transition: all 0.2s;
            cursor: pointer;
        }}

        .control-btn:hover {{
            background: var(--bg-secondary);
            border-color: var(--accent-blue);
            color: var(--text-main);
        }}

        .search-bar {{
            max-width: 320px;
            width: 100%;
        }}

        .search-input {{
            background: rgba(15, 23, 42, 0.6);
            border: 1px solid var(--border-color);
            border-radius: 0.5rem;
            color: var(--text-main);
            font-size: 0.875rem;
            padding: 0.45rem 1rem;
            width: 100%;
            transition: all 0.2s;
        }}

        .search-input:focus {{
            outline: none;
            border-color: var(--accent-blue);
            box-shadow: 0 0 0 2px rgba(14, 165, 233, 0.2);
            background: rgba(15, 23, 42, 0.8);
        }}

        .daily-card {{
            background-color: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 0.75rem;
            overflow: hidden;
            box-shadow: var(--shadow-sm);
            transition: border-color 0.2s, box-shadow 0.2s;
        }}

        .daily-card:hover {{
            border-color: rgba(14, 165, 233, 0.3);
            box-shadow: var(--shadow-md);
        }}

        .daily-card .card-header {{
            background-color: rgba(30, 41, 59, 0.3);
            border-bottom: 1px solid transparent;
            padding: 1.25rem 1.5rem;
            user-select: none;
            transition: background-color 0.2s, border-color 0.2s;
        }}

        .daily-card .card-header:hover {{
            background-color: rgba(30, 41, 59, 0.5);
        }}

        .daily-card.active .card-header {{
            border-bottom-color: var(--border-color);
            background-color: rgba(30, 41, 59, 0.4);
        }}

        .collapse-icon {{
            color: var(--text-muted-light);
            transition: transform 0.25s ease;
            display: inline-block;
        }}

        .daily-card.active .collapse-icon {{
            transform: rotate(180deg);
            color: var(--accent-blue);
        }}

        .badge-clicks, .badge-impressions, .badge-ctr {{
            background: rgba(15, 23, 42, 0.5);
            border: 1px solid var(--border-color);
            border-radius: 0.5rem;
            display: inline-flex;
            flex-direction: column;
            align-items: flex-end;
            min-width: 90px;
            font-size: 0.75rem;
        }}

        .badge-clicks {{ border-left: 3px solid var(--accent-blue); }}
        .badge-impressions {{ border-left: 3px solid var(--accent-purple); }}
        .badge-ctr {{ border-left: 3px solid var(--accent-green); }}

        .badge-label {{
            color: var(--text-muted);
            font-size: 0.65rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            margin-bottom: 0.1rem;
        }}

        .badge-clicks .badge-value {{ color: var(--accent-blue); font-weight: 700; }}
        .badge-impressions .badge-value {{ color: var(--accent-purple); font-weight: 700; }}
        .badge-ctr .badge-value {{ color: var(--accent-green); font-weight: 700; }}

        .collapsible-body {{
            max-height: 0;
            overflow: hidden;
            transition: max-height 0.3s cubic-bezier(0, 1, 0, 1);
        }}

        .daily-card.active .collapsible-body {{
            max-height: 2000px;
            transition: max-height 0.3s cubic-bezier(1, 0, 1, 0);
        }}

        .story-table {{
            margin: 0;
        }}

        .story-table th {{
            color: var(--text-muted-light);
            font-size: 0.75rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            font-weight: 600;
            padding: 1rem 1.25rem;
            border-bottom: 1px solid var(--border-color);
        }}

        .story-table td {{
            padding: 0.85rem 1.25rem;
            vertical-align: middle;
            border-bottom: 1px solid rgba(51, 65, 85, 0.2);
            font-size: 0.875rem;
        }}

        .story-row {{
            transition: background-color 0.15s;
        }}

        .story-row:hover {{
            background-color: rgba(30, 41, 59, 0.25);
        }}

        .col-rank {{
            width: 70px;
            font-weight: 700;
            color: var(--text-muted-light);
        }}

        .col-page {{
            min-width: 250px;
        }}

        .col-clicks {{
            width: 110px;
        }}

        .col-impressions {{
            width: 140px;
        }}

        .col-ctr {{
            width: 100px;
        }}

        .story-link {{
            color: #93c5fd;
            text-decoration: none;
            font-weight: 400;
            transition: color 0.15s;
            display: inline-flex;
            align-items: center;
            gap: 0.35rem;
        }}

        .story-link:hover {{
            color: var(--accent-blue);
            text-decoration: underline;
        }}

        .external-link-icon {{
            opacity: 0;
            transform: translateY(1px);
            transition: opacity 0.15s, transform 0.15s;
            color: var(--accent-blue);
        }}

        .story-link:hover .external-link-icon {{
            opacity: 0.8;
            transform: translateY(0);
        }}

        /* Footer */
        footer {{
            margin-top: auto;
            padding: 2.5rem 0;
            border-top: 1px solid var(--border-color);
            background-color: rgba(17, 24, 39, 0.4);
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
            .daily-badges-container {{
                width: 100%;
                justify-content: flex-start;
                margin-top: 0.75rem;
            }}
            .site-title {{
                font-size: 1.75rem;
            }}
            .kpi-value {{
                font-size: 1.75rem;
            }}
            .chart-container {{
                height: 280px;
            }}
            .story-table th, .story-table td {{
                padding: 0.75rem 0.75rem;
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
                    <h1 class="site-title">Google Discover Daily Report</h1>
                    <p class="text-muted-light mb-0">Discover Traffic performance analysis for <span class="fw-semibold text-white">{site_url}</span></p>
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
                    <div class="kpi-label">Days Analysed</div>
                    <div class="kpi-value text-white">{days_count}</div>
                </div>
            </div>
        </div>

        <!-- Chart Card -->
        <div class="row mb-5">
            <div class="col-12">
                <div class="chart-card">
                    <div class="chart-card-header d-flex justify-content-between align-items-center">
                        <h2 class="chart-card-title text-white mb-0">Daily Trends</h2>
                        <span class="text-muted-light small">Hover on lines to view details</span>
                    </div>
                    <div class="chart-container">
                        <canvas id="dailyPerformanceChart"></canvas>
                    </div>
                </div>
            </div>
        </div>

        <!-- Daily Breakdown Header -->
        <div class="section-title-bar">
            <h2 class="section-title">Daily Breakdown</h2>
            <div class="d-flex align-items-center gap-2">
                <button class="control-btn" onclick="toggleAllCards(true)">Expand All</button>
                <button class="control-btn" onclick="toggleAllCards(false)">Collapse All</button>
                <div class="search-bar ms-2">
                    <input type="text" id="storySearch" class="search-input" placeholder="Search stories..." oninput="filterStories()">
                </div>
            </div>
        </div>

        <!-- Daily Cards -->
        <div class="daily-cards-container">
            {daily_cards_joined}
        </div>

    </main>

    <!-- Footer -->
    <footer class="footer">
        <div class="container text-center">
            <span>Report generated on {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}. Powered by <a href="https://github.com/liamdelahunty/gsc-exporter" target="_blank">gsc-exporter</a></span>
        </div>
    </footer>

    <!-- Interactive Logic Scripts -->
    <script>
        // Toggle Card Visibility
        function toggleCard(cardId) {{
            const card = document.getElementById(cardId).parentElement;
            card.classList.toggle('active');
        }}

        // Expand or Collapse All Cards
        function toggleAllCards(expand) {{
            const cards = document.querySelectorAll('.daily-card');
            cards.forEach(card => {{
                if (expand) {{
                    card.classList.add('active');
                }} else {{
                    card.classList.remove('active');
                }}
            }});
        }}

        // Filter Stories Dynamically in HTML
        function filterStories() {{
            const query = document.getElementById('storySearch').value.toLowerCase().trim();
            const dailyCards = document.querySelectorAll('.daily-card');
            
            dailyCards.forEach(card => {{
                const rows = card.querySelectorAll('.story-row');
                let dayHasMatches = false;
                
                rows.forEach(row => {{
                    const linkText = row.querySelector('.story-link').textContent.toLowerCase();
                    if (linkText.includes(query)) {{
                        row.style.display = '';
                        dayHasMatches = true;
                    }} else {{
                        row.style.display = 'none';
                    }}
                }});

                // If query is empty, show all cards and reset active state
                if (query === '') {{
                    card.style.display = '';
                }} else if (dayHasMatches) {{
                    card.style.display = '';
                    card.classList.add('active'); // Expand matching days
                }} else {{
                    card.style.display = 'none';
                }}
            }});
        }}

        // Expand first card by default on load
        window.addEventListener('DOMContentLoaded', () => {{
            const firstCard = document.querySelector('.daily-card');
            if (firstCard) {{
                firstCard.classList.add('active');
            }}
        }});

        // Chart.js Setup
        const chartCtx = document.getElementById('dailyPerformanceChart').getContext('2d');
        
        // Define gradients for chart fills
        const blueGradient = chartCtx.createLinearGradient(0, 0, 0, 350);
        blueGradient.addColorStop(0, 'rgba(14, 165, 233, 0.25)');
        blueGradient.addColorStop(1, 'rgba(14, 165, 233, 0.00)');

        const purpleGradient = chartCtx.createLinearGradient(0, 0, 0, 350);
        purpleGradient.addColorStop(0, 'rgba(217, 70, 239, 0.20)');
        purpleGradient.addColorStop(1, 'rgba(217, 70, 239, 0.00)');

        const chartLabels = {json.dumps(chart_dates)};
        const clicksData = {json.dumps(chart_clicks)};
        const impressionsData = {json.dumps(chart_impressions)};

        new Chart(chartCtx, {{
            type: 'line',
            data: {{
                labels: chartLabels.map(d => {{
                    // Format date labels for chart: "DD MMM"
                    const dateObj = new Date(d);
                    return dateObj.toLocaleDateString('en-GB', {{ day: 'numeric', month: 'short' }});
                }}),
                datasets: [
                    {{
                        label: 'Clicks',
                        data: clicksData,
                        borderColor: '#0ea5e9',
                        backgroundColor: blueGradient,
                        borderWidth: 3,
                        pointBackgroundColor: '#0ea5e9',
                        pointBorderColor: '#0b0f19',
                        pointHoverBackgroundColor: '#fff',
                        pointHoverBorderColor: '#0ea5e9',
                        pointRadius: 4,
                        pointHoverRadius: 6,
                        yAxisID: 'yClicks',
                        fill: true,
                        tension: 0.35
                    }},
                    {{
                        label: 'Impressions',
                        data: impressionsData,
                        borderColor: '#d946ef',
                        backgroundColor: purpleGradient,
                        borderWidth: 3,
                        pointBackgroundColor: '#d946ef',
                        pointBorderColor: '#0b0f19',
                        pointHoverBackgroundColor: '#fff',
                        pointHoverBorderColor: '#d946ef',
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
                            color: '#94a3b8',
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
                        backgroundColor: '#1e293b',
                        titleColor: '#fff',
                        bodyColor: '#e2e8f0',
                        borderColor: 'rgba(255,255,255,0.1)',
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
                            color: 'rgba(51, 65, 85, 0.15)',
                            tickColor: 'rgba(51, 65, 85, 0.3)'
                        }},
                        ticks: {{
                            color: '#94a3b8',
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
                            color: 'rgba(51, 65, 85, 0.2)'
                        }},
                        ticks: {{
                            color: '#0ea5e9',
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
                            color: '#0ea5e9',
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
                            color: '#d946ef',
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
                            color: '#d946ef',
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

def run_report(service, site_url, start_date, end_date, top_stories=10):
    """
    Executes the Google Discover Daily Analysis Report.
    Queries the Search Console API for Discover data, aggregates daily totals,
    extracts the top stories per day, and exports to CSV and HTML.
    """
    print(f"Running Discover Daily Analysis Report for {site_url} ({start_date} to {end_date})...")
    
    # Fetch granular Discover data with dimensions=['date', 'page']
    df = fetch_with_cache(service, site_url, start_date, end_date, ['date', 'page'], 'discover')
    
    if df.empty:
        print(f"No Discover data found for {site_url} during the period {start_date} to {end_date}.")
        return None

    # Sort and compute daily ranks for stories
    df['date_dt'] = pd.to_datetime(df['date'])
    df_sorted = df.sort_values(by=['date_dt', 'clicks'], ascending=[True, False])
    df_sorted['rank'] = df_sorted.groupby('date').cumcount() + 1
    
    # Filter to only the top X stories
    df_top_stories = df_sorted[df_sorted['rank'] <= top_stories].copy()

    # Compute daily totals
    df_daily = df.groupby('date').agg({
        'clicks': 'sum',
        'impressions': 'sum'
    }).reset_index()
    df_daily['ctr'] = df_daily['clicks'] / df_daily['impressions']
    df_daily['date_dt'] = pd.to_datetime(df_daily['date'])
    
    # Complete date range to avoid gaps in chart
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

    # Output Paths
    output_dir = get_output_dir(site_url)
    os.makedirs(output_dir, exist_ok=True)
    slug = get_filename_slug(site_url)
    
    file_prefix = f"discover-daily-analysis-{slug}-{start_date}-to-{end_date}"
    csv_path = os.path.join(output_dir, f"{file_prefix}.csv")
    html_path = os.path.join(output_dir, f"{file_prefix}.html")

    # Save CSV (top stories per day)
    csv_cols = ['date', 'rank', 'page', 'clicks', 'impressions', 'ctr']
    df_top_stories_csv = df_top_stories[csv_cols].copy()
    df_top_stories_csv.to_csv(csv_path, index=False, encoding='utf-8')
    
    # Save HTML
    html_content = create_html_report(
        site_url=site_url,
        start_date=start_date,
        end_date=end_date,
        df_daily_complete=df_daily_complete,
        df_top_stories=df_top_stories,
        top_stories_limit=top_stories
    )
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
        
    print(f"CSV saved to: {csv_path}")
    print(f"HTML saved to: {html_path}")
    return html_path

if __name__ == '__main__':
    import argparse
    from core.client import get_gsc_service
    
    parser = argparse.ArgumentParser(description='Discover daily analysis report.')
    parser.add_argument('site_url', help='The URL of the site to analyse.')
    parser.add_argument('--start-date', help='Start date (YYYY-MM-DD).')
    parser.add_argument('--end-date', help='End date (YYYY-MM-DD).')
    parser.add_argument('--last-7-days', action='store_true', help='Run for the last 7 available days.')
    parser.add_argument('--last-month', action='store_true', help='Run for the last calendar month.')
    parser.add_argument('--last-28-days', action='store_true', help='Run for the last 28 available days.')
    parser.add_argument('--top-stories', type=int, default=10, help='Number of top stories to retrieve for each day.')
    
    args = parser.parse_args()
    
    service = get_gsc_service()
    if service:
        # Custom date parsing to default to last 28 days if no arguments are provided
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
                
        run_report(service, args.site_url, start_date, end_date, args.top_stories)
