"""
Lists all Google Search Console properties (sites) a user has access to.

This script authenticates with the Google Search Console API, fetches the list of all
sites associated with the user's account, and displays them grouped by base domain.
"""
import os
from collections import defaultdict
from urllib.parse import urlparse

# --- Google API Imports ---
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

def get_gsc_service():
    """Authenticates and returns a Google Search Console service object."""
    creds = None
    if os.path.exists(TOKEN_FILE):
        try:
            creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
        except Exception as e:
            print(f"Could not load credentials from {TOKEN_FILE}. Error: {e}\nWill attempt to re-authenticate.")
            creds = None

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                print("Credentials have expired. Attempting to refresh...")
                creds.refresh(Request())
            except exceptions.RefreshError as e:
                print(f"Error refreshing token: {e}\nDeleting token and re-authenticating.")
                if os.path.exists(TOKEN_FILE):
                    os.remove(TOKEN_FILE)
                creds = None
        
        if not creds:
            if not os.path.exists(CLIENT_SECRET_FILE):
                print(f"Error: {CLIENT_SECRET_FILE} not found. Please follow setup instructions.")
                return None
            
            print("A browser window will open for you to authorize access.")
            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        
        with open(TOKEN_FILE, 'w') as token:
            token.write(creds.to_json())
            print("Authentication successful. Credentials saved.")

    return build('webmasters', 'v3', credentials=creds)

def get_sites_from_api(service):
    """Fetches all sites from the GSC API."""
    try:
        print("Fetching sites from Google Search Console API...")
        site_list = service.sites().list().execute()
        if 'siteEntry' in site_list:
            return [entry['siteUrl'] for entry in site_list['siteEntry']]
        else:
            print("No sites found for this account.")
            return []
    except HttpError as e:
        print(f"An HTTP error occurred: {e}")
        return None
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return None

def get_base_domain(site_url):
    """Extracts a base domain from a GSC site URL."""
    if site_url.startswith('sc-domain:'):
        return site_url.replace('sc-domain:', '')
    
    hostname = urlparse(site_url).hostname
    if not hostname:
        return site_url # Fallback for unusual cases

    parts = hostname.split('.')
    if len(parts) > 2 and parts[-2] in ['co', 'com', 'org', 'net', 'gov', 'ac', 'ltd', 'info', 'biz', 'io']:
        return '.'.join(parts[-3:])
    if len(parts) > 1:
        return '.'.join(parts[-2:])
    return hostname

if __name__ == "__main__":
    service = get_gsc_service()
    if not service:
        exit()

    all_sites = get_sites_from_api(service)
    if all_sites:
        sites_grouped = defaultdict(list)
        for site in all_sites:
            base = get_base_domain(site)
            sites_grouped[base].append(site)

        print("\nAvailable sites for use in reports (choose the correct format based on your GSC property type):\n")
        
        for base_domain in sorted(sites_grouped.keys()):
            print(f"# {base_domain}")
            
            properties = sites_grouped[base_domain]
            
            def sort_key(prop_string):
                """Sorts properties by sc-domain, then www, then base domain, then alphabetically."""
                if prop_string == f"sc-domain:{base_domain}":
                    return (0, prop_string) # Domain property
                if prop_string == f"https://www.{base_domain}":
                    return (1, prop_string) # www version
                if prop_string == f"https://{base_domain}":
                    return (2, prop_string) # Base domain as URL property
                return (3, prop_string) # Other URL-prefix properties

            for prop in sorted(properties, key=sort_key):
                print(prop)
            print("")
            
    else:
        print("Could not retrieve any sites.")
