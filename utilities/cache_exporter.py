"""
Utility script to export and import cached GSC API responses between machines.
Supports compressing cache files into tar.gz or zip archives, filtering by property or dates.
"""
import os
import sys
import json
import tarfile
import zipfile
import argparse
from pathlib import Path
from datetime import datetime, date

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.naming import get_property_name

CACHE_DIR = Path("cache")

def parse_date(date_str):
    """Parses a YYYY-MM-DD date string into a datetime.date object."""
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        raise argparse.ArgumentTypeError(f"Invalid date format: '{date_str}'. Use YYYY-MM-DD.")

def is_safe_path(base_dir, path):
    """Checks if the path is safely inside base_dir to prevent directory traversal vulnerability."""
    base_dir = Path(base_dir).resolve()
    path = Path(path).resolve()
    return base_dir in path.parents or path == base_dir

def get_file_list(property_filter=None, start_date=None, end_date=None):
    """
    Scans the cache directory and returns a list of file paths to export.
    Applies filters based on property names and date ranges.
    """
    if not CACHE_DIR.exists():
        print(f"Error: Cache directory '{CACHE_DIR}' does not exist.", file=sys.stderr)
        return []

    # If no filters are provided, return all files in the cache directory
    if not property_filter and not start_date and not end_date:
        return list(CACHE_DIR.glob("**/*"))

    matched_files = []
    
    # We search for metadata files first to filter, then find corresponding data files
    for json_file in CACHE_DIR.glob("**/*.json"):
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
        except Exception as e:
            print(f"Warning: Could not read metadata file '{json_file}': {e}", file=sys.stderr)
            continue

        # 1. Filter by Property
        if property_filter:
            site_url = metadata.get("site_url", "")
            prop_name = get_property_name(site_url)
            # Support simple case-insensitive substring matching
            if property_filter.lower() not in prop_name.lower():
                continue

        # 2. Filter by Date Range
        if start_date or end_date:
            item_start_str = metadata.get("start_date")
            item_end_str = metadata.get("end_date")
            
            if not item_start_str or not item_end_str:
                continue
                
            try:
                item_start = datetime.strptime(item_start_str, "%Y-%m-%d").date()
                item_end = datetime.strptime(item_end_str, "%Y-%m-%d").date()
            except ValueError:
                continue

            # Check overlap: item_start <= end_date and item_end >= start_date
            if start_date and item_end < start_date:
                continue
            if end_date and item_start > end_date:
                continue

        # If it passed all filters, add the JSON and corresponding CSV
        matched_files.append(json_file)
        csv_file = json_file.with_suffix(".csv")
        if csv_file.exists():
            matched_files.append(csv_file)
        else:
            print(f"Warning: CSV file '{csv_file}' not found for metadata '{json_file}'", file=sys.stderr)

    return matched_files

def create_tarball(archive_path, files, project_root):
    """Creates a gzipped tarball from a list of files."""
    with tarfile.open(archive_path, "w:gz") as tar:
        for file_path in files:
            if file_path.is_file():
                arcname = file_path.resolve().relative_to(project_root)
                tar.add(file_path, arcname=str(arcname))

def create_zip(archive_path, files, project_root):
    """Creates a zip file from a list of files."""
    with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED) as zipf:
        for file_path in files:
            if file_path.is_file():
                arcname = file_path.resolve().relative_to(project_root)
                zipf.write(file_path, arcname=str(arcname))

def extract_tarball(archive_path, project_root, overwrite=False):
    """Extracts a gzipped tarball to the project root."""
    files_imported = 0
    files_skipped = 0
    
    with tarfile.open(archive_path, "r:gz") as tar:
        for member in tar.getmembers():
            target_path = (project_root / member.name).resolve()
            if not is_safe_path(project_root, target_path):
                print(f"Warning: Skipping unsafe member path in archive: '{member.name}'", file=sys.stderr)
                continue
            
            # Only extract files destined for the cache directory
            if not target_path.is_relative_to(project_root / CACHE_DIR):
                continue
                
            if member.isfile():
                if target_path.exists() and not overwrite:
                    files_skipped += 1
                    continue
                
                # Ensure directory exists
                target_path.parent.mkdir(parents=True, exist_ok=True)
                
                f_in = tar.extractfile(member)
                if f_in:
                    with open(target_path, "wb") as f_out:
                        f_out.write(f_in.read())
                    files_imported += 1
                    
    return files_imported, files_skipped

def extract_zip(archive_path, project_root, overwrite=False):
    """Extracts a zip archive to the project root."""
    files_imported = 0
    files_skipped = 0
    
    with zipfile.ZipFile(archive_path, "r") as zipf:
        for member in zipf.namelist():
            target_path = (project_root / member).resolve()
            if not is_safe_path(project_root, target_path):
                print(f"Warning: Skipping unsafe member path in archive: '{member}'", file=sys.stderr)
                continue
                
            if not target_path.is_relative_to(project_root / CACHE_DIR):
                continue
                
            # Zip entries ending with '/' represent directories
            if not member.endswith('/'):
                if target_path.exists() and not overwrite:
                    files_skipped += 1
                    continue
                    
                target_path.parent.mkdir(parents=True, exist_ok=True)
                with open(target_path, "wb") as f_out:
                    f_out.write(zipf.read(member))
                files_imported += 1
                
    return files_imported, files_skipped

def main():
    parser = argparse.ArgumentParser(
        description="Export and import cached GSC API responses between machines."
    )
    subparsers = parser.add_subparsers(dest="command", required=True, help="Subcommand to run")
    
    # Export subcommand parser
    export_parser = subparsers.add_parser("export", help="Export cache files to an archive")
    export_parser.add_argument(
        "-p", "--property",
        help="Filter exports by property name substring (case-insensitive)"
    )
    export_parser.add_argument(
        "--start-date",
        type=parse_date,
        help="Only export cache files containing data on or after this date (YYYY-MM-DD)"
    )
    export_parser.add_argument(
        "--end-date",
        type=parse_date,
        help="Only export cache files containing data on or before this date (YYYY-MM-DD)"
    )
    export_parser.add_argument(
        "-o", "--output",
        help="Path to save the output archive (e.g. export.tar.gz or export.zip). Defaults to a dated tarball."
    )
    export_parser.add_argument(
        "-f", "--force",
        action="store_true",
        help="Overwrite the output archive file if it already exists"
    )
    
    # Import subcommand parser
    import_parser = subparsers.add_parser("import", help="Import cache files from an archive")
    import_parser.add_argument(
        "archive",
        nargs="?",
        help="Path to the archive file to import (.tar.gz, .tgz, or .zip)"
    )
    import_parser.add_argument(
        "-a", "--archive",
        dest="archive_opt",
        metavar="ARCHIVE",
        help="Path to the archive file to import (.tar.gz, .tgz, or .zip)"
    )
    import_parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing cached files in the cache directory"
    )
    
    args = parser.parse_args()
    
    project_root = Path(__file__).resolve().parent.parent
    
    if args.command == "export":
        files_to_export = get_file_list(args.property, args.start_date, args.end_date)
        if not files_to_export:
            print("No cache files matched the specified criteria. Export cancelled.")
            sys.exit(0)
            
        # Filter directories out, only keep files
        files_to_export = [f for f in files_to_export if f.is_file()]
        if not files_to_export:
            print("No files found to export. Export cancelled.")
            sys.exit(0)
            
        # Determine output filename if not provided
        if not args.output:
            today_str = datetime.now().strftime("%Y-%m-%d")
            args.output = str(project_root / f"gsc-cache-export-{today_str}.tar.gz")
            
        output_path = Path(args.output).resolve()
        if output_path.exists() and not args.force:
            print(f"Error: Output file '{output_path}' already exists. Use --force to overwrite.")
            sys.exit(1)
            
        print(f"Exporting {len(files_to_export)} cache files...")
        
        is_zip = output_path.suffix.lower() == ".zip"
        
        try:
            if is_zip:
                create_zip(output_path, files_to_export, project_root)
            else:
                create_tarball(output_path, files_to_export, project_root)
                
            print(f"Successfully exported cache to: {output_path}")
            print(f"File size: {output_path.stat().st_size / 1024:.2f} KB")
        except Exception as e:
            print(f"Error during export: {e}", file=sys.stderr)
            sys.exit(1)
            
    elif args.command == "import":
        archive_file = args.archive_opt or args.archive
        if not archive_file:
            import_parser.error("the following arguments are required: archive or -a/--archive")
            
        archive_path = Path(archive_file).resolve()
        if not archive_path.exists():
            print(f"Error: Archive file '{archive_path}' does not exist.")
            sys.exit(1)
            
        print(f"Importing cache from '{archive_path}'...")
        suffix = archive_path.suffix.lower()
        
        try:
            if archive_path.name.endswith(".tar.gz") or suffix in [".gz", ".tgz", ".tar"]:
                imported, skipped = extract_tarball(archive_path, project_root, args.overwrite)
            elif suffix == ".zip":
                imported, skipped = extract_zip(archive_path, project_root, args.overwrite)
            else:
                print(f"Error: Unsupported archive format. Must be .tar.gz, .tgz, or .zip.")
                sys.exit(1)
                
            print("Import complete:")
            print(f"  - Imported: {imported} files")
            print(f"  - Skipped: {skipped} files (already exist; use --overwrite to replace)")
        except Exception as e:
            print(f"Error during import: {e}", file=sys.stderr)
            sys.exit(1)

if __name__ == "__main__":
    main()
