import os
import argparse
from pathlib import Path
from urllib.parse import urlparse

def generate_index_html(site_url):
    """Generates an index.html file that links to all HTML reports in the output directory."""
    try:
        if site_url.startswith('sc-domain:'):
            hostname = site_url.replace('sc-domain:', '')
        else:
            hostname = urlparse(site_url).hostname
        
        if not hostname:
            print(f"Error: Invalid site URL '{site_url}'.")
            return

        output_dir = Path('output') / hostname
        if not output_dir.is_dir():
            print(f"Error: Output directory '{output_dir}' not found.")
            return

        html_files = sorted([f for f in output_dir.glob('*.html') if f.name != 'index.html'])
        # resource_files = sorted(Path('resources').glob('how-to-read-the-gsc-wrapped-report.html')) # Removed this line as requested
        
        if not html_files: # resource_files check removed here
            print(f"No HTML reports found to index.")
            return

        index_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>GSC Reports for {hostname}</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body {{ padding: 2rem; }}
        h1, h2 {{ border-bottom: 2px solid #dee2e6; padding-bottom: .5rem; margin-bottom: 1rem; margin-top: 1.5rem;}}
        .list-group-item a {{ text-decoration: none; }}
        .list-group-item:hover {{ background-color: #f8f9fa; }}
        footer{{margin-top:3rem;text-align:center;color:#6c757d;}}
    </style>
</head>
<body>
    <div class="container">
        <h1>GSC Reports for {hostname}</h1>
        
        <h2>Reports</h2>
        <div class="list-group">
"""

        if html_files:
            for html_file in html_files:
                index_content += f'            <a href="{html_file.name}" class="list-group-item list-group-item-action">{html_file.stem.replace("-", " ").title()}</a>\n'
        else:
            index_content += '<p>No reports found in this directory.</p>'

        # Removing the "How-to Guides" section if it only contained the wrapped report
        # If there are other how-to guides, a more complex filter would be needed.
        # Given the original code explicitly listed only this one, removing it is sufficient.
        
        index_content += """
        </div>
    </div>
    <footer><p><a href="https://github.com/liamdelahunty/gsc-exporter" target="_blank">gsc-exporter</a></p></footer>
</body>
</html>
"""

        index_path = output_dir / 'index.html'
        with open(index_path, 'w', encoding='utf-8') as f:
            f.write(index_content)

        print(f"Successfully generated index.html at '{index_path}'")

    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Generate an index HTML file for GSC reports.')
    parser.add_argument('site_url', help='The full URL of the site property (e.g., `https://www.example.com`) or a domain property (e.g., `sc-domain:example.com`).')
    args = parser.parse_args()
    
    generate_index_html(args.site_url)
