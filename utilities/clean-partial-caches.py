"""
Utility to identify and clean partial or corrupted Google Search Console cache files.

This script scans the GSC cache directory and finds JSON cache files that are:
1. Not complete calendar months (i.e. do not start on the 1st and end on the last day of the month).
2. Corrupted or invalid JSON structures.

By default, it runs in dry-run mode. Run with the --delete flag to delete these cache files.
It saves an HTML report under output/account/ detailing the invalid caches with copy-pasteable commands to re-warm them.
"""

import os
import sys
import json
import calendar
import argparse
from pathlib import Path
from datetime import datetime

CACHE_DIR = Path("cache")

def is_full_month(start_date_str, end_date_str):
    """
    Checks if the given start and end date strings represent a full calendar month.
    """
    try:
        start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
        end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return False

    # Must start on the 1st day of the month
    if start_date.day != 1:
        return False

    # Must belong to the same month and year
    if start_date.year != end_date.year or start_date.month != end_date.month:
        return False

    # Must end on the last day of that calendar month
    last_day = calendar.monthrange(start_date.year, start_date.month)[1]
    if end_date.day != last_day:
        return False

    return True

def generate_html_report(bad_caches, total_scanned, delete_files, max_days=None):
    """
    Generates a beautiful HTML report of invalid caches and saves it to output/account/.
    """
    output_dir = Path("output/account")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    today_str = datetime.today().strftime('%Y-%m-%d')
    html_filename = f"invalid-caches-report-{today_str}.html"
    html_path = output_dir / html_filename
    
    # Group bad caches by site/property
    grouped_caches = {}
    for item in bad_caches:
        site = item["site"]
        if site not in grouped_caches:
            grouped_caches[site] = []
        grouped_caches[site].append(item)
        
    filter_desc = f" (Max Duration: {max_days} days)" if max_days else ""
    action_text = f"Deleted{filter_desc}" if delete_files else f"Dry-Run Only (No Files Deleted){filter_desc}"
    action_class = "text-danger" if delete_files else "text-warning"
    
    # Construct exact deletion command for the dry-run warning card
    delete_cmd_parts = ["python utilities/clean-partial-caches.py", "--delete"]
    if max_days:
        delete_cmd_parts.extend(["--max-days", str(max_days)])
    delete_cmd = " ".join(delete_cmd_parts)
    
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write("<!DOCTYPE html>\n<html lang='en'>\n<head>\n")
        f.write("  <meta charset='UTF-8'>\n")
        f.write(f"  <title>GSC Invalid Cache Report - {today_str}</title>\n")
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
        f.write("    }\n")
        f.write("    .table th {\n")
        f.write("      border-bottom: 2px solid #e5e7eb;\n")
        f.write("      background-color: #f9fafb;\n")
        f.write("      color: #4b5563;\n")
        f.write("    }\n")
        f.write("    .table td {\n")
        f.write("      border-bottom: 1px solid #e5e7eb;\n")
        f.write("      vertical-align: middle;\n")
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
        f.write("    code {\n")
        f.write("      color: #b91c1c;\n")
        f.write("      background-color: #f3f4f6;\n")
        f.write("      padding: 0.2rem 0.4rem;\n")
        f.write("      border-radius: 4px;\n")
        f.write("    }\n")
        f.write("    .search-input {\n")
        f.write("      border: 1px solid #d1d5db;\n")
        f.write("    }\n")
        f.write("  </style>\n")
        f.write("</head>\n<body>\n")
        f.write("  <div class='container'>\n")
        f.write(f"    <h1 class='mb-4'>GSC Invalid Cache Report</h1>\n")
        
        # Summary Info
        f.write("    <div class='row mb-4'>\n")
        f.write("      <div class='col-md-4'>\n")
        f.write("        <div class='card p-3 text-center'>\n")
        f.write("          <div class='text-muted small'>Scanned Cache Files</div>\n")
        f.write(f"          <div class='fs-2 fw-bold'>{total_scanned}</div>\n")
        f.write("        </div>\n")
        f.write("      </div>\n")
        f.write("      <div class='col-md-4'>\n")
        f.write("        <div class='card p-3 text-center'>\n")
        f.write("          <div class='text-muted small'>Matching Invalid Cache Files</div>\n")
        f.write(f"          <div class='fs-2 fw-bold text-danger'>{len(bad_caches)}</div>\n")
        f.write("        </div>\n")
        f.write("      </div>\n")
        f.write("      <div class='col-md-4'>\n")
        f.write("        <div class='card p-3 text-center'>\n")
        f.write("          <div class='text-muted small'>Action Taken</div>\n")
        f.write(f"          <div class='fs-5 fw-bold {action_class} mt-2'>{action_text}</div>\n")
        f.write("        </div>\n")
        f.write("      </div>\n")
        f.write("    </div>\n")
        
        # Action Required Deletion Card (Dry-Run Only)
        if not delete_files:
            f.write("    <div class='card border-warning p-4 mb-4' style='background-color: #fffbeb;'>\n")
            f.write("      <h4 class='text-warning-emphasis mb-2'>Action Required: Run Deletion Command</h4>\n")
            f.write("      <p class='text-muted mb-3'>This report was generated in <strong>Dry-Run Mode</strong>. No files have been deleted. To delete these invalid cache files from disk, run the following command in your terminal:</p>\n")
            f.write("      <div class='d-flex align-items-center gap-2'>\n")
            f.write(f"        <code class='fs-5 p-2 bg-light border rounded flex-grow-1'>{delete_cmd}</code>\n")
            f.write(f"        <button class='btn btn-warning text-dark fw-medium' id='btn-copy-delete-cmd' onclick=\"copyCommand('{delete_cmd}', 'btn-copy-delete-cmd')\">Copy Command</button>\n")
            f.write("      </div>\n")
            f.write("    </div>\n")
            
        # Search & Filter
        f.write("    <div class='card p-3 mb-4'>\n")
        f.write("      <div class='row align-items-center'>\n")
        f.write("        <div class='col-md-8'>\n")
        f.write("          <h5 class='m-0'>Search Properties</h5>\n")
        f.write("        </div>\n")
        f.write("        <div class='col-md-4'>\n")
        f.write("          <input type='text' id='propertySearch' class='form-control search-input' placeholder='Search site domain...'>\n")
        f.write("        </div>\n")
        f.write("      </div>\n")
        f.write("    </div>\n")
        
        # Detailed Tables
        for site, items in sorted(grouped_caches.items()):
            site_slug = site.replace(":", "-").replace("/", "").replace(".", "-")
            f.write(f"    <div class='card property-card' data-property='{site.lower()}'>\n")
            f.write(f"      <div class='card-header d-flex justify-content-between align-items-center'>\n")
            f.write(f"        <h4 class='m-0'>{site}</h4>\n")
            f.write(f"        <span class='badge bg-danger'>{len(items)} matching invalid entries</span>\n")
            f.write("      </div>\n")
            f.write("      <div class='card-body p-0'>\n")
            f.write("        <table class='table table-striped table-hover mb-0'>\n")
            f.write("          <thead>\n")
            f.write("            <tr>\n")
            f.write("              <th>Cache File</th>\n")
            f.write("              <th>Reason / Interval</th>\n")
            f.write("              <th>Warming Command</th>\n")
            f.write("            </tr>\n")
            f.write("          </thead>\n")
            f.write("          <tbody>\n")
            
            for item in items:
                json_file = item["json_file"]
                reason = item["reason"]
                
                # Determine month to warm
                start_date_str = item.get("start_date")
                month_str = None
                if start_date_str:
                    try:
                        dt = datetime.strptime(start_date_str, "%Y-%m-%d")
                        month_str = dt.strftime("%Y-%m")
                    except Exception:
                        pass
                
                if month_str:
                    cmd = f"python utilities/cache_warmer.py --month {month_str} {site}"
                else:
                    cmd = f"python utilities/cache_warmer.py {site}"
                    
                cmd_id = f"cmd-{site_slug}-{json_file.stem}"
                
                f.write("            <tr>\n")
                f.write(f"              <td><code>{json_file.name}</code></td>\n")
                f.write(f"              <td><span class='text-danger'>{reason}</span></td>\n")
                f.write("              <td>\n")
                f.write(f"                <div class='d-flex align-items-center gap-1'>\n")
                f.write(f"                  <code>{cmd}</code>\n")
                f.write(f"                  <button class='btn btn-copy' id='{cmd_id}' onclick=\"copyCommand('{cmd}', '{cmd_id}')\">Copy</button>\n")
                f.write(f"                </div>\n")
                f.write("              </td>\n")
                f.write("            </tr>\n")
                
            f.write("          </tbody>\n")
            f.write("        </table>\n")
            f.write("      </div>\n")
            f.write("    </div>\n")
            
        f.write("  </div>\n")
        
        # JS Scripts
        f.write("  <script>\n")
        f.write("    function copyCommand(text, btnId) {\n")
        f.write("      navigator.clipboard.writeText(text).then(function() {\n")
        f.write("        var btn = document.getElementById(btnId);\n")
        f.write("        var originalText = btn.innerHTML;\n")
        f.write("        btn.innerHTML = '✓ Copied!';\n")
        f.write("        if (btnId.includes('btn-warning') || btnId.includes('delete')) {\n")
        f.write("          btn.classList.remove('btn-warning');\n")
        f.write("        } else {\n")
        f.write("          btn.classList.remove('btn-copy');\n")
        f.write("        }\n")
        f.write("        btn.classList.add('btn-success');\n")
        f.write("        setTimeout(function() {\n")
        f.write("          btn.innerHTML = originalText;\n")
        f.write("          btn.classList.remove('btn-success');\n")
        f.write("          if (btnId.includes('btn-warning') || btnId.includes('delete')) {\n")
        f.write("            btn.classList.add('btn-warning');\n")
        f.write("          } else {\n")
        f.write("            btn.classList.add('btn-copy');\n")
        f.write("          }\n")
        f.write("        }, 1500);\n")
        f.write("      });\n")
        f.write("    }\n\n")
        
        f.write("    document.getElementById('propertySearch').addEventListener('input', function(e) {\n")
        f.write("      var query = e.target.value.toLowerCase();\n")
        f.write("      var cards = document.querySelectorAll('.property-card');\n")
        f.write("      cards.forEach(function(card) {\n")
        f.write("        var title = card.getAttribute('data-property');\n")
        f.write("        card.style.display = title.includes(query) ? 'block' : 'none';\n")
        f.write("      });\n")
        f.write("    });\n")
        f.write("  </script>\n")
        f.write("</body>\n</html>\n")
        
    print(f"HTML report successfully saved to: {html_path}")

def clean_caches(delete_files=False, verbose=False, max_days=None):
    """
    Scans the cache directory, finding and optionally deleting partial/corrupted cache entries.
    """
    if not CACHE_DIR.exists():
        print(f"Error: Cache directory '{CACHE_DIR}' does not exist.")
        return

    print(f"Scanning cache directory: {CACHE_DIR.resolve()}\n")

    total_scanned = 0
    bad_caches = []
    
    # Iterate through all JSON files in the cache directory
    for json_file in CACHE_DIR.glob("**/*.json"):
        total_scanned += 1
        is_bad = False
        reason = ""
        metadata = {}
        duration_days = None
        
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
        except Exception as e:
            is_bad = True
            reason = f"Corrupted JSON file ({e})"
            
        if not is_bad:
            start_date_str = metadata.get("start_date")
            end_date_str = metadata.get("end_date")
            site_url = metadata.get("site_url", "Unknown Property")
            
            if not start_date_str or not end_date_str:
                is_bad = True
                reason = "Missing start_date or end_date in metadata"
            elif not is_full_month(start_date_str, end_date_str):
                is_bad = True
                reason = f"Partial month ({start_date_str} to {end_date_str})"
                try:
                    start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
                    end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
                    duration_days = (end_date - start_date).days + 1
                except Exception:
                    duration_days = None
                
        if is_bad:
            # Apply duration filter if max_days is specified
            if max_days is not None:
                if duration_days is None or duration_days > max_days:
                    continue
                    
            csv_file = json_file.with_suffix(".csv")
            bad_caches.append({
                "json_file": json_file,
                "csv_file": csv_file,
                "reason": reason,
                "site": site_url if isinstance(metadata, dict) and metadata.get("site_url") else "Unknown",
                "start_date": metadata.get("start_date") if isinstance(metadata, dict) else None,
                "end_date": metadata.get("end_date") if isinstance(metadata, dict) else None
            })
            
            if verbose:
                print(f"Found bad cache: {json_file.name}")
                print(f"  Property: {metadata.get('site_url', 'Unknown')}")
                print(f"  Reason: {reason}\n")

    if not bad_caches:
        print(f"Scan complete. Scanned {total_scanned} cache files. No matching invalid caches found.")
        return

    print(f"Scan complete. Scanned {total_scanned} cache files.")
    print(f"Found {len(bad_caches)} matching partial or corrupted cache files.\n")

    if not delete_files:
        print("="*60)
        print("DRY-RUN MODE: No files have been deleted.")
        print("To delete these files, run this script with the --delete flag.")
        print("="*60 + "\n")
        
        # Show breakdown of bad caches
        for item in bad_caches[:20]:
            print(f"- {item['json_file'].relative_to(CACHE_DIR.parent)} ({item['site']})")
            print(f"  Reason: {item['reason']}")
            
        if len(bad_caches) > 20:
            print(f"... and {len(bad_caches) - 20} more files.")
    else:
        print("="*60)
        print("DELETING BAD CACHES...")
        print("="*60 + "\n")
        
        deleted_count = 0
        for item in bad_caches:
            # Delete JSON file
            try:
                if item["json_file"].exists():
                    os.remove(item["json_file"])
                    deleted_count += 1
            except Exception as e:
                print(f"Error deleting JSON file '{item['json_file']}': {e}")
                
            # Delete corresponding CSV file
            try:
                if item["csv_file"].exists():
                    os.remove(item["csv_file"])
                    deleted_count += 1
            except Exception as e:
                print(f"Error deleting CSV file '{item['csv_file']}': {e}")
                
        print(f"Successfully deleted {deleted_count} files ({len(bad_caches)} cache entries).")

    # Always generate and save the HTML report
    generate_html_report(bad_caches, total_scanned, delete_files, max_days)

def main():
    parser = argparse.ArgumentParser(
        description="Clean partial or corrupted Google Search Console cache files."
    )
    parser.add_argument(
        "--delete",
        action="store_true",
        help="Delete the partial or corrupted cache files (defaults to dry-run)."
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print detailed information for each invalid cache file."
    )
    parser.add_argument(
        "--max-days",
        type=int,
        help="Only target partial caches spanning this number of days or fewer (e.g. 7)."
    )
    
    args = parser.parse_args()
    clean_caches(delete_files=args.delete, verbose=args.verbose, max_days=args.max_days)

if __name__ == "__main__":
    main()
