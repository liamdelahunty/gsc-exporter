import pytest
import os
import pandas as pd
from unittest.mock import MagicMock
from core.naming import get_output_dir, get_filename_slug

# Mock data
mock_df_data = {
    'page': ['https://example.com/p1', 'https://example.com/p2'],
    'query': ['keyword1', 'keyword2'],
    'clicks': [10, 20],
    'impressions': [100, 200],
    'ctr': [0.1, 0.1],
    'position': [1.5, 2.5],
    'date': ['2024-01-01', '2024-01-01'],
    'device': ['desktop', 'mobile'],
    'country': ['gbr', 'usa']
}

@pytest.fixture
def mock_service():
    service = MagicMock()
    service.sites().list().execute.return_value = {
        'siteEntry': [{'siteUrl': 'https://www.example.com/'}]
    }
    return service

def test_performance_analysis_report(mock_service, mocker):
    # Patch the function where it is USED
    mocker.patch('reports.performance_analysis.fetch_with_cache', return_value=pd.DataFrame(mock_df_data))
    from reports.performance_analysis import run_report
    
    site = 'https://www.example.com/'
    run_report(mock_service, site, '2024-01-01', '2024-01-31', '2023-01-01', '2023-01-31')
    
    output_dir = get_output_dir(site)
    slug = get_filename_slug(site)
    csv_path = os.path.join(output_dir, f"performance-analysis-{slug}-2024-01-01-to-2024-01-31.csv")
    html_path = os.path.join(output_dir, f"performance-analysis-{slug}-2024-01-01-to-2024-01-31.html")
    
    assert os.path.exists(csv_path)
    assert os.path.exists(html_path)

def test_page_level_report(mock_service, mocker):
    mocker.patch('reports.page_level_report.fetch_with_cache', return_value=pd.DataFrame(mock_df_data))
    from reports.page_level_report import run_report
    
    site = 'https://www.example.com/'
    run_report(mock_service, site, '2024-01-01', '2024-01-31')
    output_dir = get_output_dir(site)
    slug = get_filename_slug(site)
    assert os.path.exists(os.path.join(output_dir, f"page-level-report-{slug}-2024-01-01-to-2024-01-31.html"))

def test_snapshot_report(mock_service, mocker):
    mocker.patch('reports.snapshot_report.fetch_with_cache', return_value=pd.DataFrame(mock_df_data))
    from reports.snapshot_report import run_report
    
    site = 'https://www.example.com/'
    run_report(mock_service, site, '2024-01-01', '2024-01-31')
    output_dir = get_output_dir(site)
    slug = get_filename_slug(site)
    assert os.path.exists(os.path.join(output_dir, f"snapshot-{slug}-2024-01-01-to-2024-01-31-report.html"))

# (Remaining tests can be added/fixed one by one)
