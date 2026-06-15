import pytest
import os
import pandas as pd
from datetime import datetime
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

def test_query_position_analysis_report(mock_service, mocker):
    mocker.patch('reports.query_position_analysis.fetch_with_cache', return_value=pd.DataFrame(mock_df_data))
    from reports.query_position_analysis import run_report

    site = 'https://www.example.com/'
    run_report(mock_service, site, '2026-05-01', '2026-05-31')

    output_dir = get_output_dir(site)
    slug = get_filename_slug(site)
    assert os.path.exists(os.path.join(output_dir, f"query-position-analysis-{slug}-2026-05-01-to-2026-05-31.csv"))
    assert os.path.exists(os.path.join(output_dir, f"query-position-analysis-{slug}-2026-05-01-to-2026-05-31.html"))

def test_url_inspection_report(mock_service, mocker):
    # Mock the response from urlInspection().index().inspect().execute()
    mock_response = {
        'inspectionResult': {
            'indexStatusResult': {
                'verdict': 'NEUTRAL',
                'indexingState': 'INDEXED',
                'pageFetchState': 'SUCCESSFUL'
            }
        }
    }
    mock_service.urlInspection().index().inspect().execute.return_value = mock_response
    
    from reports.url_inspection_report import run_report
    
    site = 'https://www.example.com/'
    url_to_inspect = 'https://www.example.com/test-page'
    
    run_report(mock_service, site, urls=[url_to_inspect])
    
    output_dir = get_output_dir(site)
    # The filename in url_inspection_report.py uses the current date
    current_date_str = datetime.now().strftime("%Y-%m-%d")
    slug = get_filename_slug(site)
    
    csv_path = os.path.join(output_dir, f"url-inspection-{slug}-{current_date_str}.csv")
    html_path = os.path.join(output_dir, f"url-inspection-{slug}-{current_date_str}.html")
    
    assert os.path.exists(csv_path)
    assert os.path.exists(html_path)
    
    # Check CSV content
    df = pd.read_csv(csv_path)
    assert len(df) == 1
    assert df.iloc[0]['URL'] == url_to_inspect
    assert df.iloc[0]['Verdict'] == 'NEUTRAL'

def test_url_inspection_report_smart_detection(mock_service, mocker):
    # Mock available properties
    mocker.patch('reports.url_inspection_report.get_available_properties', 
                 return_value=['https://www.example.com/', 'sc-domain:example.com'])
    
    # Mock the API response
    mock_response = {
        'inspectionResult': {
            'indexStatusResult': {'verdict': 'GOOD'}
        }
    }
    mock_service.urlInspection().index().inspect().execute.return_value = mock_response
    
    from reports.url_inspection_report import run_report
    
    # Test Scenario: User provides ONLY the page URL
    inspect_url = 'https://www.example.com/subpage'
    # In the real script, this would be handled by the __main__ block logic, 
    # but we can test find_best_property directly or simulate the call.
    from reports.url_inspection_report import find_best_property
    best_prop = find_best_property(inspect_url, ['https://www.example.com/', 'sc-domain:example.com'])
    assert best_prop == 'https://www.example.com/'
    
    run_report(mock_service, best_prop, urls=[inspect_url])
    
    output_dir = get_output_dir(best_prop)
    slug = get_filename_slug(best_prop)
    assert 'www.example.com' in output_dir
    assert os.path.exists(os.path.join(output_dir, f"url-inspection-{slug}-{datetime.now().strftime('%Y-%m-%d')}.html"))
