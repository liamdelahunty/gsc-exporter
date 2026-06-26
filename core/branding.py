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
    """
    config_path = get_config_path()
    if not os.path.exists(config_path):
        return None
    try:
        with _original_open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        return config
    except Exception as e:
        print(f"Warning: Failed to load branding configuration from {config_path}: {e}")
        return None

def apply_branding_to_html(html_content: str, filepath: str, config: dict) -> str:
    """
    Applies the custom branding configuration to the HTML content.
    Injects custom CSS styling and inserts/replaces headers and footers.
    """
    if not config or not config.get('enabled', False):
        return html_content

    theme = config.get('theme', {})
    primary_colour = theme.get('primary_colour', theme.get('primary_color', '#2c3e50'))
    text_colour = theme.get('text_colour', theme.get('text_color', '#ffffff'))
    font_family = theme.get('font_family', "'Outfit', sans-serif")

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
            padding: 8px 24px;
            font-size: 0.9rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid rgba(0,0,0,0.1);
        }}
        .branded-top-bar a {{
            color: var(--branding-text) !important;
            text-decoration: none;
            font-weight: 600;
        }}
        .branded-bottom-bar {{
            background-color: var(--branding-primary) !important;
            color: var(--branding-text) !important;
            font-family: var(--branding-font);
            padding: 12px 24px;
            font-size: 0.85rem;
            text-align: center;
            border-top: 1px solid rgba(0,0,0,0.1);
        }}
        .branded-bottom-bar a {{
            color: var(--branding-text) !important;
            text-decoration: none;
            margin: 0 10px;
        }}
        /* Override standard bootstrap classes if configured */
        header.branded-replaced-header {{
            background-color: var(--branding-primary) !important;
            color: var(--branding-text) !important;
            font-family: var(--branding-font);
            padding: 15px 24px;
        }}
        header.branded-replaced-header a {{
            color: var(--branding-text) !important;
        }}
        footer.branded-replaced-footer {{
            background-color: var(--branding-primary) !important;
            color: var(--branding-text) !important;
            font-family: var(--branding-font);
            padding: 20px 24px;
            text-align: center;
        }}
        footer.branded-replaced-footer a {{
            color: var(--branding-text) !important;
        }}
    </style>
    """

    # Inject CSS before </head>
    if '</head>' in html_content:
        html_content = html_content.replace('</head>', f'{css_styles}\n</head>', 1)
    elif '<head>' in html_content:
        html_content = html_content.replace('<head>', f'<head>\n{css_styles}', 1)

    # Process Header Branding
    header_cfg = config.get('header', {})
    if header_cfg.get('enabled', False):
        mode = header_cfg.get('mode', 'inject')
        logo_url = header_cfg.get('logo_url', '')
        link_url = header_cfg.get('link_url', '#')
        text = header_cfg.get('text', '')

        # Build logo/text HTML fragment
        logo_html = ""
        if logo_url:
            logo_html = f'<img src="{logo_url}" alt="Logo" height="30" style="vertical-align: middle; margin-right: 10px;">'

        header_brand_html = f'<a href="{link_url}" target="_blank" style="text-decoration: none; display: inline-flex; align-items: center; color: inherit;">{logo_html}<span style="font-weight: bold;">{text}</span></a>'

        if mode == 'replace':
            pattern = re.compile(r'<header[^>]*>.*?</header>', re.DOTALL | re.IGNORECASE)
            new_header = f"""
            <header class="branded-replaced-header mb-4">
                <div class="container-fluid d-flex justify-content-between align-items-center">
                    {header_brand_html}
                    <div>
                        <span style="opacity: 0.85; font-size: 0.95rem;">Performance Report</span>
                    </div>
                </div>
            </header>
            """
            if pattern.search(html_content):
                html_content = pattern.sub(new_header, html_content, count=1)
            else:
                body_pattern = re.compile(r'(<body[^>]*>)', re.IGNORECASE)
                if body_pattern.search(html_content):
                    html_content = body_pattern.sub(r'\1' + new_header, html_content, count=1)

        elif mode == 'bar':
            top_bar_html = f"""
            <div class="branded-top-bar">
                <div>
                    {header_brand_html}
                </div>
                <div>
                    <span style="opacity: 0.85; font-size: 0.85rem;">Google Search Console Insights</span>
                </div>
            </div>
            """
            body_pattern = re.compile(r'(<body[^>]*>)', re.IGNORECASE)
            if body_pattern.search(html_content):
                html_content = body_pattern.sub(r'\1' + top_bar_html, html_content, count=1)

        elif mode == 'inject':
            # Prepend the brand inside the first div of the header
            header_match = re.search(r'(<header[^>]*>.*?<div[^>]*>)', html_content, re.DOTALL | re.IGNORECASE)
            if header_match:
                matched_str = header_match.group(1)
                injected_brand = f'<div class="me-3 d-inline-block align-self-center">{header_brand_html}</div>'
                html_content = html_content.replace(matched_str, matched_str + injected_brand, 1)
            else:
                # Fallback to bar mode
                top_bar_html = f"""
                <div class="branded-top-bar">
                    <div>
                        {header_brand_html}
                    </div>
                    <div>
                        <span style="opacity: 0.85; font-size: 0.85rem;">Google Search Console Insights</span>
                    </div>
                </div>
                """
                body_pattern = re.compile(r'(<body[^>]*>)', re.IGNORECASE)
                if body_pattern.search(html_content):
                    html_content = body_pattern.sub(r'\1' + top_bar_html, html_content, count=1)

    # Process Footer Branding
    footer_cfg = config.get('footer', {})
    if footer_cfg.get('enabled', False):
        mode = footer_cfg.get('mode', 'inject')
        logo_url = footer_cfg.get('logo_url', '')
        link_url = footer_cfg.get('link_url', '#')
        text = footer_cfg.get('text', '')
        links = footer_cfg.get('links', [])

        logo_html = ""
        if logo_url:
            logo_html = f'<img src="{logo_url}" alt="Logo" height="20" style="vertical-align: middle; margin-right: 10px;">'

        links_html = ""
        if links:
            links_html = " | ".join(f'<a href="{lnk.get("url", "#")}" target="_blank">{lnk.get("text", "")}</a>' for lnk in links)

        footer_brand_html = f"""
        <div class="d-inline-flex align-items-center">
            {logo_html}
            <span>{text}</span>
        </div>
        """
        if links_html:
            footer_brand_html += f'<div class="mt-2">{links_html}</div>'

        if mode == 'replace':
            pattern = re.compile(r'<footer[^>]*>.*?</footer>', re.DOTALL | re.IGNORECASE)
            new_footer = f"""
            <footer class="branded-replaced-footer mt-4">
                <div class="container-fluid">
                    {footer_brand_html}
                </div>
            </footer>
            """
            if pattern.search(html_content):
                html_content = pattern.sub(new_footer, html_content, count=1)
            else:
                body_close_pattern = re.compile(r'(</body>)', re.IGNORECASE)
                if body_close_pattern.search(html_content):
                    html_content = body_close_pattern.sub(new_footer + r'\1', html_content, count=1)

        elif mode == 'bar':
            bottom_bar_html = f"""
            <div class="branded-bottom-bar mt-4">
                {footer_brand_html}
            </div>
            """
            body_close_pattern = re.compile(r'(</body>)', re.IGNORECASE)
            if body_close_pattern.search(html_content):
                html_content = body_close_pattern.sub(bottom_bar_html + r'\1', html_content, count=1)

        elif mode == 'inject':
            footer_close_match = re.search(r'(</footer>)', html_content, re.IGNORECASE)
            if footer_close_match:
                injected_footer = f'<div class="container mt-2 border-top pt-2" style="border-color: rgba(0,0,0,0.1) !important;">{footer_brand_html}</div>'
                html_content = html_content.replace('</footer>', injected_footer + '</footer>', 1)
            else:
                bottom_bar_html = f"""
                <div class="branded-bottom-bar mt-4">
                    {footer_brand_html}
                </div>
                """
                body_close_pattern = re.compile(r'(</body>)', re.IGNORECASE)
                if body_close_pattern.search(html_content):
                    html_content = body_close_pattern.sub(bottom_bar_html + r'\1', html_content, count=1)

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
