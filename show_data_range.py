"""
Displays the first and last available data dates for a Google Search Console property.

This script connects to the Google Search Console API to determine the exact date
range for which performance data is available for a given site.
"""
import os
import argparse
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta

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
            print(f"Could not load credentials from {TOKEN_FILE}. Error: {e}")
            creds = None

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except exceptions.RefreshError as e:
                print(f"Error refreshing token: {e}")
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

def get_latest_available_gsc_date(service, site_url, max_retries=10):
    """
    Determines the latest date for which GSC data is available by querying
    backwards from today.
    """
    current_date = date.today()
    for i in range(max_retries):
        check_date = current_date - timedelta(days=i)
        check_date_str = check_date.strftime('%Y-%m-%d')
        
        print(f"Checking for latest date: {check_date_str}...")
        try:
            request = {
                'startDate': check_date_str,
                'endDate': check_date_str,
                'dimensions': ['date'],
                'rowLimit': 1
            }
            response = service.searchanalytics().query(siteUrl=site_url, body=request).execute()
            
            if 'rows' in response and response['rows']:
                print(f"Latest available GSC data found for: {check_date_str}")
                return check_date
        except HttpError as e:
            if e.resp.status == 400: # No data for this date
                continue
            print(f"HTTP error on {check_date_str}: {e}")
        except Exception as e:
            print(f"Unexpected error on {check_date_str}: {e}")
            
    print(f"Could not determine latest available GSC date within {max_retries} days.")
    return None

def has_data_on_date(service, site_url, check_date):
    """Checks if there is any GSC data for a specific date."""
    check_date_str = check_date.strftime('%Y-%m-%d')
    try:
        request = {
            'startDate': check_date_str,
            'endDate': check_date_str,
            'dimensions': ['date'],
            'rowLimit': 1
        }
        response = service.searchanalytics().query(siteUrl=site_url, body=request).execute()
        return 'rows' in response and response['rows']
    except HttpError as e:
        if e.resp.status == 400: # No data for this date
            return False
        print(f"HTTP error while checking {check_date_str}: {e}")
        return False
    except Exception as e:
        print(f"Unexpected error while checking {check_date_str}: {e}")
        return False

def get_first_available_gsc_date(service, site_url, latest_date):
    """
    Determines the first date for which GSC data is available using binary search.
    """
    print("Searching for the first available date (this may take a moment)...")
    
    # GSC data is available for approx. 16 months. Search a wider range to be safe.
    low = latest_date - relativedelta(months=17)
    high = latest_date
    
    first_date = None
    
    while low <= high:
        mid = low + (high - low) // 2
        print(f"Searching around: {mid.strftime('%Y-%m-%d')}")
        if has_data_on_date(service, site_url, mid):
            first_date = mid
            high = mid - timedelta(days=1) # Try to find an even earlier date
        else:
            low = mid + timedelta(days=1) # First date must be after mid
            
    return first_date

def main():
    parser = argparse.ArgumentParser(description='Display the first and last available data dates for a GSC property.')
    parser.add_argument('site_url', help='The URL of the site to process (e.g., sc-domain:example.com).')
    
    args = parser.parse_args()
    site_url = args.site_url

    service = get_gsc_service()
    if not service:
        print("Failed to get GSC service.")
        return

    print(f"Finding data availability range for: {site_url}")
    
    latest_date = get_latest_available_gsc_date(service, site_url)
    if not latest_date:
        return
        
    first_date = get_first_available_gsc_date(service, site_url, latest_date)
    if not first_date:
        print("Could not determine the first available date.")
        return
        
    print("----------------------------------")
    print(" GSC Data Availability")
    print("----------------------------------")
    print(f" Property: {site_url}")
    print(f" First available date: {first_date.strftime('%Y-%m-%d')}")
    print(f" Last available date:  {latest_date.strftime('%Y-%m-%d')}")
    print("----------------------------------")

if __name__ == '__main__':
    main()
search