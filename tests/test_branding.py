import os
import argparse
import pytest
from unittest.mock import patch
from core.branding import load_branding_config, apply_branding_to_html, get_config_path

def test_get_config_path_default():
    with patch.dict(os.environ, {}, clear=True):
        with patch('sys.argv', ['script.py']):
            assert get_config_path() == os.path.join('config', 'branding.json')

def test_get_config_path_env():
    with patch.dict(os.environ, {'GSC_BRANDING_CONFIG': 'custom.json'}):
        assert get_config_path() == 'custom.json'

def test_get_config_path_cli():
    with patch.dict(os.environ, {}, clear=True):
        with patch('sys.argv', ['script.py', '--branding-config', 'cli-config.json']):
            assert get_config_path() == 'cli-config.json'
            
        with patch('sys.argv', ['script.py', '--branding-config=cli-config2.json']):
            assert get_config_path() == 'cli-config2.json'

def test_apply_branding_disabled():
    html = "<html><head></head><body><header>Original Header</header><main></main><footer>Original Footer</footer></body></html>"
    config = {"enabled": False}
    result = apply_branding_to_html(html, "test.html", config)
    assert result == html

def test_apply_branding_enabled_inject():
    html = "<html><head></head><body><header><div class='container'>Original Header</div></header><main></main><footer>Original Footer</footer></body></html>"
    config = {
        "enabled": True,
        "theme": {
            "primary_colour": "#ff0000"
        },
        "header": {
            "enabled": True,
            "logo_url": "http://logo.png",
            "text": "My Brand",
            "mode": "inject"
        },
        "footer": {
            "enabled": True,
            "text": "Footer Brand",
            "mode": "inject"
        }
    }
    result = apply_branding_to_html(html, "test.html", config)
    assert "#ff0000" in result
    assert "My Brand" in result
    assert "Footer Brand" in result
    assert "Original Header" in result
    assert "Original Footer" in result

def test_apply_branding_replace():
    html = "<html><head></head><body><header>Original Header</header><main></main><footer>Original Footer</footer></body></html>"
    config = {
        "enabled": True,
        "header": {
            "enabled": True,
            "text": "Brand Header",
            "mode": "replace"
        },
        "footer": {
            "enabled": True,
            "text": "Brand Footer",
            "mode": "replace"
        }
    }
    result = apply_branding_to_html(html, "test.html", config)
    assert "Brand Header" in result
    assert "Brand Footer" in result
    assert "Original Header" not in result
    assert "Original Footer" not in result

def test_apply_branding_bar():
    html = "<html><head></head><body><header>Original Header</header><main></main><footer>Original Footer</footer></body></html>"
    config = {
        "enabled": True,
        "header": {
            "enabled": True,
            "text": "Top Bar Brand",
            "mode": "bar"
        },
        "footer": {
            "enabled": True,
            "text": "Bottom Bar Brand",
            "mode": "bar"
        }
    }
    result = apply_branding_to_html(html, "test.html", config)
    assert "Top Bar Brand" in result
    assert "Bottom Bar Brand" in result
    assert "Original Header" in result
    assert "Original Footer" in result

def test_argparse_patch():
    parser = argparse.ArgumentParser()
    # parse_args should automatically add '--branding-config'
    # Parse empty args to check
    args = parser.parse_args([])
    assert hasattr(args, 'branding_config')

def test_file_write_hook(tmp_path):
    test_file = tmp_path / "report.html"
    config = {
        "enabled": True,
        "header": {
            "enabled": True,
            "text": "File Brand Header",
            "mode": "bar"
        }
    }
    
    with patch('core.branding.load_branding_config', return_value=config):
        with open(test_file, 'w', encoding='utf-8') as f:
            f.write("<html><head></head><body><h1>Hello</h1></body></html>")
            
    with open(test_file, 'r', encoding='utf-8') as f:
        content = f.read()
        
    assert "File Brand Header" in content
    assert "Hello" in content

def test_branding_integration_on_report(mocker):
    import pandas as pd
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
    
    from unittest.mock import MagicMock
    mock_service = MagicMock()
    mock_service.sites().list().execute.return_value = {
        'siteEntry': [{'siteUrl': 'https://www.example.com/'}]
    }

    # Patch the fetch_with_cache function where it is used
    mocker.patch('reports.performance_analysis.fetch_with_cache', return_value=pd.DataFrame(mock_df_data))
    
    # We want to run with branding enabled
    config = {
        "enabled": True,
        "theme": {
            "primary_colour": "#123456"
        },
        "header": {
            "enabled": True,
            "text": "Integration Brand Header",
            "mode": "bar"
        }
    }
    
    from core.naming import get_output_dir, get_filename_slug
    site = 'https://www.example.com/'
    
    # Run the report with the mock config loaded
    with patch('core.branding.load_branding_config', return_value=config):
        from reports.performance_analysis import run_report
        run_report(mock_service, site, '2024-01-01', '2024-01-31', '2023-01-01', '2023-01-31')
        
    output_dir = get_output_dir(site)
    slug = get_filename_slug(site)
    html_path = os.path.join(output_dir, f"performance-analysis-{slug}-2024-01-01-to-2024-01-31.html")
    
    assert os.path.exists(html_path)
    
    # Verify the HTML file was branded
    with open(html_path, 'r', encoding='utf-8') as f:
        content = f.read()
        
    assert "Integration Brand Header" in content
    assert "#123456" in content
    
    # Clean up output files
    if os.path.exists(html_path):
        os.remove(html_path)
    csv_path = os.path.join(output_dir, f"performance-analysis-{slug}-2024-01-01-to-2024-01-31.csv")
    if os.path.exists(csv_path):
        os.remove(csv_path)

