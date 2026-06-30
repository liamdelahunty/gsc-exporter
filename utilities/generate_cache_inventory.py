"""
Utility to check GSC cache completeness.
Scans cache directory and reports on presence of "Golden Caches"
(date, page, query, and page+query dimensions) for a site or list of sites.
"""
import os
import sys
import json
import datetime
import calendar
import argparse
import hashlib
from pathlib import Path
from collections import defaultdict
from urllib.parse import urlparse
import pandas as pd

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.naming import get_property_name, get_output_dir, get_filename_slug

try:
    from core.client import get_gsc_service, get_available_properties
    from core.date_utils import (
        get_latest_available_date,
        get_first_available_gsc_date,
        get_first_complete_month_start
    )
    HAS_API = True
except ImportError:
    HAS_API = False

# Golden Dimension Sets to verify
GOLDEN_SETS = [
    (tuple(['date']), "Daily Totals (date)"),
    (tuple(['page']), "Page-level (page)"),
    (tuple(['query']), "Query-level (query)"),
    (tuple(['page', 'query']), "Page-Query (page, query)")
]

DIM_LABELS = {
    tuple(['date']): 'date',
    tuple(['page']): 'page',
    tuple(['query']): 'query',
    tuple(['page', 'query']): 'page+query'
}

def get_base_domain(site_url):
    """Extracts a base domain from a GSC site URL."""
    if site_url.startswith('sc-domain:'):
        return site_url.replace('sc-domain:', '')
    
    hostname = urlparse(site_url).hostname
    if not hostname:
        return site_url

    parts = hostname.split('.')
    if len(parts) > 2 and parts[-2] in ['co', 'com', 'org', 'net', 'gov', 'ac', 'ltd', 'info', 'biz', 'io']:
        return '.'.join(parts[-3:])
    if len(parts) > 1:
        return '.'.join(parts[-2:])
    return hostname

def get_month_range(year, month):
    """Returns the start and end dates of a month."""
    last_day = calendar.monthrange(year, month)[1]
    return f"{year:04d}-{month:02d}-01", f"{year:04d}-{month:02d}-{last_day:02d}"

def get_expected_months(start_date_str=None, end_date_str=None, lookback_months=16):
    """
    Generates a list of dictionaries detailing the target months to verify.
    Sorted in reverse chronological order (latest month first).
    """
    from dateutil.relativedelta import relativedelta
    
    if start_date_str and end_date_str:
        start_date = datetime.datetime.strptime(start_date_str, '%Y-%m-%d').date()
        end_date = datetime.datetime.strptime(end_date_str, '%Y-%m-%d').date()
    else:
        # Default: 16 months lookback from the last complete calendar month
        today = datetime.date.today()
        first_of_this_month = today.replace(day=1)
        end_date = first_of_this_month - datetime.timedelta(days=1)
        start_date = (first_of_this_month - relativedelta(months=lookback_months)).replace(day=1)
        
    expected = []
    curr = start_date.replace(day=1)
    while curr <= end_date:
        y, m = curr.year, curr.month
        m_start, m_end = get_month_range(y, m)
        expected.append({
            'month': f"{y:04d}-{m:02d}",
            'start': m_start,
            'end': m_end
        })
        curr = curr + relativedelta(months=1)
        
    return sorted(expected, key=lambda x: x['month'], reverse=True)

def adjust_expected_months_for_site(service, site_url, expected_months):
    """
    Adjusts the expected check window to match the site's available data range.
    Prevents reporting false positives for dates before the site's GSC history.
    """
    if not service or not HAS_API:
        return expected_months
        
    try:
        latest = get_latest_available_date(service, site_url)
        first_avail = get_first_available_gsc_date(service, site_url, latest, verbose=False)
        if first_avail:
            first_complete_start = get_first_complete_month_start(first_avail)
            if first_complete_start:
                first_complete_start_str = first_complete_start.strftime('%Y-%m-%d')
                # Filter down to months starting on or after the first complete month
                return [m for m in expected_months if m['start'] >= first_complete_start_str]
    except Exception as e:
        print(f"Warning: Could not adjust expected months for site {site_url}: {e}", file=sys.stderr)
        
    return expected_months

def load_cache_inventory():
    """
    Reads all cache JSON files in the cache directory.
    Returns a nested dict: prop_name -> (start_date, end_date) -> set of sorted dimension tuples.
    """
    cache_dir = Path("cache")
    inventory = defaultdict(lambda: defaultdict(set))
    
    if not cache_dir.exists():
        return inventory
        
    for json_file in cache_dir.glob("**/*.json"):
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                site_url = data.get("site_url")
                if not site_url:
                    continue
                prop_name = get_property_name(site_url)
                start_date = data.get("start_date")
                end_date = data.get("end_date")
                dims = data.get("dimensions", [])
                
                dims_tuple = tuple(sorted(dims))
                inventory[prop_name][(start_date, end_date)].add(dims_tuple)
        except Exception:
            continue
            
    return inventory

def determine_sites(site_arg=None, file_arg=None, api_flag=False, cache_inventory=None):
    """
    Resolves the list of site URLs to check.
    If no options provided, scans cache directory to discover cached sites.
    """
    all_sites = []
    
    if site_arg:
        all_sites = [site_arg]
    elif file_arg:
        if os.path.exists(file_arg):
            with open(file_arg, 'r', encoding='utf-8') as f:
                all_sites = [line.strip() for line in f if line.strip() and not line.strip().startswith('#')]
        else:
            print(f"Error: File '{file_arg}' not found.", file=sys.stderr)
            sys.exit(1)
    elif api_flag and HAS_API:
        try:
            service = get_gsc_service()
            all_sites = get_available_properties(service)
        except Exception as e:
            print(f"API discovery failed: {e}. Falling back to cached sites.", file=sys.stderr)
            api_flag = False
            
    if not all_sites and cache_inventory:
        # Offline fallback: scan cache subdirectories
        cached_props = sorted(list(cache_inventory.keys()))
        for prop in cached_props:
            if prop.startswith('sc-domain.'):
                all_sites.append(prop.replace('sc-domain.', 'sc-domain:'))
            else:
                all_sites.append(f"https://{prop}/")
                
    return all_sites

def generate_reports(site_evals, file_suffix, last_month_str, output_dir_str, format_arg):
    """Generates console, CSV, and HTML reports based on the evaluation metadata."""
    output_dir = Path(output_dir_str)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 1. Console Output
    if format_arg in ['all', 'console']:
        print("\n" + "="*80)
        print(" GSC CACHE INVENTORY SUMMARY")
        print("="*80)
        
        for site, data in site_evals.items():
            total = len(data['months'])
            ok_count = sum(1 for m in data['months'] if m['status'] == 'OK')
            
            print(f"\nProperty: {site} ({get_property_name(site)})")
            print(f"Status: {ok_count}/{total} complete months cached")
            
            gaps = [m for m in data['months'] if m['status'] in ['PARTIAL', 'MISSING']]
            if gaps:
                print("Cache Gaps:")
                for gap in gaps:
                    missing_str = ", ".join(gap['missing_labels'])
                    print(f"  - {gap['month']}: {gap['status']} (Missing: {missing_str})")
                print(f"  -> Run command to warm: python utilities/cache_warmer.py {site}")
            else:
                print("  ✓ Cache is 100% complete.")
        print("\n" + "="*80 + "\n")
        
    # Prepare flat table dataset for CSV and HTML
    flat_rows = []
    for site, data in site_evals.items():
        for m in data['months']:
            flat_rows.append({
                'Property': site,
                'Month': m['month'],
                'Status': m['status'],
                'Cached_Dimensions': ";".join(m['cached_labels']),
                'Missing_Dimensions': ";".join(m['missing_labels']),
                'Warming_Command': f"python utilities/cache_warmer.py {site}"
            })
            
    df = pd.DataFrame(flat_rows)
    
    # 2. Save CSV
    if format_arg in ['all', 'csv']:
        csv_filename = f"cache-inventory-{file_suffix}-{last_month_str}.csv"
        csv_path = output_dir / csv_filename
        df.to_csv(csv_path, index=False)
        print(f"CSV Report saved to: {csv_path}")
        
    # 3. Save HTML
    if format_arg in ['all', 'html']:
        html_filename = f"cache-inventory-{file_suffix}-{last_month_str}.html"
        html_path = output_dir / html_filename
        
        # Build HTML content
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write("<!DOCTYPE html>\n<html lang='en'>\n<head>\n")
            f.write("  <meta charset='UTF-8'>\n")
            f.write(f"  <title>GSC Cache Inventory - {last_month_str}</title>\n")
            f.write("  <link href='https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css' rel='stylesheet'>\n")
            f.write("  <style>\n")
            f.write("    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&display=swap');\n")
            f.write("    body {\n")
            f.write("      font-family: 'Outfit', sans-serif;\n")
            f.write("      background-color: #f9fafb;\n")
            f.write("      color: #111827;\n")
            f.write("      padding-top: 2rem;\n")
            f.write("      padding-bottom: 4rem;\n")
            f.write("    }\n")
            f.write("    .card {\n")
            f.write("      background-color: #ffffff;\n")
            f.write("      border: 1px solid #e5e7eb;\n")
            f.write("      border-radius: 12px;\n")
            f.write("      box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);\n")
            f.write("      margin-bottom: 2rem;\n")
            f.write("    }\n")
            f.write("    .card-header {\n")
            f.write("      background-color: #f3f4f6;\n")
            f.write("      border-bottom: 1px solid #e5e7eb;\n")
            f.write("      border-top-left-radius: 12px !important;\n")
            f.write("      border-top-right-radius: 12px !important;\n")
            f.write("      display: flex;\n")
            f.write("      justify-content: space-between;\n")
            f.write("      align-items: center;\n")
            f.write("    }\n")
            f.write("    .table {\n")
            f.write("      color: #374151;\n")
            f.write("      margin-bottom: 0;\n")
            f.write("    }\n")
            f.write("    .table th {\n")
            f.write("      border-bottom: 2px solid #e5e7eb;\n")
            f.write("      background-color: #f9fafb;\n")
            f.write("      color: #4b5563;\n")
            f.write("    }\n")
            f.write("    .table td {\n")
            f.write("      border-bottom: 1px solid #e5e7eb;\n")
            f.write("      background-color: #ffffff;\n")
            f.write("      vertical-align: middle;\n")
            f.write("    }\n")
            f.write("    .table-striped>tbody>tr:nth-of-type(odd)>td {\n")
            f.write("      background-color: #f9fafb;\n")
            f.write("    }\n")
            f.write("    .badge-ok {\n")
            f.write("      background-color: rgba(16, 185, 129, 0.1);\n")
            f.write("      color: #059669;\n")
            f.write("      border: 1px solid rgba(16, 185, 129, 0.2);\n")
            f.write("    }\n")
            f.write("    .badge-partial {\n")
            f.write("      background-color: rgba(245, 158, 11, 0.1);\n")
            f.write("      color: #d97706;\n")
            f.write("      border: 1px solid rgba(245, 158, 11, 0.2);\n")
            f.write("    }\n")
            f.write("    .badge-missing {\n")
            f.write("      background-color: rgba(239, 68, 68, 0.1);\n")
            f.write("      color: #dc2626;\n")
            f.write("      border: 1px solid rgba(239, 68, 68, 0.2);\n")
            f.write("    }\n")
            f.write("    .btn-copy {\n")
            f.write("      background-color: #f3f4f6;\n")
            f.write("      border: 1px solid #d1d5db;\n")
            f.write("      color: #374151;\n")
            f.write("      font-size: 0.8rem;\n")
            f.write("      padding: 0.25rem 0.5rem;\n")
            f.write("      transition: all 0.2s ease;\n")
            f.write("    }\n")
            f.write("    .btn-copy:hover {\n")
            f.write("      background-color: #e5e7eb;\n")
            f.write("      color: #111827;\n")
            f.write("    }\n")
            f.write("    .search-input {\n")
            f.write("      background-color: #ffffff;\n")
            f.write("      border: 1px solid #d1d5db;\n")
            f.write("      color: #111827;\n")
            f.write("    }\n")
            f.write("    .search-input:focus {\n")
            f.write("      background-color: #ffffff;\n")
            f.write("      color: #111827;\n")
            f.write("      border-color: #3b82f6;\n")
            f.write("      box-shadow: 0 0 0 0.25rem rgba(59, 130, 246, 0.15);\n")
            f.write("    }\n")
            f.write("    a {\n")
            f.write("      color: #2563eb;\n")
            f.write("      text-decoration: none;\n")
            f.write("    }\n")
            f.write("    a:hover {\n")
            f.write("      color: #1d4ed8;\n")
            f.write("      text-decoration: underline;\n")
            f.write("    }\n")
            f.write("    .toc-item {\n")
            f.write("      margin-bottom: 0.5rem;\n")
            f.write("    }\n")
            f.write("    code {\n")
            f.write("      color: #b91c1c;\n")
            f.write("      background-color: #f3f4f6;\n")
            f.write("      padding: 0.2rem 0.4rem;\n")
            f.write("      border-radius: 4px;\n")
            f.write("    }\n")
            f.write("  </style>\n")
            f.write("</head>\n<body>\n")
            f.write("  <div class='container'>\n")
            f.write(f"    <h1 class='mb-4'>GSC Cache Inventory - {last_month_str}</h1>\n")
            
            # Overview Panel
            f.write("    <div class='card p-4 mb-4'>\n")
            f.write("      <div class='row align-items-center'>\n")
            f.write("        <div class='col-md-6'>\n")
            f.write("          <h4>Filter Results</h4>\n")
            f.write("          <div class='btn-group' role='group'>\n")
            f.write("            <button type='button' id='btn-filter-all' class='btn btn-primary filter-btn active' onclick=\"filterRows('all')\">All Months</button>\n")
            f.write("            <button type='button' id='btn-filter-gaps' class='btn btn-outline-secondary filter-btn' onclick=\"filterRows('gaps')\">Gaps Only</button>\n")
            f.write("            <button type='button' id='btn-filter-ok' class='btn btn-outline-secondary filter-btn' onclick=\"filterRows('ok')\">Complete Only</button>\n")
            f.write("          </div>\n")
            f.write("        </div>\n")
            f.write("        <div class='col-md-6'>\n")
            f.write("          <h4>Search Properties</h4>\n")
            f.write("          <input type='text' id='propertySearch' class='form-control search-input' placeholder='Search by site domain...'>\n")
            f.write("        </div>\n")
            f.write("      </div>\n")
            f.write("    </div>\n")
            
            # TOC Grouping
            f.write("    <div class='card'>\n")
            f.write("      <div class='card-header'><h2>Properties Directory</h2></div>\n")
            f.write("      <div class='card-body'><div class='row'>\n")
            
            sites_grouped = defaultdict(list)
            for site in site_evals.keys():
                base = get_base_domain(site)
                sites_grouped[base].append(site)
                
            for base in sorted(sites_grouped.keys()):
                f.write(f"        <div class='col-12 col-md-4 mb-3 toc-group'>\n")
                f.write(f"          <h5 class='text-muted border-bottom pb-1'>{base}</h5>\n")
                f.write(f"          <ul class='list-unstyled'>\n")
                for site in sites_grouped[base]:
                    site_id = get_filename_slug(site)
                    total = len(site_evals[site]['months'])
                    ok_count = sum(1 for m in site_evals[site]['months'] if m['status'] == 'OK')
                    if ok_count == total:
                        badge_class = "bg-success"
                        badge_text = f"{ok_count}/{total} OK"
                    elif ok_count >= 12:
                        badge_class = "bg-warning text-dark"
                        badge_text = f"{ok_count}/{total}"
                    else:
                        badge_class = "bg-danger"
                        badge_text = f"{ok_count}/{total}"
                    f.write(f"            <li class='toc-item' data-property='{site}'>")
                    f.write(f"<a href='#{site_id}'>{site}</a> ")
                    f.write(f"<span class='badge {badge_class}'>{badge_text}</span></li>\n")
                f.write("          </ul>\n")
                f.write("        </div>\n")
                
            f.write("      </div></div>\n")
            f.write("    </div>\n")
            
            # Detailed Tables per Property
            for site, data in site_evals.items():
                site_id = get_filename_slug(site)
                total = len(data['months'])
                ok_count = sum(1 for m in data['months'] if m['status'] == 'OK')
                
                f.write(f"    <div class='card property-card' id='{site_id}' data-property='{site}'>\n")
                if ok_count == total:
                    card_badge_class = "bg-success"
                    card_badge_text = f"{ok_count}/{total} OK"
                elif ok_count >= 12:
                    card_badge_class = "bg-warning text-dark"
                    card_badge_text = f"{ok_count}/{total} Complete"
                else:
                    card_badge_class = "bg-danger"
                    card_badge_text = f"{ok_count}/{total} Complete"
                f.write("      <div class='card-header'>\n")
                f.write(f"        <h2 class='m-0'>{site}</h2>\n")
                f.write(f"        <span class='badge {card_badge_class}'>{card_badge_text}</span>\n")
                f.write("      </div>\n")
                f.write("      <div class='card-body p-0'>\n")
                f.write("        <table class='table table-striped table-hover mb-0'>\n")
                f.write("          <thead><tr><th>Month</th><th>Status</th><th>Cached Dimensions</th><th>Missing Dimensions</th><th>Warm Command</th></tr></thead>\n")
                f.write("          <tbody>\n")
                
                for m in data['months']:
                    status = m['status']
                    badge_map = {'OK': 'ok', 'PARTIAL': 'partial', 'MISSING': 'missing'}
                    badge = badge_map.get(status, 'secondary')
                    
                    cached_str = ", ".join(m['cached_labels']) if m['cached_labels'] else "-"
                    missing_str = ", ".join(m['missing_labels']) if m['missing_labels'] else "-"
                    
                    cmd = f"python utilities/cache_warmer.py {site}"
                    cmd_id = f"cmd-{site_id}-{m['month']}"
                    
                    f.write(f"            <tr class='inventory-row' data-status='{status}'>\n")
                    f.write(f"              <td><strong>{m['month']}</strong></td>\n")
                    f.write(f"              <td><span class='badge badge-{badge}'>{status}</span></td>\n")
                    f.write(f"              <td><small>{cached_str}</small></td>\n")
                    f.write(f"              <td><small>{missing_str}</small></td>\n")
                    f.write("              <td>\n")
                    if status != 'OK':
                        f.write(f"                <div class='d-flex align-items-center gap-1'>\n")
                        f.write(f"                  <code>{cmd}</code>\n")
                        f.write(f"                  <button class='btn btn-copy' id='{cmd_id}' onclick=\"copyCommand('{cmd}', '{cmd_id}')\">Copy</button>\n")
                        f.write(f"                </div>\n")
                    else:
                        f.write("                <span class='text-muted'>-</span>\n")
                    f.write("              </td>\n")
                    f.write("            </tr>\n")
                    
                f.write("          </tbody>\n")
                f.write("        </table>\n")
                f.write("      </div>\n")
                f.write("    </div>\n")
                
            f.write("  </div>\n")
            
            # Scripts
            f.write("  <script>\n")
            f.write("    function copyCommand(text, btnId) {\n")
            f.write("      navigator.clipboard.writeText(text).then(function() {\n")
            f.write("        var btn = document.getElementById(btnId);\n")
            f.write("        var originalText = btn.innerHTML;\n")
            f.write("        btn.innerHTML = '✓ Copied!';\n")
            f.write("        btn.classList.remove('btn-copy');\n")
            f.write("        btn.classList.add('btn-success');\n")
            f.write("        setTimeout(function() {\n")
            f.write("          btn.innerHTML = originalText;\n")
            f.write("          btn.classList.remove('btn-success');\n")
            f.write("          btn.classList.add('btn-copy');\n")
            f.write("        }, 1500);\n")
            f.write("      });\n")
            f.write("    }\n\n")
            
            f.write("    document.getElementById('propertySearch').addEventListener('input', function(e) {\n")
            f.write("      var query = e.target.value.toLowerCase();\n")
            f.write("      var cards = document.querySelectorAll('.property-card');\n")
            f.write("      var tocItems = document.querySelectorAll('.toc-item');\n")
            f.write("      var tocGroups = document.querySelectorAll('.toc-group');\n\n")
            
            f.write("      cards.forEach(function(card) {\n")
            f.write("        var title = card.getAttribute('data-property').toLowerCase();\n")
            f.write("        card.style.display = title.includes(query) ? 'block' : 'none';\n")
            f.write("      });\n\n")
            
            f.write("      tocItems.forEach(function(item) {\n")
            f.write("        var title = item.getAttribute('data-property').toLowerCase();\n")
            f.write("        item.style.display = title.includes(query) ? 'block' : 'none';\n")
            f.write("      });\n\n")
            
            f.write("      tocGroups.forEach(function(group) {\n")
            f.write("        var visibleItems = group.querySelectorAll('.toc-item[style=\"display: block\"]');\n")
            f.write("        group.style.display = (visibleItems.length > 0 || query === '') ? 'block' : 'none';\n")
            f.write("      });\n")
            f.write("    });\n\n")
            
            f.write("    function filterRows(type) {\n")
            f.write("      document.querySelectorAll('.filter-btn').forEach(btn => {\n")
            f.write("        btn.classList.remove('active', 'btn-primary');\n")
            f.write("        btn.classList.add('btn-outline-secondary');\n")
            f.write("      });\n")
            f.write("      var activeBtn = document.getElementById('btn-filter-' + type);\n")
            f.write("      activeBtn.classList.remove('btn-outline-secondary');\n")
            f.write("      activeBtn.classList.add('active', 'btn-primary');\n\n")
            
            f.write("      var rows = document.querySelectorAll('.inventory-row');\n")
            f.write("      rows.forEach(function(row) {\n")
            f.write("        var status = row.getAttribute('data-status');\n")
            f.write("        if (type === 'all') {\n")
            f.write("          row.style.display = '';\n")
            f.write("        } else if (type === 'gaps') {\n")
            f.write("          row.style.display = (status === 'MISSING' || status === 'PARTIAL') ? '' : 'none';\n")
            f.write("        } else if (type === 'ok') {\n")
            f.write("          row.style.display = (status === 'OK') ? '' : 'none';\n")
            f.write("        }\n")
            f.write("      });\n")
            f.write("    }\n")
            f.write("  </script>\n")
            f.write("</body>\n</html>\n")
            
        print(f"HTML Report saved to: {html_path}")

def format_dims(dims_list):
    """Formats tuples into short dimension label strings."""
    return [DIM_LABELS.get(d, "+".join(d)) for d in dims_list]

def run_inventory(site_arg=None, file_arg=None, months=16, start_date=None, end_date=None, api_flag=False, output_dir='output/account', format_arg='all'):
    """Executes the cache evaluation process and generates reports."""
    cache_inventory = load_cache_inventory()
    
    # 1. Resolve site list
    sites = determine_sites(site_arg, file_arg, api_flag, cache_inventory)
    if not sites:
        print("Error: No sites resolved to check.", file=sys.stderr)
        sys.exit(1)
        
    # 2. Get baseline expected months
    expected_months = get_expected_months(start_date, end_date, months)
    if not expected_months:
        print("Error: Could not determine expected months from range.", file=sys.stderr)
        sys.exit(1)
        
    last_month_str = expected_months[0]['month']
    
    # Resolve GSC API service if requested
    service = None
    if api_flag and HAS_API:
        try:
            service = get_gsc_service()
        except Exception as e:
            print(f"Failed to connect to GSC API service: {e}. Running offline.", file=sys.stderr)
            
    site_evals = {}
    
    print(f"Analysing cache status for {len(sites)} sites...")
    
    for site in sites:
        prop_name = get_property_name(site)
        
        # Adjust check range if live GSC dates API is accessible
        site_expected = adjust_expected_months_for_site(service, site, expected_months)
        
        site_evals[site] = {'months': []}
        
        for m in site_expected:
            start, end = m['start'], m['end']
            cached_sets = cache_inventory[prop_name].get((start, end), set())
            
            # Check presence of each golden dimension set
            present_sets = []
            missing_sets = []
            for g_set, label in GOLDEN_SETS:
                if g_set in cached_sets:
                    present_sets.append(g_set)
                else:
                    missing_sets.append(g_set)
                    
            if not missing_sets:
                status = 'OK'
            elif len(missing_sets) == len(GOLDEN_SETS):
                status = 'MISSING'
            else:
                status = 'PARTIAL'
                
            site_evals[site]['months'].append({
                'month': m['month'],
                'status': status,
                'cached_labels': format_dims(present_sets),
                'missing_labels': format_dims(missing_sets)
            })
            
    # Resolve file suffix naming
    file_suffix = "all"
    if site_arg:
        file_suffix = get_filename_slug(site_arg)
    elif file_arg:
        file_suffix = Path(file_arg).stem
        
    # Generate requested reports
    generate_reports(site_evals, file_suffix, last_month_str, output_dir, format_arg)

def main():
    parser = argparse.ArgumentParser(description='Investigate GSC cache completeness and identify gaps.')
    
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--site', help='Check cache completeness for a single site URL (e.g. sc-domain:example.com or https://www.example.com/).')
    group.add_argument('--sites-file', help='Path to a text file containing site URLs.')
    
    parser.add_argument('--months', type=int, default=16, help='Number of months to look back (default 16).')
    parser.add_argument('--start-date', help='Check cache starting from date YYYY-MM-DD (requires --end-date).')
    parser.add_argument('--end-date', help='Check cache ending at date YYYY-MM-DD (requires --start-date).')
    
    parser.add_argument('--api', action='store_true', help='Use GSC API to dynamically filter out expected months before property creation.')
    parser.add_argument('--output-dir', default='output/account', help='Directory to save output reports (default: output/account).')
    parser.add_argument('--format', choices=['all', 'html', 'csv', 'console'], default='all', 
                        help='Report format: console, csv, html, or all (default).')
                        
    args = parser.parse_args()
    
    # Verify range arguments
    if (args.start_date and not args.end_date) or (args.end_date and not args.start_date):
        parser.error('--start-date and --end-date must be used together.')
        
    run_inventory(
        site_arg=args.site,
        file_arg=args.sites_file,
        months=args.months,
        start_date=args.start_date,
        end_date=args.end_date,
        api_flag=args.api,
        output_dir=args.output_dir,
        format_arg=args.format
    )

if __name__ == '__main__':
    main()
