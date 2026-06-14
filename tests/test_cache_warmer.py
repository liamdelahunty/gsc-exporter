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
