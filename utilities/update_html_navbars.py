"""
Utility script to standardise and update the navigation bar order across all generated HTML reports.
Follows the exact order requested by the user.
"""
import os
import re

def update_navbars(directory, slug, dates):
    # Files to process
    files = {
        'index': f"dato-drupal-index-{slug}-{dates}.html",
        'analysis': f"drupal-dato-migration-analysis-{slug}-{dates}.html",
        'page_level': f"drupal-dato-migration-page-level-report-{slug}-{dates}.html",
        'prioritisation': f"drupal-dato-migration-prioritisation-report-{slug}-{dates}.html",
        'suggested': f"dato-suggested-urls-alphabetical-{slug}-{dates}.html",
        'comparison': f"gsc-data-comparison-{slug}-{dates}.html",
        'dato_perf': f"dato-pages-performance-report-{slug}-{dates}.html"
    }

    # Verify files exist in directory
    for key, name in files.items():
        path = os.path.join(directory, name)
        if not os.path.exists(path):
            print(f"Warning: File {name} not found at {path}. Skipping.")
            
    # Build navbar for each file
    for key, name in files.items():
        path = os.path.join(directory, name)
        if not os.path.exists(path):
            continue

        print(f"Processing {name}...")

        # Setup classes
        act = "btn-primary active"
        inact = "btn-outline-primary"

        nav_html = f"""    <div class="d-flex flex-wrap gap-2 justify-content-center mb-4 pb-3 border-bottom">
        <a href="{files['index']}" class="btn {act if key == 'index' else inact} px-4">Migration Index</a>
        <a href="{files['analysis']}" class="btn {act if key == 'analysis' else inact} px-4">Breakdown Dashboard (Query-Level)</a>
        <a href="{files['page_level']}" class="btn {act if key == 'page_level' else inact} px-4">Page-Level Report (All Clicks)</a>
        <a href="{files['prioritisation']}" class="btn {act if key == 'prioritisation' else inact} px-4">Top 50 Prioritisation Report</a>
        <a href="{files['suggested']}" class="btn {act if key == 'suggested' else inact} px-4">Proposed Dato URLs (Alphabetical)</a>
        <a href="{files['comparison']}" class="btn {act if key == 'comparison' else inact} px-4">GSC Data Comparison</a>
        <a href="{files['dato_perf']}" class="btn {act if key == 'dato_perf' else inact} px-4">Dato Pages Performance</a>
    </div>"""

        # Read file
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Regex to match the navigation menu wrapper
        # Matches: <div class="d-flex flex-wrap gap-2 justify-content-center mb-4 pb-3 border-bottom">...</div>
        pattern = r'<div class="d-flex flex-wrap gap-2 justify-content-center mb-4 pb-3 border-bottom">.*?</div>'
        
        # Check if the navigation block exists
        if re.search(pattern, content, re.DOTALL):
            new_content = re.sub(pattern, nav_html, content, flags=re.DOTALL)
            with open(path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            print(f"  Successfully updated navbar in {name}")
        else:
            # Fallback if classes or formatting differ slightly, e.g. with <!-- Navigation Menu --> comment
            pattern_commented = r'<!-- Navigation Menu -->\s*<div class="d-flex flex-wrap gap-2 justify-content-center.*?>.*?</div>'
            if re.search(pattern_commented, content, re.DOTALL):
                new_content = re.sub(pattern_commented, "<!-- Navigation Menu -->\n" + nav_html, content, flags=re.DOTALL)
                with open(path, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                print(f"  Successfully updated commented navbar in {name}")
            else:
                print(f"  Error: Could not locate navbar pattern in {name}")

if __name__ == '__main__':
    directory = 'output/www.hr-inform.co.uk'
    slug = 'www-hr-inform-co-uk'
    dates = '2026-06-01-to-2026-06-30'
    update_navbars(directory, slug, dates)
