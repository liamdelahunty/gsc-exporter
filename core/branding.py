"""
Branding options module for GSC Exporter.
Allows custom logos, links, text and colours to be injected into generated HTML reports.
Transparently hooks into file-writing and argument parsing to support global configuration.
"""
import os
import json
import builtins
import re
import argparse

# Keep reference to original open
_original_open = builtins.open

def get_config_path() -> str:
    """
    Determines the path to the branding configuration JSON file.
    Checks environment variable GSC_BRANDING_CONFIG, then sys.argv,
    then defaults to config/branding.json.
    """
    env_path = os.environ.get('GSC_BRANDING_CONFIG')
    if env_path:
        return env_path
    
    import sys
    for i, arg in enumerate(sys.argv):
        if arg == '--branding-config' and i + 1 < len(sys.argv):
            return sys.argv[i + 1]
        elif arg.startswith('--branding-config='):
            return arg.split('=', 1)[1]
            
    return os.path.join('config', 'branding.json')

def load_branding_config() -> dict | None:
    """
    Loads the branding configuration from JSON.
    Uses original open to avoid recursion.
    Checks config path, then defaults to config/branding.json, then config/branding.default.json.
    """
    config_path = get_config_path()
    if not os.path.exists(config_path):
        # If it was the default path, try falling back to branding.default.json
        if config_path == os.path.join('config', 'branding.json'):
            config_path = os.path.join('config', 'branding.default.json')
            if not os.path.exists(config_path):
                return None
        else:
            return None

    try:
        with _original_open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        return config
    except Exception as e:
        print(f"Warning: Failed to load branding configuration from {config_path}: {e}")
        return None

def find_report_doc_filename(filepath: str) -> str | None:
    """
    Determines the appropriate documentation filename for the running report.
    Checks sys.argv[0] first, then falls back to matching keywords in the output filename.
    """
    import sys
    
    # 1. Check sys.argv[0] (running script)
    script_name = os.path.basename(sys.argv[0])
    if script_name.endswith('.py') and script_name != '__init__.py':
        # E.g. reports/consolidated_traffic_report.py
        doc_name = script_name[:-3].replace('_', '-') + '.md'
        # Verify it exists
        if os.path.exists(os.path.join('resources', 'reports', doc_name)):
            return doc_name

    # 2. Fallback: Match against files in resources/reports/ using output filename
    docs_dir = os.path.join('resources', 'reports')
    if os.path.exists(docs_dir):
        html_basename = os.path.basename(filepath).lower()
        html_name = os.path.splitext(html_basename)[0]
        
        # Sort doc files by length descending so longer matches take precedence
        doc_files = sorted(os.listdir(docs_dir), key=len, reverse=True)
        for doc_file in doc_files:
            if doc_file.endswith('.md'):
                doc_base = doc_file[:-3] # Remove '.md'
                doc_parts = doc_base.split('-')
                
                # Ignore trailing 'report' word if there are other parts
                if len(doc_parts) > 1 and doc_parts[-1] == 'report':
                    match_prefix = '-'.join(doc_parts[:-1])
                else:
                    match_prefix = doc_base
                    
                if html_name.startswith(match_prefix):
                    return doc_file
                    
    return None

def apply_branding_to_html(html_content: str, filepath: str, config: dict) -> str:
    """
    Applies the custom branding configuration to the HTML content.
    Injects custom CSS/JS assets and prepends the branding bar with a dropdown menu at the top of the body.
    """
    if not config or not config.get('enabled', False):
        return html_content

    theme = config.get('theme', {})
    primary_colour = theme.get('primary_colour', theme.get('primary_color', '#1a73e8'))
    text_colour = theme.get('text_colour', theme.get('text_color', '#ffffff'))
    font_family = theme.get('font_family', "'Outfit', sans-serif")
    logo_url = config.get('logo_url', '')
    link_url = config.get('link_url', '#')
    text = config.get('text', '')
    links = config.get('links', [])

    # Build logo/text HTML fragment
    logo_html = ""
    if logo_url:
        logo_html = f'<img src="{logo_url}" alt="Logo" height="24" style="vertical-align: middle; margin-right: 10px;">'

    header_brand_html = f'<a href="{link_url}" target="_blank" style="text-decoration: none; display: inline-flex; align-items: center; color: inherit;">{logo_html}<span style="font-weight: bold;">{text}</span></a>'

    # Re-order and build menu links in the requested order:
    # 1. Repository
    # 2. General Documentation
    # 3. Bespoke Report Documentation
    repo_link_html = ""
    general_doc_link_html = ""
    
    for link in links:
        link_text = link.get('text', '')
        link_url_val = link.get('url', '#')
        text_lower = link_text.lower()
        
        if 'repository' in text_lower or 'repo' in text_lower:
            repo_link_html = f'<a href="{link_url_val}" target="_blank">{link_text}</a>'
        elif 'documentation' in text_lower or 'docs' in text_lower:
            general_doc_link_html = f'<a href="{link_url_val}" target="_blank">{link_text}</a>'
        else:
            # Append other links to repository section by default
            if repo_link_html:
                repo_link_html += f'<a href="{link_url_val}" target="_blank">{link_text}</a>'
            else:
                repo_link_html = f'<a href="{link_url_val}" target="_blank">{link_text}</a>'

    # Fallback to direct rendering if categorization keywords aren't found
    if not repo_link_html and not general_doc_link_html and links:
        fallback_links = ""
        for link in links:
            fallback_links += f'<a href="{link.get("url", "#")}" target="_blank">{link.get("text", "")}</a>'
        repo_link_html = fallback_links

    # Build bespoke documentation GitHub link
    bespoke_doc_link_html = ""
    doc_filename = find_report_doc_filename(filepath)
    if doc_filename:
        # Base repo URL from config or fallback
        repo_base = config.get('link_url', 'https://github.com/liamdelahunty/gsc-exporter')
        repo_base = repo_base.rstrip('/')
        doc_github_url = f"{repo_base}/blob/main/resources/reports/{doc_filename}"
        
        bespoke_doc_link_html = f'<a href="{doc_github_url}" target="_blank" style="font-weight: bold; color: var(--branding-primary) !important;">Report Documentation</a>'

    # Assemble links in specified order (no separator line)
    all_links_html = ""
    if repo_link_html:
        all_links_html += repo_link_html
    if general_doc_link_html:
        all_links_html += general_doc_link_html
    if bespoke_doc_link_html:
        all_links_html += bespoke_doc_link_html

    # Build hamburger menu HTML fragment
    menu_wrapper_html = ""
    if all_links_html:
        menu_wrapper_html = f"""
        <div style="position: relative;">
            <button class="branded-hamburger-button" onclick="toggleBrandingMenu()" aria-label="Toggle Menu">
                <svg viewBox="0 0 24 24" width="24" height="24" stroke="currentColor" stroke-width="2" fill="none" stroke-linecap="round" stroke-linejoin="round">
                    <line x1="3" y1="12" x2="21" y2="12"></line>
                    <line x1="3" y1="6" x2="21" y2="6"></line>
                    <line x1="3" y1="18" x2="21" y2="18"></line>
                </svg>
            </button>
            <div id="branded-menu-dropdown" class="branded-menu-dropdown" style="display: none;">
                {all_links_html}
            </div>
        </div>
        """

    # Build CSS styling to be injected
    css_styles = f"""
    <style id="custom-branding-styles">
        /* Custom branding theme styles */
        :root {{
            --branding-primary: {primary_colour};
            --branding-text: {text_colour};
            --branding-font: {font_family};
        }}
        .branded-top-bar {{
            background-color: var(--branding-primary) !important;
            color: var(--branding-text) !important;
            font-family: var(--branding-font);
            padding: 10px 24px;
            font-size: 0.95rem;
            border-bottom: 1px solid rgba(0,0,0,0.1);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        .branded-top-bar a {{
            color: var(--branding-text) !important;
            text-decoration: none;
            font-weight: 600;
            display: inline-flex;
            align-items: center;
        }}
        .branded-hamburger-button {{
            background: none !important;
            border: none !important;
            color: var(--branding-text) !important;
            cursor: pointer;
            padding: 4px;
            display: flex;
            align-items: center;
            outline: none !important;
            transition: opacity 0.15s ease;
        }}
        .branded-hamburger-button:hover {{
            opacity: 0.8;
        }}
        .branded-menu-dropdown {{
            position: absolute;
            top: 100%;
            right: 0;
            background-color: #ffffff !important;
            border: 1px solid #dadce0 !important;
            border-radius: 8px;
            box-shadow: 0 4px 16px rgba(0,0,0,0.08);
            padding: 6px 0;
            min-width: 170px;
            z-index: 1050;
            margin-top: 8px;
        }}
        .branded-menu-dropdown a {{
            color: #3c4043 !important;
            display: block !important;
            padding: 6px 12px;
            margin: 2px 6px;
            border-radius: 4px;
            text-decoration: none;
            font-weight: 500;
            font-size: 0.875rem;
            white-space: nowrap;
            transition: background-color 0.15s ease, color 0.15s ease;
        }}
        .branded-menu-dropdown a:hover {{
            background-color: #f1f3f4 !important;
            color: var(--branding-primary) !important;
            text-decoration: none !important;
        }}
        /* Force standard Bootstrap fixed headers to flow naturally below the branding bar */
        .fixed-top {{
            position: static !important;
        }}
        body {{
            padding-top: 0 !important;
        }}
    </style>
    """

    # Build Javascript to toggle dropdown and close when clicking outside
    js_code = """
    <script id="custom-branding-js">
        function toggleBrandingMenu() {
            var menu = document.getElementById('branded-menu-dropdown');
            if (menu) {
                if (menu.style.display === 'block') {
                    menu.style.display = 'none';
                } else {
                    menu.style.display = 'block';
                }
            }
        }
        document.addEventListener('click', function(event) {
            var menu = document.getElementById('branded-menu-dropdown');
            var button = event.target.closest('.branded-hamburger-button');
            if (menu && !button && !event.target.closest('.branded-menu-dropdown')) {
                menu.style.display = 'none';
            }
        });
    </script>
    """

    # Inject CSS & JS before </head>
    injected_assets = f"{css_styles}\n{js_code}"
    if '</head>' in html_content:
        html_content = html_content.replace('</head>', f'{injected_assets}\n</head>', 1)
    elif '<head>' in html_content:
        html_content = html_content.replace('<head>', f'<head>\n{injected_assets}', 1)

    # Build navigation bar HTML
    top_bar_html = f"""
    <div class="branded-top-bar">
        <div>
            {header_brand_html}
        </div>
        {menu_wrapper_html}
    </div>
    """

    # Prepend branding navigation bar to body
    body_pattern = re.compile(r'(<body[^>]*>)', re.IGNORECASE)
    if body_pattern.search(html_content):
        html_content = body_pattern.sub(r'\1' + top_bar_html, html_content, count=1)
    else:
        # Fallback if no body tag found
        html_content = top_bar_html + html_content

    return html_content

class BrandedFileWrapper:
    """
    A file-like wrapper that intercepts write operations on HTML files
    to apply custom branding before saving.
    """
    def __init__(self, real_file, filepath: str, config: dict):
        self.real_file = real_file
        self.filepath = filepath
        self.config = config
        self.content = []

    def write(self, s):
        if isinstance(s, bytes):
            # If for some reason we get bytes, try decoding it
            try:
                s = s.decode('utf-8')
            except UnicodeDecodeError:
                # Fallback to write bytes directly if decoding fails
                return self.real_file.write(s)
        self.content.append(s)

    def writelines(self, lines):
        for line in lines:
            self.write(line)

    def close(self):
        if self.content:
            full_content = "".join(self.content)
            branded_content = apply_branding_to_html(full_content, self.filepath, self.config)
            self.real_file.write(branded_content)
        self.real_file.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def __getattr__(self, name):
        # Delegate any other file methods/attributes to the real file object
        return getattr(self.real_file, name)

# Hook builtins.open
def custom_open(file, mode='r', buffering=-1, encoding=None, errors=None, newline=None, closefd=True, opener=None):
    filepath = os.fspath(file) if isinstance(file, (str, bytes, os.PathLike)) else str(file)
    is_write = 'w' in mode or 'a' in mode or 'x' in mode
    if isinstance(filepath, str) and filepath.lower().endswith('.html') and is_write and 'b' not in mode:
        config = load_branding_config()
        if config and config.get('enabled', False):
            real_file = _original_open(file, mode, buffering, encoding, errors, newline, closefd, opener)
            return BrandedFileWrapper(real_file, filepath, config)
            
    return _original_open(file, mode, buffering, encoding, errors, newline, closefd, opener)

builtins.open = custom_open

# Hook argparse.ArgumentParser.parse_args
_original_parse_args = argparse.ArgumentParser.parse_args

def patched_parse_args(self, args=None, namespace=None):
    # Register --branding-config argument if not already present
    has_branding = any(
        '--branding-config' in action.option_strings 
        for action in self._actions
    )
    if not has_branding:
        self.add_argument('--branding-config', help='Path to custom branding configuration JSON file.')
    return _original_parse_args(self, args, namespace)

argparse.ArgumentParser.parse_args = patched_parse_args
