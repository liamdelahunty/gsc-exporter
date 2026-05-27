import os
import json
import datetime
import argparse
from pathlib import Path
from collections import defaultdict
from urllib.parse import urlparse

# --- Google API Imports ---
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

# --- Configuration ---
SCOPES = ['https://www.googleapis.com/auth/webmasters.readonly']
CLIENT_SECRET_FILE = 'client_secret.json'
TOKEN_FILE = 'token.json'

def get_gsc_service():
    """Authenticates and returns a Google Search Console service object."""
    creds = None
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception as e:
                print(f"Error refreshing token: {e}. Re-authenticating.")
                if os.path.exists(TOKEN_FILE):
                    os.remove(TOKEN_FILE)
                creds = None
        
        if not creds:
            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        
        with open(TOKEN_FILE, 'w') as token:
            token.write(creds.to_json())

    return build('webmasters', 'v3', credentials=creds)

def get_sites_from_api(service):
    """Fetches all sites from the GSC API."""
    site_list = service.sites().list().execute()
    if 'siteEntry' in site_list:
        return [entry['siteUrl'] for entry in site_list['siteEntry']]
    return []

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

def get_last_complete_month():
    today = datetime.date.today()
    first_day_of_current_month = today.replace(day=1)
    last_day_of_prev_month = first_day_of_current_month - datetime.timedelta(days=1)
    return last_day_of_prev_month.strftime("%Y-%m")

def generate_inventory(sites_file_path):
    cache_dir = Path("cache")
    
    # Load sites
    if sites_file_path and os.path.exists(sites_file_path):
        sites_file = Path(sites_file_path)
        with open(sites_file, 'r') as f:
            all_sites = [line.strip() for line in f if line.strip() and not line.strip().startswith('#')]
    else:
        # Default behavior: discover all sites from API
        service = get_gsc_service()
        all_sites = get_sites_from_api(service)
        all_sites = sorted(all_sites)
    
    inventory = {site: {} for site in all_sites}
    
    for json_file in cache_dir.glob("*.json"):
        with open(json_file, 'r') as f:
            try:
                data = json.load(f)
                site = data.get("site_url")
                if site not in inventory:
                    continue
                
                month = data["start_date"][:7] 
                
                if month not in inventory[site]:
                    inventory[site][month] = True
            except Exception:
                continue
                
    last_month_str = get_last_complete_month()
    
    # Load sites and determine filename suffix
    file_suffix = "all"
    if sites_file_path and os.path.exists(sites_file_path):
        sites_file = Path(sites_file_path)
        file_suffix = sites_file.stem
    
    last_month_date = datetime.datetime.strptime(last_month_str, "%Y-%m").date()
    
    # Build list of all months found to handle older-than-16-months data
    all_found_months = set()
    for site_months in inventory.values():
        all_found_months.update(site_months.keys())
    
    # Calculate expected months (16 months + anything older found)
    expected_months_list = []
    for i in range(16):
        d = last_month_date - datetime.timedelta(days=i*28)
        expected_months_list.append(d.strftime("%Y-%m"))
    
    # Add any found months that are older than the 16 month window
    all_months = sorted(list(set(expected_months_list) | all_found_months), reverse=True)

    output_path = Path(f"output/account/cache-inventory-{file_suffix}-{last_month_str}.html")
    
    with open(output_path, 'w') as f:
        f.write("<!DOCTYPE html><html lang='en'><head><meta charset='UTF-8'><title>Cache Inventory</title>")
        f.write("<link href='https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css' rel='stylesheet'>")
        f.write("<style>body { padding-top: 2rem; } h2 { margin: 0; font-size: 1.25rem; }</style></head><body>")
        f.write("<div class='container'><h1>Cache Inventory - " + last_month_str + "</h1>")
        
        # Options Info
        f.write("<div class='card mb-4'><div class='card-header'><h2>Report Options</h2></div><div class='card-body'>")
        f.write(f"<p><strong>Sites Source:</strong> {sites_file_path if sites_file_path else 'All Available Properties (API)'}</p>")
        f.write("<p><strong>How to use a custom site list:</strong> Run the script with the <code>--sites-file</code> flag: <code>python utilities/generate_cache_inventory.py --sites-file site-lists/your-list.txt</code></p>")
        f.write("</div></div>")
        
        # Add Property TOC
        f.write("<div class='card mb-4'><div class='card-header'><h2>Properties</h2></div><div class='card-body'><div class='row'>")
        
        # Sort and Group Sites
        sites_grouped = defaultdict(list)
        for site in all_sites:
            base = get_base_domain(site)
            sites_grouped[base].append(site)
        
        sorted_bases = sorted(sites_grouped.keys())
        
        # Prepare a flat list of properties with their sorting keys
        # We store items as (base, prop) to allow tracking gaps
        items = []
        for base in sorted_bases:
            properties = sites_grouped[base]
            
            def sort_key(prop_string):
                # sc-domain first
                if prop_string.startswith('sc-domain:'): return (0, prop_string)
                # www second
                hostname = prop_string.replace('https://', '').replace('http://', '').split('/')[0]
                if hostname.startswith('www.'): return (1, prop_string)
                # others third
                return (2, prop_string)
                
            sorted_props = sorted(properties, key=sort_key)
            # Add items, marking the first of each group for potential gap logic
            for i, prop in enumerate(sorted_props):
                items.append({'base': base, 'prop': prop, 'is_first_of_base': i == 0})

        # Intelligent Column Distribution
        # 4 columns (xxl), 3 (xl), 2 (lg/md), 1 (sm)
        # We'll aim for balanced distribution.
        total_items = len(items)
        # Add estimated gap count for balanced height (approx 1 gap per base domain)
        num_bases = len(sorted_bases)
        total_height = total_items + (num_bases - 1)
        
        target_col_height = (total_height + 3) // 4
        
        # Distribute into columns
        columns = [[] for _ in range(4)]
        current_col = 0
        current_col_height = 0
        
        for item in items:
            # Check if this item (plus potential gap) fits in current column
            item_height = 1
            if item['is_first_of_base'] and current_col_height > 0:
                item_height += 1 # Gap
                
            if current_col_height + item_height > target_col_height and current_col < 3:
                current_col += 1
                current_col_height = 0
                
            columns[current_col].append(item)
            current_col_height += item_height
            
        f.write("<div class='col-12 col-md-6 col-xl-4 col-xxl-3'><ul>")
        
        last_base = None
        for col_idx, col_items in enumerate(columns):
            if col_idx > 0:
                f.write("</ul></div><div class='col-12 col-md-6 col-xl-4 col-xxl-3'><ul>")
            
            for i, item in enumerate(col_items):
                # Check if this is the last item of the current base domain group
                is_last_of_group = False
                if i < len(col_items) - 1:
                    if col_items[i+1]['base'] != item['base']:
                        is_last_of_group = True
                
                # Apply mb-3 to the last item of a group
                mb_class = "mb-3" if is_last_of_group else ""
                
                site_id = item['prop'].replace('https://', '').replace('http://', '').replace('/', '').replace('.', '-')
                f.write(f"<li class='{mb_class}'><a href='#{site_id}'>{item['prop']}</a></li>")
                last_base = item['base']
                
        f.write("</ul></div></div></div></div>")
        
        for site in all_sites:
            site_id = site.replace('https://', '').replace('http://', '').replace('/', '').replace('.', '-')
            f.write(f"<div class='card mb-4' id='{site_id}'><div class='card-header'><h2>{site}</h2></div><div class='card-body'>")
            f.write("<table class='table table-striped table-hover'><thead><tr><th>Month</th><th>Status</th><th>Command</th></tr></thead><tbody>")
            
            for month in all_months:
                # Limit display to last 16 months for the "MISSING" logic, but show found older ones as OK
                is_within_window = month in expected_months_list
                status = "OK"
                badge = "success"
                command = ""
                
                if month not in inventory[site]:
                    if is_within_window:
                        status = "MISSING"
                        badge = "danger"
                        command = f"python reports/snapshot_report.py {site} --start-date {month}-01"
                    else:
                        status = "N/A"
                        badge = "secondary"
                
                f.write(f"<tr><td>{month}</td><td><span class='badge bg-{badge}'>{status}</span></td><td><code>{command}</code></td></tr>")
            
            f.write("</tbody></table></div></div>")
        
        f.write("</div></body></html>")

    print(f"Report generated: {output_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Generate cache inventory report.')
    parser.add_argument('--sites-file', help='Path to a text file containing site URLs.')
    args = parser.parse_args()
    generate_inventory(args.sites_file)
