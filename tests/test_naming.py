import pytest
from core.naming import get_property_name, get_output_dir, get_filename_slug

def test_get_property_name_domain():
    assert get_property_name('sc-domain:example.com') == 'sc-domain.example.com'

def test_get_property_name_url():
    assert get_property_name('https://www.example.com/') == 'www.example.com'
    assert get_property_name('http://example.com/subfolder') == 'example.com'

def test_get_output_dir():
    assert get_output_dir('https://www.example.com/') == 'output/www.example.com'
    assert get_output_dir('sc-domain:example.com', base_dir='test_output') == 'test_output/sc-domain.example.com'

def test_get_filename_slug():
    assert get_filename_slug('https://www.example.com/') == 'www-example-com'
    assert get_filename_slug('sc-domain:example.com') == 'sc-domain-example-com'
