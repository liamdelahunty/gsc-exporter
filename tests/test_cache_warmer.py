import pytest
from unittest.mock import MagicMock, patch
from utilities.cache_warmer import warm_site, GOLDEN_DIMENSIONS
from datetime import date

def test_warm_site(mocker):
    # Mock core utilities
    mock_latest = date(2026, 6, 14)
    mocker.patch('utilities.cache_warmer.get_latest_available_date', return_value=mock_latest)
    mocker.patch('utilities.cache_warmer.get_last_month_range', return_value=('2026-05-01', '2026-05-31'))
    mocker.patch('utilities.cache_warmer.get_month_range_lookback', return_value=('2025-02-01', '2026-05-31'))
    
    # Mock fetch_with_cache
    mock_fetch = mocker.patch('utilities.cache_warmer.fetch_with_cache')
    
    service = MagicMock()
    site_url = 'sc-domain:example.com'
    
    warm_site(service, site_url, lookback_months=16)
    
    # Verify fetch_with_cache was called for each golden dimension
    assert mock_fetch.call_count == len(GOLDEN_DIMENSIONS)
    
    # Check one specific call
    # First call should be for 'Daily Totals' (['date'])
    mock_fetch.assert_any_call(
        service, 
        site_url, 
        '2025-02-01', 
        '2026-05-31', 
        ['date'], 
        label="Warming Daily Totals"
    )
    
    # Check the granular mapping call
    mock_fetch.assert_any_call(
        service, 
        site_url, 
        '2025-02-01', 
        '2026-05-31', 
        ['page', 'query'], 
        label="Warming Page-Query Mapping (Granular)"
    )

def test_warm_site_with_adjustment(mocker):
    # Mock core utilities
    mock_latest = date(2026, 6, 14)
    mocker.patch('utilities.cache_warmer.get_latest_available_date', return_value=mock_latest)
    mocker.patch('utilities.cache_warmer.get_last_month_range', return_value=('2026-05-01', '2026-05-31'))
    mocker.patch('utilities.cache_warmer.get_month_range_lookback', return_value=('2025-02-01', '2026-05-31'))
    
    # First available GSC date is 2025-02-13, first complete month start is 2025-03-01
    mocker.patch('utilities.cache_warmer.get_first_available_gsc_date', return_value=date(2025, 2, 13))
    mocker.patch('utilities.cache_warmer.get_first_complete_month_start', return_value=date(2025, 3, 1))
    
    # Mock fetch_with_cache
    mock_fetch = mocker.patch('utilities.cache_warmer.fetch_with_cache')
    
    service = MagicMock()
    site_url = 'sc-domain:example.com'
    
    warm_site(service, site_url, lookback_months=16)
    
    # Verify fetch_with_cache was called with adjusted start_date: '2025-03-01'
    assert mock_fetch.call_count == len(GOLDEN_DIMENSIONS)
    mock_fetch.assert_any_call(
        service, 
        site_url, 
        '2025-03-01', 
        '2026-05-31', 
        ['date'], 
        label="Warming Daily Totals"
    )

def test_warm_site_no_complete_months(mocker):
    # Mock core utilities
    mock_latest = date(2025, 2, 15)
    mocker.patch('utilities.cache_warmer.get_latest_available_date', return_value=mock_latest)
    mocker.patch('utilities.cache_warmer.get_last_month_range', return_value=('2025-01-01', '2025-01-31'))
    mocker.patch('utilities.cache_warmer.get_month_range_lookback', return_value=('2023-10-01', '2025-01-31'))
    
    # First available GSC date is 2025-02-13, first complete month start is 2025-03-01
    mocker.patch('utilities.cache_warmer.get_first_available_gsc_date', return_value=date(2025, 2, 13))
    mocker.patch('utilities.cache_warmer.get_first_complete_month_start', return_value=date(2025, 3, 1))
    
    # Mock fetch_with_cache
    mock_fetch = mocker.patch('utilities.cache_warmer.fetch_with_cache')
    
    service = MagicMock()
    site_url = 'sc-domain:example.com'
    
    warm_site(service, site_url, lookback_months=16)
    
    # Since start_date ('2025-03-01') > end_date ('2025-01-31'), fetch_with_cache should not be called
    assert mock_fetch.call_count == 0

