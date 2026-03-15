Table headers (`<thead>`) in the HTML reports are generated automatically by the Pandas `to_html()` function. You can adjust their style by adding custom CSS rules to the `<style>` block within the HTML template in each script.

Here is how you can do it for the `key-performance-metrics.py` script. The same logic applies to the other scripts.

### Step 1: Locate the HTML Template

In `key-performance-metrics.py`, find the `create_single_site_html_report` function. Inside it, you will see a multiline f-string that defines the HTML structure.

### Step 2: Add CSS Rules

You can add CSS rules to the `<style>` tag to target the table header. For example, to change the background colour and text colour of the header:

It is recommended to use a descriptive variable name for the report title. In this example, we've updated the function to use `report_title` instead of `site_url` for better readability.

```python
def create_single_site_html_report(df, report_title):
    """Generates a simplified HTML report for a single site."""
    df_no_site = df.drop(columns=['site_url'])
    report_body = df_no_site.to_html(classes="table table-striped table-hover", index=False, border=0)
    return f"""
<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>GSC Performance Report for {report_title}</title><link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
<style>
    body{{padding:2rem;}}
    h1{{border-bottom:2px solid #dee2e6;padding-bottom:.5rem;margin-top:2rem;}}
    footer{{margin-top:3rem;text-align:center;color:#6c757d;}}

    /* --- Add these styles for the table header --- */
    .table thead th {{
        background-color: #434343;
        color: #ffffff;
        text-align: left;
    }}
    /* --- End of added styles --- */

</style></head>
<body><div class="container-fluid"><h1>GSC Performance Report for {report_title}</h1><div class="table-responsive">{report_body}</div></div>
<footer><p><a href="https://github.com/liamdelahunty/gsc-exporter" target="_blank">gsc-exporter</a></p></footer></body></html>"""
```

### Explanation

*   We are targeting `th` elements (table headers) inside a `thead` (table head) within an element that has the class `.table`. This is specific enough to only affect the headers of your data tables.
*   You can replace the `background-color` and `color` values with any standard CSS colour codes.
This change has also been applied to the HTML template strings in:
*   `queries-pages-analysis.py`
*   `query-position-analysis.py`

## Setup