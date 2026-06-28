import pytest
import pandas as pd
from datetime import date
from core.cache import _get_monthly_chunks, fetch_with_cache

def test_get_monthly_chunks_single_month():
    start = '2024-01-01'
    end = '2024-01-31'
    chunks = _get_monthly_chunks(start, end)
    assert len(chunks) == 1
    assert chunks[0] == (date(2024, 1, 1), date(2024, 1, 31))

def test_get_monthly_chunks_multi_month():
    start = '2024-01-15'
    end = '2024-03-05'
    chunks = _get_monthly_chunks(start, end)
    assert len(chunks) == 3
    assert chunks[0] == (date(2024, 1, 15), date(2024, 1, 31))
    assert chunks[1] == (date(2024, 2, 1), date(2024, 2, 29)) # Leap year 2024
    assert chunks[2] == (date(2024, 3, 1), date(2024, 3, 5))

def test_aggregation_logic(mocker):
    # Mocking fetch_with_cache internals to test the aggregation
    # We'll mock _get_monthly_chunks to return two months
    mocker.patch('core.cache._get_monthly_chunks', return_value=[
        (date(2024, 1, 1), date(2024, 1, 31)),
        (date(2024, 2, 1), date(2024, 2, 29))
    ])
    
    # Mock os.path.exists to always return True so it looks in "cache"
    mocker.patch('os.path.exists', return_value=True)
    
    # Mock pd.read_csv to return specific data for each month
    df1 = pd.DataFrame({
        'page': ['url1', 'url2'],
        'clicks': [10, 20],
        'impressions': [100, 200],
        'position': [1.0, 2.0]
    })
    df2 = pd.DataFrame({
        'page': ['url1', 'url2'],
        'clicks': [5, 15],
        'impressions': [50, 150],
        'position': [3.0, 4.0]
    })
    
    mocker.patch('pandas.read_csv', side_effect=[df1, df2])
    
    result = fetch_with_cache(None, 'site', '2024-01-01', '2024-02-29', ['page'])
    
    assert len(result) == 2
    # url1: 10 + 5 = 15 clicks, 100 + 50 = 150 impressions, (1+3)/2 = 2.0 pos
    url1 = result[result['page'] == 'url1'].iloc[0]
    assert url1['clicks'] == 15
    assert url1['impressions'] == 150
    assert url1['position'] == 2.0
    assert url1['ctr'] == 0.1

def test_fetch_from_api_feedback(mocker, capsys):
    from core.cache import _fetch_from_api
    
    # Mock service
    mock_service = mocker.MagicMock()
    mock_query = mocker.MagicMock()
    mock_execute = mocker.MagicMock()
    
    mock_service.searchanalytics.return_value = mock_query
    mock_query.query.return_value = mock_execute
    
    # Return two pages of data
    # Page 1: 10000 rows (to trigger pagination loop)
    # Page 2: 50 rows (less than 10000, so it breaks the loop)
    page1_rows = [{'keys': ['page1', 'query1'], 'clicks': 10, 'impressions': 100, 'ctr': 0.1, 'position': 1.0}] * 10000
    page2_rows = [{'keys': ['page2', 'query2'], 'clicks': 5, 'impressions': 50, 'ctr': 0.1, 'position': 2.0}] * 50
    
    mock_execute.execute.side_effect = [
        {'rows': page1_rows},
        {'rows': page2_rows}
    ]
    
    df = _fetch_from_api(
        service=mock_service,
        site_url='sc-domain:example.com',
        start_date='2026-05-01',
        end_date='2026-05-31',
        dimensions=['page', 'query'],
        row_limit=10000
    )
    
    # Assert return value
    assert not df.empty
    assert len(df) == 10050
    
    # Verify printed outputs
    captured = capsys.readouterr()
    assert "Retrieved 10000 rows (total: 10000)..." in captured.out
    assert "Retrieved 50 rows (total: 10050)..." in captured.out

def test_fetch_from_api_timeout_retry(mocker, capsys):
    import socket
    from core.cache import _fetch_from_api
    
    # Mock time.sleep to not waste time
    mocker.patch('time.sleep')
    
    mock_service = mocker.MagicMock()
    mock_query = mocker.MagicMock()
    mock_execute = mocker.MagicMock()
    
    mock_service.searchanalytics.return_value = mock_query
    mock_query.query.return_value = mock_execute
    
    # First call: Timeout error
    # Second call: Success with rows
    mock_execute.execute.side_effect = [
        socket.timeout("Timeout!"),
        {'rows': [{'keys': ['page1'], 'clicks': 1, 'impressions': 10, 'ctr': 0.1, 'position': 1.0}]}
    ]
    
    df = _fetch_from_api(
        service=mock_service,
        site_url='sc-domain:example.com',
        start_date='2026-05-01',
        end_date='2026-05-31',
        dimensions=['page'],
        row_limit=10
    )
    
    assert not df.empty
    assert len(df) == 1
    
    captured = capsys.readouterr()
    assert "Timeout occurred. Retrying (attempt 1/3)..." in captured.out
    assert "Retrieved 1 rows (total: 1)..." in captured.out
