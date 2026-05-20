import os
import re
from urllib.parse import urlparse
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.auth import exceptions

# --- Configuration ---
SCOPES = ['https://www.googleapis.com/auth/webmasters.readonly']
CLIENT_SECRET_FILE = 'client_secret.json'
TOKEN_FILE = 'token.json'
CONFIG_DIR = 'config'

def get_gsc_service():
    """Authenticates and returns a Google Search Console service object."""
    creds = None
    if os.path.exists(TOKEN_FILE):
        try:
            creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
        except Exception as e:
            print(f"Could not load credentials from {TOKEN_FILE}. Error: {e}")
            creds = None

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except exceptions.RefreshError:
                if os.path.exists(TOKEN_FILE):
                    os.remove(TOKEN_FILE)
                creds = None
        
        if not creds:
            if not os.path.exists(CLIENT_SECRET_FILE):
                print(f"Error: {CLIENT_SECRET_FILE} not found.")
                return None
            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        
        with open(TOKEN_FILE, 'w') as token:
            token.write(creds.to_json())

    return build('webmasters', 'v3', credentials=creds)

def get_all_sites(service):
    """Fetches a list of all sites in the user's GSC account."""
    try:
        site_list = service.sites().list().execute()
        return [s['siteUrl'] for s in site_list.get('siteEntry', [])]
    except HttpError as e:
        print(f"An HTTP error occurred while fetching sites: {e}")
        return []

def get_root_domain(site_url):
    """Extracts a clean root domain from a GSC site URL."""
    if site_url.startswith('sc-domain:'):
        return site_url.replace('sc-domain:', '')
    
    hostname = urlparse(site_url).hostname
    if not hostname:
        return None
    
    # Use a regex to find the most likely root domain, handling .co.uk, .com, etc.
    match = re.search(r'([\w-]+\.(?:co\.uk|com\.au|co\.nz|co\.za|co\.il|co\.jp|com|org|net|biz|info))\s*$', hostname.lower())
    if match:
        return match.group(1)
    
    # Fallback for other TLDs
    parts = hostname.split('.')
    if len(parts) > 1:
        return '.'.join(parts[-2:])
    return hostname

def get_brand_terms_from_domain(domain):
    """Generates a set of likely brand terms from a domain name."""
    if not domain:
        return set()

    # Remove common suffixes
    suffixes_to_remove = ['.co.uk', '.com', '.org', '.net', '.gov', '.edu', '.io', '.co']
    for suffix in sorted(suffixes_to_remove, key=len, reverse=True):
        if domain.endswith(suffix):
            domain = domain[:-len(suffix)]
            break
            
    if not domain:
        return set()

    # Generate variations
    terms = {domain}
    if '-' in domain:
        terms.add(domain.replace('-', ' '))
        terms.add(domain.replace('-', ''))
    
    return terms

def main():
    """Fetches all GSC sites, determines unique root domains, and creates default brand term files."""
    os.makedirs(CONFIG_DIR, exist_ok=True)
    
    service = get_gsc_service()
    if not service:
        print("Could not connect to Google Search Console.")
        return

    print("Fetching all properties from your GSC account...")
    all_sites = get_all_sites(service)
    
    if not all_sites:
        print("No sites found in your account.")
        return

    unique_root_domains = {get_root_domain(site) for site in all_sites}
    unique_root_domains.discard(None) # Remove any potential Nones

    print(f"Found {len(unique_root_domains)} unique root domains. Generating brand files...")

    for domain in unique_root_domains:
        brand_terms = get_brand_terms_from_domain(domain)
        if not brand_terms:
            continue

        # Create a simple name for the file from the first part of the domain
        file_name_root = domain.split('.')[0]
        file_path = os.path.join(CONFIG_DIR, f"brand-terms-{file_name_root}.txt")

        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                for term in sorted(list(brand_terms)):
                    f.write(term + '\n')
            print(f"  - Created brand file: {file_path}")
        except IOError as e:
            print(f"  - Error creating file {file_path}: {e}")

    print("\nProcess complete.")

if __name__ == '__main__':
    main()
