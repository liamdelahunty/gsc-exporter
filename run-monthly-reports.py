"""
Runs a suite of Google Search Console reports for the last calendar month for multiple sites.

This script automates the generation of various GSC reports for a group of sites 
defined in a text file. It defaults to a comprehensive set of monthly useful 
reports, but can also take a custom list of reports from a file.

Usage:
    python run-monthly-reports.py --sites-file <path_to_sites.txt> [--reports-file <path_to_reports.txt>]

Example:
    python run-monthly-reports.py --sites-file site-lists/sites.txt
"""

import os
import sys
import subprocess
import argparse

# Scripts to exclude from automated runs (usually require manual input or specific URLs)
EXCLUDE_FROM_AUTO = [
    "reports/page_performance_single_page.py",
    "reports/url_inspection_report.py",
    "reports/migrations/drupal_dato_migration_analysis.py",
    "reports/migrations/drupal_dato_gsc_comparison_report.py",
    "reports/migrations/dato_pages_performance_report.py",
    "reports/migrations/generate_migration_index.py",
    "reports/generate_gsc_wrapped.py",
    "reports/migrations/library_marketing_migration_prioritisation_report.py",
    "reports/migrations/library_marketing_migration_analysis.py",
    "reports/migrations/library_quick_links_performance_report.py",
    "reports/migrations/generate_library_migration_index.py",
    "reports/__init__.py"
]

def get_default_reports():
    """Dynamically finds all reports in the reports/ directory."""
    reports_dir = 'reports'
    if not os.path.isdir(reports_dir):
        return []
    
    all_scripts = [os.path.join(reports_dir, f) for f in os.listdir(reports_dir) if f.endswith('.py')]
    return sorted([s for s in all_scripts if s not in EXCLUDE_FROM_AUTO])

def main():
    parser = argparse.ArgumentParser(
        description='Run GSC reports for the last calendar month for multiple sites.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Example Usage:
  python run-monthly-reports.py --sites-file site-lists/sites.txt
  python run-monthly-reports.py --sites-file site-lists/sites.txt --reports-file reports.txt
"""
    )
    parser.add_argument('--sites-file', required=True, help='Path to a text file containing site URLs (one per line).')
    parser.add_argument('--reports-file', help='Optional path to a text file containing report script names to run.')
    parser.add_argument('--dry-run', action='store_true', help='Print the commands without executing them.')
    
    # Capture any unknown arguments to pass them to the target scripts
    args, other_args = parser.parse_known_args()
    
    # 1. Load sites
    if not os.path.exists(args.sites_file):
        print(f"Error: Sites file '{args.sites_file}' not found.")
        return
    
    try:
        with open(args.sites_file, 'r') as f:
            sites = [line.strip() for line in f if line.strip() and not line.strip().startswith('#')]
    except Exception as e:
        print(f"Error reading sites file: {e}")
        return
    
    if not sites:
        print(f"Error: No sites found in '{args.sites_file}'.")
        return

    # 2. Load reports
    if args.reports_file:
        if not os.path.exists(args.reports_file):
            print(f"Error: Reports file '{args.reports_file}' not found.")
            return
        try:
            with open(args.reports_file, 'r') as f:
                reports_to_run = [line.strip() for line in f if line.strip() and not line.strip().startswith('#')]
        except Exception as e:
            print(f"Error reading reports file: {e}")
            return
    else:
        reports_to_run = get_default_reports()
    
    if not reports_to_run:
        print("Error: No reports to run.")
        return

    print(f"\n{'='*50}")
    print(f"Starting Monthly Reports Run")
    print(f"Sites: {len(sites)}")
    print(f"Reports: {len(reports_to_run)}")
    print(f"{'='*50}\n")

    for site in sites:
        print(f"\n{'#'*60}")
        print(f"### SITE: {site}")
        print(f"{'#'*60}")
        
        for report in reports_to_run:
            if not os.path.exists(report):
                print(f"\n[!] Warning: Script '{report}' not found. Skipping.")
                continue
            
            print(f"\n>>> Executing {report} for {site}...")
            
            # Use sys.executable to ensure we use the same Python environment
            # Set PYTHONPATH to the current directory so that 'core' can be found
            env = os.environ.copy()
            env["PYTHONPATH"] = os.getcwd()
            
            command = [sys.executable, report, site]
            
            # Since all reports are now standardised, we default to --last-month
            # if no other date-related flag was provided by the user.
            date_flags = ['--last-month', '--start-date', '--end-date', '--lookback-months']
            
            # Check if any date-related flag is already in other_args
            has_date_flag = any(flag in other_args for flag in date_flags)
            
            if not has_date_flag:
                command.append('--last-month')
            
            # Add any other flags provided by the user
            command.extend(other_args)
            
            print(f"Command: {' '.join(command)}")
            
            if args.dry_run:
                print("--- DRY RUN: Skipping execution ---")
                continue
            
            try:
                # Use subprocess.run to execute the script
                # We don't use capture_output=True so the user can see progress in real-time
                process = subprocess.run(command, env=env)
                
                if process.returncode == 0:
                    print(f"--- SUCCESS: {report} completed for {site}")
                else:
                    print(f"--- FAILURE: {report} exited with code {process.returncode} for {site}")
            except Exception as e:
                print(f"--- ERROR: An unexpected error occurred while running {report}: {e}")

    print(f"\n{'='*50}")
    print(f"Monthly Reports Run Completed")
    print(f"{'='*50}\n")

if __name__ == '__main__':
    main()
