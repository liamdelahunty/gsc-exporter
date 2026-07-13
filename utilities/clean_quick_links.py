"""
Script to strip all unnecessary HTML structure and attributes from library-quick-links.html.
Preserves only the nested lists (ol, li) and the links (a) with their hrefs and titles.
"""
import os
import sys
from html.parser import HTMLParser

class QuickLinksCleaner(HTMLParser):
    def __init__(self):
        super().__init__()
        self.output = []
        self.indent_level = 0
        self.indent_str = "  "
        self.in_a = False
        self.a_href = ""
        self.a_text_parts = []
        
    def write_line(self, text):
        indent = self.indent_str * self.indent_level
        self.output.append(f"{indent}{text}")

    def handle_starttag(self, tag, attrs):
        if tag == 'ol':
            self.write_line("<ol>")
            self.indent_level += 1
        elif tag == 'li':
            self.write_line("<li>")
            self.indent_level += 1
        elif tag == 'a':
            self.in_a = True
            self.a_text_parts = []
            # Extract only href and make it absolute
            for name, value in attrs:
                if name == 'href':
                    if value.startswith('/'):
                        self.a_href = "https://library.croneri.co.uk" + value
                    elif not value.startswith('http'):
                        self.a_href = "https://library.croneri.co.uk/" + value
                    else:
                        self.a_href = value
                    break

    def handle_endtag(self, tag):
        if tag == 'ol':
            self.indent_level = max(0, self.indent_level - 1)
            self.write_line("</ol>")
        elif tag == 'li':
            self.indent_level = max(0, self.indent_level - 1)
            self.write_line("</li>")
        elif tag == 'a':
            self.in_a = False
            title = " ".join("".join(self.a_text_parts).split())
            href_esc = self.a_href.replace('"', '&quot;')
            self.write_line(f'<a href="{href_esc}">{title}</a>')

    def handle_data(self, data):
        if self.in_a:
            self.a_text_parts.append(data)

    def get_clean_html(self):
        return "\n".join(self.output)

def clean_file(filepath):
    if not os.path.exists(filepath):
        print(f"Error: File {filepath} not found.")
        return False
        
    print(f"Reading source from {filepath}...")
    with open(filepath, 'r', encoding='utf-8') as f:
        raw_html = f.read()
        
    print("Stripping HTML tags and attributes, and converting to absolute links...")
    parser = QuickLinksCleaner()
    parser.feed(raw_html)
    clean_html = parser.get_clean_html()
    
    # Overwrite the html file with cleaned absolute link output
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(clean_html)
        
    print(f"Successfully cleaned quick links and saved to {filepath}!")
    return True

if __name__ == '__main__':
    target = 'config/library-quick-links.html'
    clean_file(target)
