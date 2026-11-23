"""
Generates highly detailed markdown documentation files for all GSC report types.
Parses script docstrings, CLI arguments, and output filenames to produce comprehensive guides.
"""
import os
import ast
import re

# Custom interpretation templates for key reports to make documentation extremely thorough
CUSTOM_INTERPRETATIONS = {
    "snapshot_report": """## How to Interpret the Snapshot Report

This report provides a multi-dimensional summary of a site's performance for a single period.

### 1. Overall Performance Summary
* **Clicks & Impressions**: Establish the absolute traffic and visibility baseline.
* **Average CTR**: High-level indicator of search snippet relevance and clickability.
* **Average Position**: The weighted average ranking position across all query impressions.

### 2. Top Pages by Clicks & Impressions
* Identify your **Top Traffic Drivers** (high clicks) and **Brand Visibility Leaders** (high impressions).
* A page with high impressions but low clicks indicates a major click-through rate optimization opportunity.

### 3. High Impressions, Low CTR Opportunities
* Lists pages with **>= 1,000 impressions** and **< 1% CTR**.
* **Actionable Insight**: These pages are highly visible in search results but fail to attract clicks. Prioritise them for search snippet optimization (rewriting title tags, improving meta descriptions, and adding structured schema).

### 4. Performance by Device
* **Mobile vs. Desktop vs. Tablet**: Evaluate the mobile-friendliness of your site. If mobile impressions are high but CTR/Position is low, check mobile page speed, rendering, and content presentation.

### 5. Performance by Country
* Analyse geographic traffic distribution. Useful for identifying international expansion opportunities or localising content for top-performing regions.""",

    "period_comparison_report": """## How to Interpret the Period Comparison Report

This report tracks performance changes between a current period and a previous period of equal length.

### 1. Interactive Charts
* Visualise query-level deltas to quickly distinguish broad traffic changes from page-specific fluctuations.

### 2. Query Deltas (Clicks & Impressions)
* **Positive Delta (+)**: Marks search terms that have gained visibility and clicks ("Rising Stars").
* **Negative Delta (-)**: Highlights search terms that have lost traction ("Decaying Keywords").

### 3. Position Deltas
* **Negative Delta (-)**: Represents a positive change (ranking moved closer to position 1).
* **Positive Delta (+)**: Indicates ranking slippage.

### 4. Content Decay & Opportunity Analysis
* Sort by click delta descending to find the biggest winners.
* Sort by click delta ascending to locate decaying pages/queries that require content updates or backlink acquisition.
* Focus on queries with stable or rising impressions but falling clicks—this indicates a drop in snippet relevance or increased competitor ad spend.""",

    "keyword_cannibalisation_report": """## How to Interpret the Keyword Cannibalisation Report

Keyword cannibalisation occurs when multiple pages on your site compete for the same search query.

### 1. Identifying Competitor Pages
* Look for queries where multiple URLs rank with similar average positions.
* If a query lists multiple ranking URLs with split clicks, it indicates search engines are confused about which page is most relevant.

### 2. Assessing the Impact
* **Diluted Authority**: Link equity and click-through rates are split across pages.
* **Rank Fluctuations**: Search engines may constantly alternate which page ranks, causing position instability.

### 3. Actions to Resolve Cannibalisation
* **Canonicalisation**: Set the canonical tag of the weaker page to point to the primary page if they serve the same intent.
* **301 Redirects**: Redirect the redundant page to the primary page and merge their content.
* **De-optimisation**: Remove the target keyword from the metadata and headings of the secondary page.
* **Content Restructuring**: Re-write the pages to target distinct search intents (e.g. informational vs. transactional).""",

    "page_level_report": """## How to Interpret the Page Level Report

A page-centric view of performance focusing on organic traffic distribution and query complexity.

### 1. Unique Query Counts (Query #)
* **Long-Tail Depth**: Pages with a high number of unique queries are successfully capturing long-tail search traffic.
* **Narrow Intent**: Pages with high clicks but a low unique query count typically rank highly for a single, high-volume keyword.

### 2. Traffic Skew
* Typically, 20% of your pages drive 80% of your traffic. Use this report to verify if traffic is diversified or heavily reliant on a single landing page.
* Check pages with high unique queries but low clicks—they may require small content expansions to move long-tail rankings from page 2 to page 1.""",

    "search_appearance_report": """## How to Interpret the Search Appearance Report

Segment your performance metrics by Google Rich Result types (e.g. Review Snippets, FAQs, Videos, AMP, Products).

### 1. Rich Result Efficiency
* Compare CTRs of search appearances against standard web search. Rich results generally exhibit significantly higher CTR.

### 2. Schema Markup Verification
* If you deployed Structured Data (e.g. Product or FAQ Schema) but see zero impressions for that type, your schema may be invalid or not yet indexed by Google.
* Use this report to calculate the direct traffic ROI of your structured data implementation efforts.""",

    "discover_key_performance_metrics": """## How to Interpret the Google Discover Report

Google Discover is a query-less feed based on user interests rather than search intent.

### 1. Volatility and Spikes
* Discover traffic is notoriously spike-heavy and short-lived. Expect rapid impression surges followed by steep declines.

### 2. High CTR Expectations
* Discover CTRs are often much higher than standard organic web CTR (often 5% to 15%+).
* Analyse high-performing Discover topics to identify content themes that resonate with your target audience's interest feed.""",

    "sitemap_generator": """## How to Interpret the Sitemap Generator Report

This tool discovers active URLs based on GSC historical query data and outputs a search-validated XML sitemap.

### 1. Active vs. Orphaned URLs
* Compares URLs in GSC that received impressions/clicks against your internal database.
* Identifies "active" pages that Google is currently crawling and serving.

### 2. Crawl Budget Efficiency
* Sitemap files generated from search-validated URLs ensure Google prioritises crawls on pages that actually generate search visibility, optimizing your crawl budget.
* Exclude low-impression, low-value pages to prevent Google from wasting crawl resources.""",

    "key_performance_metrics": """## How to Interpret the Key Performance Metrics Report

A macro-level dashboard tracking site health and organic visibility over monthly (16-month) or weekly intervals.

### 1. Seasonal Trends and Weekly Cadence
* Spot year-over-year (YoY) changes, holiday dips, or quarterly industry trends in monthly mode.
* Track short-term week-on-week fluctuations and recent campaign momentum in weekly mode.

### 2. Search Performance Metrics
* Track absolute clicks and impressions alongside click-through rates (CTR) and average search positions.

### 3. Historical Trajectory
* Assess whether SEO strategies are yielding compound growth or if site-wide visibility is in decline.""",

    "query_position_analysis": """## How to Interpret the Query Position Analysis Report

Tracks how your keywords are distributed across different ranking groups over time.

### 1. Position Buckets
* Monitors the count and trend of keywords ranking in:
  * **Top 3**: Primary traffic drivers.
  * **Positions 4-10**: Page 1 visibility; prime candidates for optimization to push into Top 3.
  * **Positions 11-20**: Page 2 visibility; requires content improvements or link additions to reach page 1.
  * **Positions 21-100**: Long-tail or low-relevance queries.

### 2. Trend Identification
* If Top 3 keywords are declining while Positions 11-20 are increasing, it indicates site-wide ranking deflation or increased competitor activity.""",
}

DEFAULT_INTERPRETATION = """## How to Interpret the Report Metrics

* **Clicks**: Represents the number of times a user clicked your search result to visit your site.
* **Impressions**: The number of times your search result appeared in search results.
* **CTR (Click-Through Rate)**: The percentage of impressions that resulted in a click (`Clicks / Impressions`). A low CTR indicates snippet styling or metadata needs improvement.
* **Average Position**: The average ranking position of your URLs for the queries. A lower position (closer to 1) is better. Monitor position trends to spot algorithm updates or competitor improvements."""


def to_title_case(name):
    return " ".join(word.capitalize() for word in name.split("_"))


def extract_docstring(filepath):
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            tree = ast.parse(f.read(), filename=filepath)
        docstring = ast.get_docstring(tree)
        return docstring or "No overview description available."
    except Exception as e:
        print(f"Error parsing docstring for {filepath}: {e}")
        return "No overview description available."


def parse_arguments_from_file(filepath):
    """
    Statically parses argparse arguments from python code.
    """
    arguments = []
    has_site_url = False
    
    with open(filepath, "r", encoding="utf-8") as f:
        code = f.read()

    # Find parser.add_argument(...) matches
    # This matches positional or optional arguments
    matches = re.finditer(r'add_argument\(\s*[\'"]([^\'"]+)[\'"](.*?)\)', code, re.DOTALL)
    for m in matches:
        arg_name = m.group(1)
        rest = m.group(2)
        
        # Extract help string
        help_match = re.search(r'help\s*=\s*[\'"]([^\'"]+)[\'"]', rest)
        help_str = help_match.group(1) if help_match else "No description available."
        
        # Extract default value
        default_match = re.search(r'default\s*=\s*([^\s,\)]+)', rest)
        default_val = default_match.group(1) if default_match else None
        
        if arg_name in ['--start-date', '--end-date', '--last-7-days', '--last-month', '--branding-config']:
            continue
            
        if arg_name == 'site_url':
            has_site_url = True
            continue # site_url is handled separately as a standard positional arg
            
        arguments.append({
            "name": arg_name,
            "help": help_str,
            "default": default_val
        })
        
    return arguments, has_site_url


def parse_outputs_from_file(filepath, base_name):
    """
    Extracts output files generated by the report script.
    """
    with open(filepath, "r", encoding="utf-8") as f:
        code = f.read()

    outputs = []
    
    # Try to find file_prefix definitions when {file_prefix} is used
    prefix_matches = []
    if '{file_prefix}' in code:
        prefix_matches = re.findall(r'file_prefix\s*=\s*[f]?[\'"]([^\'"]+)[\'"]', code)
        for p in prefix_matches:
            outputs.append(f"`output/<domain>/{p}.csv` (CSV dataset)")
            outputs.append(f"`output/<domain>/{p}.html` (HTML report)")

    # Try to find CSV files
    csv_matches = re.findall(r'[\'"]([^\'"]+\.csv)[\'"]', code)
    for m in csv_matches:
        if '{file_prefix}' in m and prefix_matches:
            continue
        if '{' in m or 'slug' in m or 'start' in m:
            outputs.append(f"`output/<domain>/{m}` (CSV dataset)")
        else:
            outputs.append(f"`output/<domain>/{m.replace('{slug}', base_name)}` (CSV dataset)")
            
    # Try to find HTML files
    html_matches = re.findall(r'[\'"]([^\'"]+\.html)[\'"]', code)
    for m in html_matches:
        if '{file_prefix}' in m and prefix_matches:
            continue
        if m.startswith('templates/'):
            continue # Skip templates
        if '{' in m or 'slug' in m or 'start' in m:
            outputs.append(f"`output/<domain>/{m}` (HTML report)")
        else:
            outputs.append(f"`output/<domain>/{m.replace('{slug}', base_name)}` (HTML report)")

    # Fallback default outputs based on standard GSC Exporter conventions
    if not outputs:
        slug_name = base_name.replace("_", "-")
        outputs.append(f"`output/<domain>/{slug_name}-<domain>-<start_date>-to-<end_date>.csv` (CSV dataset)")
        outputs.append(f"`output/<domain>/{slug_name}-<domain>-<start_date>-to-<end_date>.html` (HTML report)")
        
    # Deduplicate
    unique_outputs = []
    for o in outputs:
        if o not in unique_outputs:
            unique_outputs.append(o)
            
    return unique_outputs


def main():
    reports_dir = "reports"
    docs_dir = os.path.join("resources", "reports")
    os.makedirs(docs_dir, exist_ok=True)

    if not os.path.exists(reports_dir):
        print(f"Error: {reports_dir} directory not found.")
        return

    files = [f for f in os.listdir(reports_dir) if f.endswith(".py") and f != "__init__.py"]
    
    generated_count = 0
    for filename in sorted(files):
        base_name = filename[:-3] # Remove '.py'
        doc_filename = base_name.replace("_", "-") + ".md"
        doc_filepath = os.path.join(docs_dir, doc_filename)
        
        filepath = os.path.join(reports_dir, filename)
        
        report_title = to_title_case(base_name)
        docstring = extract_docstring(filepath)
        arguments, has_site_url = parse_arguments_from_file(filepath)
        outputs = parse_outputs_from_file(filepath, base_name)
        
        # Build arguments markdown
        args_md = ""
        if arguments:
            args_md += "### Optional Arguments\n\n"
            for arg in arguments:
                default_str = f" (default: `{arg['default']}`)" if arg['default'] else ""
                args_md += f"* **`{arg['name']}`**: {arg['help']}{default_str}\n"
        else:
            args_md += "No custom optional arguments defined for this report.\n"

        # Determine interpretation text
        interpretation_text = CUSTOM_INTERPRETATIONS.get(base_name, DEFAULT_INTERPRETATION)

        # Assemble CLI usage example
        site_arg = " <site_url>" if has_site_url else ""
        example_cmd = f"python reports/{filename}{site_arg} --last-month"
        if base_name == "page_performance_single_page":
            example_cmd = f"python reports/{filename} sc-domain:example.com https://example.com/page-url --last-month"
        elif base_name == "key_performance_metrics":
            example_cmd = f"python reports/{filename}{site_arg} --last-month\n```\n\n### Weekly Reporting Example\n```bash\npython reports/{filename}{site_arg} --weekly --weeks 4"

        content = f"""# {report_title}

{docstring}

---

## Command Line Usage

### Standard Example
```bash
{example_cmd}
```

### Argument Reference
* **`site_url`** *(positional)*: The GSC property URL (e.g. `sc-domain:example.com` or `https://example.com/`).
* **`--start-date YYYY-MM-DD`**: Specify a custom start date for the analysis.
* **`--end-date YYYY-MM-DD`**: Specify a custom end date.
* **`--last-month`**: Automatically run the report for the last complete calendar month.
* **`--last-7-days`**: Run for the last 7 full days of available data.

{args_md}

---

## Expected Output Files

This report generates the following files in the output directory:

"""
        for o in outputs:
            content += f"* {o}\n"

        content += f"""
---

{interpretation_text}

---

## Recommendations and Best Practices

1. **Warm the Cache First**: Run `python utilities/cache_warmer.py --file site-lists/sites.txt` to populate GSC data locally before executing batch reports.
2. **Frequency**: Generate this report monthly to identify seasonal trends and monitor organic visibility performance.
3. **Bespoke Branding**: Custom logo, primary colours, and support links can be configured in `config/branding.json`.
"""

        with open(doc_filepath, "w", encoding="utf-8") as f:
            f.write(content)
        generated_count += 1

    print(f"Successfully generated {generated_count} detailed markdown documentation files in {docs_dir}.")


if __name__ == "__main__":
    main()
