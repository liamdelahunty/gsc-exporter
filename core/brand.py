"""
Utility for brand-detection logic in GSC Exporter.
"""
import os
import re
from urllib.parse import urlparse

def get_brand_terms(site_url, brand_terms=None, brand_terms_file=None, no_brand_detection=False):
    """
    Determines the set of brand terms for a site.
    Priority:
    1. brand_terms (list)
    2. brand_terms_file (path)
    3. config/brand-terms-{slug}.txt
    4. Automatic detection from site_url
    """
    if no_brand_detection:
        return set()

    all_brand_terms = set()

    # 1. Manual terms
    if brand_terms:
        all_brand_terms.update(brand_terms)

    # 2. Manual file
    if brand_terms_file and os.path.exists(brand_terms_file):
        with open(brand_terms_file, 'r', encoding='utf-8') as f:
            all_brand_terms.update(line.strip() for line in f if line.strip())

    # 3. Config file
    if not all_brand_terms:
        from core.naming import get_filename_slug
        slug = get_filename_slug(site_url)
        # Try a few variations of the slug for the brand file
        # e.g. brand-terms-hr-inform-co-uk.txt or brand-terms-hr-inform.txt
        config_dir = 'config'
        if os.path.exists(config_dir):
            # Try full slug first
            brand_file = os.path.join(config_dir, f"brand-terms-{slug}.txt")
            if os.path.exists(brand_file):
                with open(brand_file, 'r', encoding='utf-8') as f:
                    all_brand_terms.update(line.strip() for line in f if line.strip())
            else:
                # Try domain root (e.g. hr-inform)
                hostname = urlparse(site_url).hostname
                if not hostname and site_url.startswith('sc-domain:'):
                    hostname = site_url.replace('sc-domain:', '')
                
                if hostname:
                    root = hostname.split('.')[0] if not hostname.startswith('www.') else hostname.split('.')[1]
                    brand_file = os.path.join(config_dir, f"brand-terms-{root}.txt")
                    if os.path.exists(brand_file):
                        with open(brand_file, 'r', encoding='utf-8') as f:
                            all_brand_terms.update(line.strip() for line in f if line.strip())

    # 4. Automatic detection
    if not all_brand_terms:
        hostname = urlparse(site_url).hostname
        if not hostname:
            if site_url.startswith('sc-domain:'):
                hostname = site_url.replace('sc-domain:', '')
            else:
                return set()

        suffixes_to_remove = ['.com', '.co.uk', '.org', '.net', '.gov', '.edu', '.io', '.co']
        if hostname.startswith('www.'):
            hostname = hostname[4:]
            
        for suffix in sorted(suffixes_to_remove, key=len, reverse=True):
            if hostname.endswith(suffix):
                hostname = hostname[:-len(suffix)]
                break
                
        if hostname:
            all_brand_terms.add(hostname)
            if '-' in hostname:
                all_brand_terms.add(hostname.replace('-', ' '))
                all_brand_terms.add(hostname.replace('-', ''))

    return all_brand_terms

def classify_query(query, brand_terms):
    """Returns True if the query contains any brand terms."""
    if not brand_terms:
        return False
    
    # Use word boundaries for precise matching
    pattern = r'\b(?:' + '|'.join(re.escape(term) for term in brand_terms) + r')\b'
    return bool(re.search(pattern, query, re.IGNORECASE))
