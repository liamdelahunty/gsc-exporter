"""
Core naming logic for the GSC Exporter.
Standardises property-based naming for directories and files.
"""
import os
from urllib.parse import urlparse

def get_property_name(site_url: str) -> str:
    """
    Standardises the GSC property name for use in directory names.
    Maintains dot-notation to preserve uniqueness.
    
    Example:
        'sc-domain:example.com' -> 'sc-domain.example.com'
        'https://www.example.com/' -> 'www.example.com'
    """
    if site_url.startswith('sc-domain:'):
        # Prefix with sc-domain. to distinguish from URL-prefix properties
        return site_url.replace('sc-domain:', 'sc-domain.')
    
    parsed = urlparse(site_url)
    if parsed.netloc:
        return parsed.netloc.lstrip(':')
    
    # Fallback for unexpected formats, ensuring we don't have colons in paths
    return site_url.strip('/').replace(':', '.')

def get_output_dir(site_url: str, base_dir: str = 'output') -> str:
    """
    Returns the output directory path for a given site URL.
    Uses dot-notation for the directory name.
    """
    property_name = get_property_name(site_url)
    return os.path.join(base_dir, property_name)

def get_filename_slug(site_url: str) -> str:
    """
    Converts a site URL into a hyphenated slug for filenames.
    
    Example:
        'sc-domain.example.com' -> 'sc-domain-example-com'
    """
    property_name = get_property_name(site_url)
    return property_name.replace('.', '-')
