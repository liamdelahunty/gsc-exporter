"""
Generates placeholder markdown documentation files for all report types in the reports/ directory.
Saves them under resources/reports/ using lowercase, hyphenated filenames.
"""
import os

def to_title_case(name):
    # Convert "consolidated_traffic_report" to "Consolidated Traffic Report"
    return " ".join(word.capitalize() for word in name.split("_"))

def main():
    reports_dir = "reports"
    docs_dir = os.path.join("resources", "reports")
    os.makedirs(docs_dir, exist_ok=True)

    if not os.path.exists(reports_dir):
        print(f"Error: {reports_dir} directory not found.")
        return

    # Find all Python files in reports/ (except __init__.py)
    files = [f for f in os.listdir(reports_dir) if f.endswith(".py") and f != "__init__.py"]
    
    generated_count = 0
    for filename in sorted(files):
        base_name = filename[:-3] # Remove '.py'
        doc_filename = base_name.replace("_", "-") + ".md"
        doc_filepath = os.path.join(docs_dir, doc_filename)
        
        report_title = to_title_case(base_name)
        
        content = f"""# {report_title}

This is a placeholder documentation page for the **{report_title}**.

---

## Overview
Detailed description of the report's purpose and contents will go here.

## Standard Arguments Supported
* `--start-date YYYY-MM-DD`
* `--end-date YYYY-MM-DD`
* `--last-month` (Anchor for historical reports)

## Key Metrics Included
* **Clicks**: Total organic search traffic.
* **Impressions**: Visibility count in search engine results.
* **CTR (Click-Through Rate)**: Ratio of clicks to impressions.
* **Position**: Average ranking position in search results.
"""
        
        # Write only if it doesn't already exist to avoid overwriting user documentation
        if not os.path.exists(doc_filepath):
            with open(doc_filepath, "w", encoding="utf-8") as f:
                f.write(content)
            generated_count += 1

    print(f"Generated {generated_count} placeholder documentation files in {docs_dir}.")

if __name__ == "__main__":
    main()
