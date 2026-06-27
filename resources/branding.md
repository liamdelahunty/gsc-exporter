# GSC Exporter - Simplified Branding Documentation

This document explains the unified branding implementation for generated HTML reports in the GSC Exporter tool. 

---

## Architectural Overview

Rather than supporting multiple layout injection modes, the branding system prepends a single, consistent branding navigation bar / menu at the absolute top of the generated HTML documents (directly inside the `<body>` element).

### Configuration Files
The branding system uses two configuration files:
1. **Default Configuration**: [branding.default.json](file:///home/liamvictor/projects/gsc-exporter/config/branding.default.json)
   * This is tracked in the repository and serves as a default/example template for users.
2. **Bespoke Configuration**: `config/branding.json`
   * This is used for your local environment's bespoke branding setup.
   * This file is ignored by Git in [.gitignore](file:///home/liamvictor/projects/gsc-exporter/.gitignore) so that local brand configurations are never accidentally committed to the repository.

At runtime, [branding.py](file:///home/liamvictor/projects/gsc-exporter/core/branding.py) attempts to load `config/branding.json` first. If it does not exist, it falls back to `config/branding.default.json`.

---

## Configuration Schema

Here is the schema for both the default and bespoke branding configurations:

```json
{
  "enabled": true,
  "theme": {
    "primary_colour": "#2c3e50",
    "text_colour": "#ffffff",
    "font_family": "'Outfit', 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif"
  },
  "logo_url": "https://raw.githubusercontent.com/google/material-design-icons/master/png/action/analytics/materialicons/24dp/2x/baseline_analytics_black_24dp.png",
  "link_url": "https://github.com/liamdelahunty/gsc-exporter",
  "text": "My Custom GSC Exporter",
  "links": [
    {
      "text": "Documentation",
      "url": "https://github.com/liamdelahunty/gsc-exporter/blob/main/README.md"
    },
    {
      "text": "Repository",
      "url": "https://github.com/liamdelahunty/gsc-exporter"
    }
  ]
}
```

* **`enabled`** *(boolean)*: Toggles branding injection on or off.
* **`theme`** *(object)*: Defines primary colours, text colours, and fonts for the top bar.
* **`logo_url`** *(string)*: Optional URL to a logo displayed inside the top bar.
* **`link_url`** *(string)*: Hyperlink for the logo and brand name.
* **`text`** *(string)*: The brand title text displayed beside the logo on the left.
* **`links`** *(array of objects)*: List of custom links to render inside the hamburger dropdown menu on the right-hand side of the top bar. Each link object requires a `text` string and `url` string.

---

## Layout Rules

To ensure that the navigation bar sits cleanly above the report content and behaves correctly:
* The branding bar is prepended at the absolute top of the `<body>`.
* Fixed-top headers (like Bootstrap's `.fixed-top` navbars) are automatically overridden via injected CSS styles to be `position: static !important;`.
* The template's default body spacing (`padding-top`) is set to `0 !important`.
* This ensures that all content flows naturally in block layout without clipping, overlaps, or redundant gaps.
* All custom footer injection and replacement logic has been removed to preserve the standard footer template layouts.
