import os
import sys
import subprocess
from core.client import get_gsc_service

def get_all_sites(service):
    """Fetches a list of all sites (properties) from the GSC account."""
    try:
        site_list = service.sites().list().execute()
        if 'siteEntry' in site_list:
            # Sort the sites alphabetically for predictable order
            sites = sorted([site['siteUrl'] for site in site_list['siteEntry']])
            return sites
        else:
            print("No sites found in your Google Search Console account.")
            return []
    except Exception as e:
        print(f"An error occurred while fetching the site list: {e}")
        return []

def main():
    """
    Runs the generate_gsc_wrapped.py script for every property in the GSC account.
    Passes any command-line arguments to the underlying script.
    """
    # Get any extra arguments passed to this script to forward them
    extra_args = sys.argv[1:]
    
    print("Authenticating with Google to get the list of all properties...")
    service = get_gsc_service()
    if not service:
        return

    print("\nFetching list of properties...")
    sites = get_all_sites(service)
    
    if not sites:
        return
        
    print(f"\nFound {len(sites)} properties. Preparing to run the Wrapped report for each.")
    print("The following properties will be processed:")
    for site in sites:
        print(f" - {site}")
    
    for site in sites:
        print(f"\n{'='*20} Running for: {site} {'='*20}")
        command = ['python', 'reports/generate_gsc_wrapped.py', site] + extra_args
        
        print(f"Executing command: {' '.join(command)}")
        
        try:
            # We use subprocess.run for simplicity here, similar to run_all_reports_for_site.py
            process = subprocess.run(command, capture_output=False, text=True, check=False)
            
            if process.returncode == 0:
                print(f"\n----- Successfully completed for {site} ----- ")
            else:
                 print(f"\n----- Script finished with return code {process.returncode} for {site} ----- ")

        except Exception as e:
            print(f"\nAn unexpected error occurred while running the script for {site}: {e}")

if __name__ == '__main__':
    main()
