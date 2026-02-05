"""
Runs all primary Google Search Console analysis scripts for a single specified domain.

This composite script automates the generation of a full suite of reports
for a given site URL, passing through any additional command-line arguments
to the individual analysis scripts.

Usage:
    python run_all_reports_for_site.py <site_url> [additional_arguments_for_scripts]

Example:
    python run_all_reports_for_site.py https://www.example.com --last-month
    python run_all_reports_for_site.py sc-domain:example.com
"""

import os
import sys
import subprocess
import argparse

def main():
    """
    Parses arguments and runs all analysis scripts for the specified site.
    """
    parser = argparse.ArgumentParser(
        description='Run all GSC analysis scripts for a single specified domain.',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument('site_url', help='The URL of the site to run all reports for.')
    
    # Capture any unknown arguments to pass them to the target scripts
    args, other_args = parser.parse_known_args()

    site_url = args.site_url

    # List of primary analysis scripts to run.
    # generate_gsc_wrapped.py amd monthly-summary-report.py not included.
    analysis_scripts = [
        "gsc-pages-queries.py",
        "gsc_pages_exporter.py",
        "key-performance-metrics.py",
        "page-level-report.py", 
        "page-performance-over-time.py",
        "performance-analysis.py",
        "queries-pages-analysis.py",
        "query-position-analysis.py",
        "query-segmentation-report.py",
        "snapshot-report.py",
    ]

    print(f"\n--- Running all reports for site: {site_url} ---")
    
    for script in analysis_scripts:
        if not os.path.exists(script):
            print(f"Warning: Script '{script}' not found. Skipping.")
            continue

        print(f"\n{'='*10} Executing {script} for {site_url} {'='*10}")
        
        # Construct the command for the subprocess
        command = ['py', script, site_url] + other_args
        
        print(f"Command: {' '.join(command)}")
        
        try:
            # Use subprocess.run and capture output
            process = subprocess.run(
                command, 
                capture_output=True, 
                text=True, 
                check=False # Do not raise exception on non-zero exit codes
            )
            
            # Print stdout and stderr from the child process
            if process.stdout:
                print("--- Output from child script ---")
                print(process.stdout)
            if process.stderr:
                print("--- Errors from child script ---")
                print(process.stderr)

            if process.returncode == 0:
                print(f"--- Successfully completed {script} for {site_url} ---")
            else:
                print(f"--- {script} finished with a non-zero exit code ({process.returncode}) for {site_url} ---")

        except FileNotFoundError:
            print(f"Error: 'py' command not found. Is Python installed and configured in your system's PATH?")
            print(f"Skipping further scripts. You might need to use 'python' instead of 'py'.")
            break # Stop processing if Python command fails
        except Exception as e:
            print(f"An unexpected error occurred while running {script} for {site_url}: {e}")
            
    print(f"\n--- All reports finished for site: {site_url} ---")

if __name__ == '__main__':
    main()
