import os
import argparse
from pathlib import Path
from urllib.parse import urlparse
from jinja2 import Environment, FileSystemLoader

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
        
        if not html_files:
            print(f"No HTML reports found to index.")
            # Still generate a blank index.html for consistency, if desired.
            # For now, we will return None if no reports to index.
            return

        # Setup Jinja2 environment
        template_loader = FileSystemLoader('templates')
        env = Environment(loader=template_loader)
        template = env.get_template('index-template.html')

        # Render the template
        index_content = template.render(hostname=hostname, html_files=html_files)

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
