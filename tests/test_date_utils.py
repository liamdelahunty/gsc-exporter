import pytest
from datetime import date, datetime, timedelta
from unittest.mock import MagicMock
from core.date_utils import (
    get_latest_available_date,
    get_last_month_range,
    get_last_7_days_range,
    parse_standard_date_args
)

def test_get_latest_available_date_success(mocker):
    mock_service = MagicMock()
    # Mocking the GSC API response for a successful date check
    mock_service.searchanalytics().query().execute.return_value = {'rows': [{'keys': ['2026-05-30']}]}
    
    site_url = 'sc-domain:example.com'
    # Should find it immediately on first attempt (today is Monday 2026-06-01 in our scenario)
    # Actually the tool uses date.today(), so it depends on when the test runs.
    # Let's mock date.today() to be 2026-06-01
    mocker.patch('core.date_utils.date', mocker.Mock(today=lambda: date(2026, 6, 1)))
    
    latest_date = get_latest_available_date(mock_service, site_url)
    assert latest_date == date(2026, 6, 1)

def test_get_latest_available_date_with_lag(mocker):
    mock_service = MagicMock()
    
    def side_effect(siteUrl, body):
        if body['startDate'] == '2026-05-30':
            return MagicMock(execute=lambda: {'rows': [{'keys': ['2026-05-30']}]})
        return MagicMock(execute=lambda: {})

    mock_service.searchanalytics().query.side_effect = side_effect
    
    mocker.patch('core.date_utils.date', mocker.Mock(today=lambda: date(2026, 6, 1)))
    latest_date = get_latest_available_date(mock_service, 'sc-domain:example.com')
    assert latest_date == date(2026, 5, 30)

def test_get_last_7_days_range():
    anchor = date(2026, 5, 30)
    start, end = get_last_7_days_range(anchor)
    assert start == '2026-05-24'
    assert end == '2026-05-30'

def test_get_last_month_range():
    # If anchor is June 1st, last month is May
    anchor = date(2026, 6, 1)
    start, end = get_last_month_range(anchor)
    assert start == '2026-05-01'
    assert end == '2026-05-31'
    
    # If anchor is June 15th, last month is still May
    anchor = date(2026, 6, 15)
    start, end = get_last_month_range(anchor)
    assert start == '2026-05-01'
    assert end == '2026-05-31'

def test_parse_standard_date_args_explicit():
    args = MagicMock(start_date='2026-01-01', end_date='2026-01-07')
    start, end = parse_standard_date_args(args)
    assert start == '2026-01-01'
    assert end == '2026-01-07'

def test_parse_standard_date_args_last_7_days(mocker):
    args = MagicMock(last_7_days=True, start_date=None, end_date=None)
    mock_service = MagicMock()
    
    # Mocking searchanalytics().query(siteUrl=..., body=...).execute()
    mock_query = MagicMock()
    mock_execute = MagicMock()
    mock_execute.execute.return_value = {'rows': [{'keys': ['2026-05-30']}]}
    
    def query_side_effect(siteUrl, body):
        if body['startDate'] == '2026-05-30':
            return mock_execute
        return MagicMock(execute=lambda: {})

    mock_service.searchanalytics().query.side_effect = query_side_effect
    
    mocker.patch('core.date_utils.date', mocker.Mock(today=lambda: date(2026, 6, 1)))
    
    start, end = parse_standard_date_args(args, mock_service, 'sc-domain:example.com')
    assert start == '2026-05-24'
    assert end == '2026-05-30'
