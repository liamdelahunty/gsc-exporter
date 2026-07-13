"""
Script to map the product owner's top 20 quick links list (from library-quick-links.txt)
to their absolute URLs in the cleaned library-quick-links.html file.
"""
import os
import re
from html.parser import HTMLParser

class QuickLinksMapParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []  # List of dicts: {'href': ..., 'text': ..., 'parent_text': ...}
        self.current_href = None
        self.current_text = []
        # Maintain a stack of active topics to determine parents
        self.stack = [] # Stack of {'tag': ..., 'text': ...}
        self.last_item_text = None

    def handle_starttag(self, tag, attrs):
        if tag == 'a':
            for name, value in attrs:
                if name == 'href':
                    self.current_href = value
                    self.current_text = []
                    break

    def handle_endtag(self, tag):
        if tag == 'a' and self.current_href:
            text = " ".join("".join(self.current_text).split())
            parent_text = self.stack[-1]['text'] if self.stack else None
            self.links.append({
                'href': self.current_href,
                'text': text,
                'parent_text': parent_text
            })
            self.last_item_text = text
            self.current_href = None
            
        elif tag == 'li':
            # We finished a list item, pop from stack if we pushed one for this li
            if self.stack and self.stack[-1]['tag'] == 'li':
                self.stack.pop()
                
    def handle_data(self, data):
        if self.current_href:
            self.current_text.append(data)
        else:
            cleaned = data.strip()
            if cleaned and self.last_item_text == cleaned:
                # This was the text of the link we just processed, push it as context for nested lists
                self.stack.append({'tag': 'li', 'text': cleaned})
                self.last_item_text = None

def find_urls():
    txt_path = 'config/library-quick-links.txt'
    html_path = 'config/library-quick-links.html'
    
    if not os.path.exists(txt_path) or not os.path.exists(html_path):
        print("Error: Required files not found.")
        return
        
    # Read top 20 list
    with open(txt_path, 'r', encoding='utf-8') as f:
        lines = [line.strip() for line in f if line.strip()]
        
    # Parse HTML links
    with open(html_path, 'r', encoding='utf-8') as f:
        html_content = f.read()
        
    parser = QuickLinksMapParser()
    parser.feed(html_content)
    parsed_links = parser.links
    
    print(f"Parsed {len(parsed_links)} links from HTML.")
    
    results = []
    
    for line in lines:
        if '|' in line:
            subject, category = [p.strip() for p in line.split('|', 1)]
        else:
            subject = line.strip()
            category = None
            
        # Match subject case-insensitively
        matches = [l for l in parsed_links if l['text'].lower() == subject.lower()]
        
        if not matches:
            # Try partial matching if exact match fails
            matches = [l for l in parsed_links if subject.lower() in l['text'].lower()]
            
        if not matches:
            results.append((line, "NOT FOUND"))
            continue
            
        # Disambiguate if there are multiple matches
        if len(matches) > 1 and category:
            # Try to match the parent category
            best_match = None
            for m in matches:
                # Check if the parent text matches or is related to the category
                if m['parent_text'] and (category.lower() in m['parent_text'].lower() or m['parent_text'].lower() in category.lower()):
                    best_match = m
                    break
            if best_match:
                results.append((line, best_match['href']))
            else:
                # Fallback to the first match
                results.append((line, matches[0]['href']))
        else:
            results.append((line, matches[0]['href']))
            
    print("\n--- Top 20 Quick Links Map ---")
    for subj, url in results:
        print(f"{subj} => {url}")

if __name__ == '__main__':
    find_urls()
