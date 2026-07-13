"""
Script to format and prettify the minified library-quick-links.html file.
Uses HTMLParser to output a clean, indented, and human-readable HTML file.
"""
import os
import sys
from html.parser import HTMLParser

class HTMLPrettifier(HTMLParser):
    def __init__(self):
        super().__init__()
        self.output = []
        self.indent_level = 0
        self.indent_str = "  "
        self.inline_tags = {'i', 'span', 'a', 'b', 'strong', 'em', 'u'}
        self.current_line = []
        self.in_inline = False

    def write_line(self):
        if self.current_line:
            line_str = "".join(self.current_line)
            # Remove redundant spaces
            line_str = " ".join(line_str.split())
            if line_str:
                indent = self.indent_str * self.indent_level
                self.output.append(f"{indent}{line_str}")
            self.current_line = []

    def handle_starttag(self, tag, attrs):
        # Format attributes
        attrs_parts = []
        for name, value in attrs:
            if value is not None:
                val_esc = value.replace('"', '&quot;')
                attrs_parts.append(f'{name}="{val_esc}"')
            else:
                attrs_parts.append(name)
        attrs_str = " " + " ".join(attrs_parts) if attrs_parts else ""
        
        tag_str = f"<{tag}{attrs_str}>"
        
        if tag in self.inline_tags:
            self.in_inline = True
            self.current_line.append(tag_str)
        else:
            self.write_line()
            self.current_line.append(tag_str)
            self.write_line()
            self.indent_level += 1

    def handle_endtag(self, tag):
        tag_str = f"</{tag}>"
        
        if tag in self.inline_tags:
            self.current_line.append(tag_str)
            # If we exited all inline tags, we can write the line
            self.in_inline = False
        else:
            self.write_line()
            self.indent_level = max(0, self.indent_level - 1)
            self.current_line.append(tag_str)
            self.write_line()

    def handle_data(self, data):
        cleaned = data.strip()
        if cleaned:
            self.current_line.append(cleaned)
            if not self.in_inline:
                self.write_line()

    def handle_comment(self, data):
        self.write_line()
        comment_str = f"<!--{data}-->"
        self.current_line.append(comment_str)
        self.write_line()

    def get_pretty_html(self):
        self.write_line()
        return "\n".join(self.output)

def prettify_file(filepath):
    if not os.path.exists(filepath):
        print(f"Error: File {filepath} not found.")
        return False
        
    print(f"Reading {filepath}...")
    with open(filepath, 'r', encoding='utf-8') as f:
        raw_html = f.read()
        
    print("Formatting HTML...")
    parser = HTMLPrettifier()
    parser.feed(raw_html)
    pretty_html = parser.get_pretty_html()
    
    # Overwrite the file with formatted content
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(pretty_html)
        
    print(f"Successfully cleaned up and formatted {filepath}!")
    return True

if __name__ == '__main__':
    target = 'config/library-quick-links.html'
    prettify_file(target)
