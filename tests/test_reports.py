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

def test_daily_performance_matrix_report(mock_service, mocker):
    mocker.patch('reports.daily_performance_matrix.fetch_with_cache', return_value=pd.DataFrame(mock_df_data))
    from reports.daily_performance_matrix import run_report
    
    site = 'https://www.example.com/'
    run_report(mock_service, site, '2024-01-01', '2024-01-31', top_stories=2)
    output_dir = get_output_dir(site)
    slug = get_filename_slug(site)
    clicks_csv = os.path.join(output_dir, f"daily-performance-matrix-{slug}-discover-2024-01-01-to-2024-01-31-clicks.csv")
    impressions_csv = os.path.join(output_dir, f"daily-performance-matrix-{slug}-discover-2024-01-01-to-2024-01-31-impressions.csv")
    html_path = os.path.join(output_dir, f"daily-performance-matrix-{slug}-discover-2024-01-01-to-2024-01-31.html")
    
    assert os.path.exists(clicks_csv)
    assert os.path.exists(impressions_csv)
    assert os.path.exists(html_path)

def test_head_mid_long_tail_report(mock_service, mocker):
    query_mock_data = {
        'query': [
            'example brand',                      # 2 words (Head, Brand)
            'login',                              # 1 word (Head)
            'how to manage annual leave online',  # 6 words (Long Tail)
            'statutory redundancy pay calculation', # 4 words (Mid Tail)
            'what is statutory sick pay in uk'    # 7 words (Long Tail)
        ],
        'clicks': [120, 60, 15, 3, 0],
        'impressions': [1000, 500, 300, 80, 25],
        'ctr': [0.12, 0.12, 0.05, 0.0375, 0.0],
        'position': [1.2, 1.8, 3.4, 8.5, 12.0]
    }
    site_mock_data = {
        'clicks': [250],
        'impressions': [2500],
        'ctr': [0.10],
        'position': [3.5]
    }

    def side_effect(service, site_url, start_date, end_date, dimensions=None, **kwargs):
        if dimensions == []:
            return pd.DataFrame(site_mock_data)
        return pd.DataFrame(query_mock_data)

    mocker.patch('reports.head_mid_long_tail_report.fetch_with_cache', side_effect=side_effect)
    from reports.head_mid_long_tail_report import run_report
    
    site = 'https://www.example.com/'
    start_date = '2024-01-01'
    end_date = '2024-01-31'
    summary_csv, queries_csv, html_path = run_report(mock_service, site, start_date, end_date)
    
    assert summary_csv is not None and os.path.exists(summary_csv)
    assert queries_csv is not None and os.path.exists(queries_csv)
    assert html_path is not None and os.path.exists(html_path)

    # Check anonymised data inclusion in summary CSV and HTML
    df_summary = pd.read_csv(summary_csv)
    assert 'Property Reconciliation' in df_summary['Category Type'].values
    assert 'Anonymised Queries' in df_summary['Segment'].values

    with open(html_path, 'r', encoding='utf-8') as f:
        html_content = f.read()
    assert 'Google Search Console Privacy Threshold Notice' in html_content
    assert 'Anonymised Queries' in html_content


def test_drupal_dato_top_1000_migration_report(mock_service, mocker):
    migration_mock_data = {
        'page': [
            'https://www.hr-inform.co.uk/',                                # Root homepage to ignore
            'https://www.hr-inform.co.uk/features/working-during-heatwave', # Live Dato page
            'https://www.hr-inform.co.uk/user/login',                      # Utility page to ignore
            'https://www.hr-inform.co.uk/employment-law/statutory-redundancy', # Winner for query
            'https://www.hr-inform.co.uk/news/redundancy-guide',           # Cannibalised for query
            'https://www.hr-inform.co.uk/templates/disciplinary-sample?page=2', # Stripped params & CTR Opp
            'https://www.hr-inform.co.uk/guides/maternity-rights',         # Standard candidate
            'https://www.hr-inform.co.uk/system/files/downloads/2017-09/Template%20payslips.docx' # Download document
        ],
        'query': [
            'hr inform homepage',
            'working during heatwave',
            'login hr inform',
            'statutory redundancy pay',
            'statutory redundancy pay',
            'disciplinary sample template',
            'maternity rights uk',
            'free payslip template docx'
        ],
        'clicks': [150, 50, 5, 200, 20, 3, 40, 25],
        'impressions': [2000, 400, 10, 1500, 150, 900, 500, 300],
        'ctr': [0.075, 0.125, 0.5, 0.133, 0.133, 0.0033, 0.08, 0.083],
        'position': [1.0, 2.1, 1.0, 1.5, 6.2, 5.0, 3.2, 2.2]
    }
    mocker.patch('reports.migrations.drupal_dato_top_1000_migration_report.fetch_with_cache',
                 return_value=pd.DataFrame(migration_mock_data))
    
    from reports.migrations.drupal_dato_top_1000_migration_report import run_report
    site = 'https://www.hr-inform.co.uk'
    candidates_csv, cannibal_csv, dato_csv, downloads_csv, html_path = run_report(
        mock_service, site, '2024-01-01', '2024-12-31', limit=1000
    )

    assert candidates_csv is not None and os.path.exists(candidates_csv)
    assert cannibal_csv is not None and os.path.exists(cannibal_csv)
    assert dato_csv is not None and os.path.exists(dato_csv)
    assert downloads_csv is not None and os.path.exists(downloads_csv)
    assert html_path is not None and os.path.exists(html_path)

    # Verify Candidates CSV
    df_cand = pd.read_csv(candidates_csv)
    assert 'https://www.hr-inform.co.uk/employment-law/statutory-redundancy' in df_cand['Legacy Drupal URL'].values
    # Root page, utility and live Dato pages must not be in candidates
    assert 'https://www.hr-inform.co.uk' not in df_cand['Legacy Drupal URL'].values
    assert 'https://www.hr-inform.co.uk/' not in df_cand['Legacy Drupal URL'].values
    assert 'https://www.hr-inform.co.uk/user/login' not in df_cand['Legacy Drupal URL'].values
    assert 'https://www.hr-inform.co.uk/features/working-during-heatwave' not in df_cand['Legacy Drupal URL'].values
    # Download document must be separated and not in candidates
    assert 'https://www.hr-inform.co.uk/system/files/downloads/2017-09/Template%20payslips.docx' not in df_cand['Legacy Drupal URL'].values
    # Cannibalised secondary page must not be in candidates
    assert 'https://www.hr-inform.co.uk/news/redundancy-guide' not in df_cand['Legacy Drupal URL'].values
    # Parameter should be stripped
    assert 'https://www.hr-inform.co.uk/templates/disciplinary-sample' in df_cand['Legacy Drupal URL'].values
    # CTR opportunity should be flagged
    opp_row = df_cand[df_cand['Legacy Drupal URL'] == 'https://www.hr-inform.co.uk/templates/disciplinary-sample'].iloc[0]
    assert opp_row['Is CTR Opportunity'] == True

    # Verify Cannibalised CSV
    df_cannibal = pd.read_csv(cannibal_csv)
    assert 'https://www.hr-inform.co.uk/news/redundancy-guide' in df_cannibal['Cannibalised Secondary URL (Source)'].values
    assert 'https://www.hr-inform.co.uk/employment-law/statutory-redundancy' in df_cannibal['Primary Winning URL (Target)'].values

    # Verify Dato CSV
    df_dato = pd.read_csv(dato_csv)
    assert 'https://www.hr-inform.co.uk/features/working-during-heatwave' in df_dato['Live Dato URL'].values

    # Verify Download Documents CSV
    df_down = pd.read_csv(downloads_csv)
    assert 'https://www.hr-inform.co.uk/system/files/downloads/2017-09/Template%20payslips.docx' in df_down['Document URL'].values
    assert 'DOCX' in df_down['File Type'].values
    assert 'Template payslips.docx' in df_down['Document Filename'].values

    # Verify HTML
    with open(html_path, 'r', encoding='utf-8') as f:
        html = f.read()
    assert 'Top 1,000 Drupal to Dato Migration Report' in html
    assert 'Redirect 301 /news/redundancy-guide /employment-law/statutory-redundancy' in html
    assert 'Methodology and Scoring Definitions' in html
    assert 'Comp. Score (Composite Score)' in html
    assert 'Rank Sum (Combined Rank Sum)' in html
    assert 'Tier (Tiered Allocation)' in html


def test_drupal_dato_migration_report_multi_mechanism_expanded(mock_service, mocker):
    """Verifies that the report pulls more than 1,000 rows across multiple mechanisms."""
    # 600 high-click pages (low impressions) + 600 high-impression pages (zero clicks)
    rows = []
    for i in range(600):
        rows.append({
            'page': f'https://www.hr-inform.co.uk/articles/click-leader-{i}',
            'query': f'high click query {i}',
            'clicks': 1000 - i,
            'impressions': 50,
            'ctr': 0.5,
            'position': 1.5
        })
    for j in range(600):
        rows.append({
            'page': f'https://www.hr-inform.co.uk/articles/impr-leader-{j}',
            'query': f'high impression query {j}',
            'clicks': 0,
            'impressions': 10000 - j,
            'ctr': 0.0,
            'position': 8.0
        })

    mocker.patch(
        'reports.migrations.drupal_dato_top_1000_migration_report.fetch_with_cache',
        return_value=pd.DataFrame(rows)
    )

    from reports.migrations.drupal_dato_top_1000_migration_report import run_report
    site = 'https://www.hr-inform.co.uk'
    candidates_csv, _, _, _, html_path = run_report(
        mock_service, site, '2024-01-01', '2024-12-31', limit=1000
    )

    df_cand = pd.read_csv(candidates_csv)
    # Total candidates must exceed 1,000 because both top 1,000 clicks and top 1,000 impressions are included
    assert len(df_cand) == 1200
    assert 'Clicks Rank' in df_cand.columns
    assert 'Impressions Rank' in df_cand.columns
    assert 'Method A (Composite Score)' in df_cand.columns
    assert 'Method B (Combined Rank Sum)' in df_cand.columns
    assert 'Method C (Tiered Allocation)' in df_cand.columns

    # Verify both click leaders and impression leaders are present
    assert 'https://www.hr-inform.co.uk/articles/click-leader-0' in df_cand['Legacy Drupal URL'].values
    assert 'https://www.hr-inform.co.uk/articles/impr-leader-599' in df_cand['Legacy Drupal URL'].values

    with open(html_path, 'r', encoding='utf-8') as f:
        html = f.read()
    assert '1,200' in html


def test_download_documents_report(mock_service, mocker):
    """Verifies that the standalone download documents report extracts all file types."""
    mock_data = {
        'page': [
            'https://www.hr-inform.co.uk/downloads/sample-handbook.pdf',
            'https://www.hr-inform.co.uk/downloads/salary-grid.xlsx',
            'https://www.hr-inform.co.uk/downloads/payslip-template.docx',
            'https://www.hr-inform.co.uk/downloads/data-export.csv',
            'https://www.hr-inform.co.uk/articles/standard-article' # Not a document
        ],
        'query': [
            'sample employee handbook pdf',
            'salary grid template xlsx',
            'payslip template download docx',
            'workplace data export csv',
            'standard employment law article'
        ],
        'clicks': [85, 42, 60, 15, 200],
        'impressions': [900, 500, 800, 250, 3000],
        'ctr': [0.094, 0.084, 0.075, 0.06, 0.067],
        'position': [2.1, 3.4, 1.8, 4.2, 1.5]
    }
    mocker.patch(
        'reports.migrations.download_documents_report.fetch_with_cache',
        return_value=pd.DataFrame(mock_data)
    )

    from reports.migrations.download_documents_report import run_report
    site = 'https://www.hr-inform.co.uk'
    csv_path, html_path = run_report(
        mock_service, site, '2024-01-01', '2024-12-31'
    )

    assert csv_path is not None and os.path.exists(csv_path)
    assert html_path is not None and os.path.exists(html_path)

    df_docs = pd.read_csv(csv_path)
    # Only the 4 document assets should be present
    assert len(df_docs) == 4
    assert 'https://www.hr-inform.co.uk/downloads/sample-handbook.pdf' in df_docs['Document URL'].values
    assert 'https://www.hr-inform.co.uk/downloads/salary-grid.xlsx' in df_docs['Document URL'].values
    assert 'https://www.hr-inform.co.uk/articles/standard-article' not in df_docs['Document URL'].values

    assert 'PDF' in df_docs['File Type'].values
    assert 'XLSX' in df_docs['File Type'].values
    assert 'DOCX' in df_docs['File Type'].values
    assert 'CSV' in df_docs['File Type'].values

    with open(html_path, 'r', encoding='utf-8') as f:
        html = f.read()
    assert 'Download Documents Audit' in html
    assert 'sample-handbook.pdf' in html




