"""
Runs a specified analysis script for a list of Google Search Console properties.

This script provides a flexible way to execute other analysis scripts from this
repository for a defined group of sites, either provided as command-line arguments
or from a file.

Usage:
    # Run for a few sites listed directly
    python run_for_sites.py query-position-analysis.py https://www.example.com https://www.example.co.uk

    # Run for a list of sites from a file
    python run_for_sites.py gsc-pages-queries.py --sites-file my_sites.txt

    # Pass additional arguments to the target script
    python run_for_sites.py snapshot-report.py --sites-file my_sites.txt --last-7-days
"""

import os
import sys
import subprocess
import argparse

def main():
    """
    Parses arguments and runs the specified script for each site.
    """
    parser = argparse.ArgumentParser(
        description='Run a specified analysis script for a list of GSC properties.',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument('script_to_run', help='The Python script to execute (e.g., query-position-analysis.py).')
    
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('sites', nargs='*', default=[], help='A list of site URLs to process.')
    group.add_argument('--sites-file', help='Path to a text file containing a list of site URLs, one per line.')
    
    # Capture any unknown arguments to pass them to the target script
    args, other_args = parser.parse_known_args()

    script_to_run = args.script_to_run
    if not os.path.exists(script_to_run):
        print(f"Error: The script '{script_to_run}' was not found in the current directory.")
        return

    sites_to_process = []
    if args.sites_file:
        try:
            with open(args.sites_file, 'r') as f:
                sites_to_process = [line.strip() for line in f if line.strip() and not line.strip().startswith('#')]
            print(f"Loaded {len(sites_to_process)} sites from {args.sites_file}.")
        except FileNotFoundError:
            print(f"Error: The sites file '{args.sites_file}' was not found.")
            return
    else:
        sites_to_process = args.sites

    if not sites_to_process:
        print("No sites provided to process. Please provide site URLs directly or via a --sites-file.")
        return

    print(f"\nFound {len(sites_to_process)} properties to process with '{script_to_run}'.")
    
    for site in sites_to_process:
        print(f"\n{'='*20} Running for: {site} {'='*20}")
        
        # Construct the command for the subprocess
        command = ['py', script_to_run, site] + other_args
        
        print(f"Executing command: {' '.join(command)}")
        
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
                print("--- Output ---")
                print(process.stdout)
            if process.stderr:
                print("--- Errors ---")
                print(process.stderr)

            if process.returncode == 0:
                print(f"\n----- Successfully completed for {site} -----")
            else:
                print(f"\n----- Script finished with a non-zero exit code ({process.returncode}) for {site} -----")

        except FileNotFoundError:
            print(f"\nError: 'py' command not found. Is Python installed and configured in your system's PATH?")
            print("You might need to use 'python' instead of 'py'.")
            break # Stop processing if Python command fails
        except Exception as e:
            print(f"\nAn unexpected error occurred while running the script for {site}: {e}")

if __name__ == '__main__':
    main()
