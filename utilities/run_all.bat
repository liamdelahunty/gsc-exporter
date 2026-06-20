@echo off
SETLOCAL

REM Check if a site URL is provided
IF [%1]==[] (
    ECHO Usage: %0 ^<site_url^>
    GOTO :EOF
)

SET SITE_URL=%1

ECHO Running gsc_pages_exporter.py for %SITE_URL%...
python gsc_pages_exporter.py %SITE_URL%

ECHO Running gsc-pages-queries.py for %SITE_URL%...
python gsc-pages-queries.py %SITE_URL%

ECHO Running performance-analysis.py for %SITE_URL%...
python performance-analysis.py %SITE_URL%

ECHO Running snapshot-report.py for %SITE_URL%...
python snapshot-report.py %SITE_URL%

ECHO Running key-performance-metrics.py for %SITE_URL%...
python key-performance-metrics.py %SITE_URL%

ECHO Running queries-pages-analysis.py for %SITE_URL%...
python queries-pages-analysis.py %SITE_URL%

ECHO Running query-position-analysis.py for %SITE_URL%...
python query-position-analysis.py %SITE_URL%

ECHO All scripts finished for %SITE_URL%.

ECHO Generating index.html for %SITE_URL%...
python generate_index.py %SITE_URL%

ECHO Done.
