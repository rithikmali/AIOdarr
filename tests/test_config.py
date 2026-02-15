import pytest
from src.config import Config


def test_config_loads_from_env(monkeypatch):
    """Test that configuration loads from environment variables"""
    monkeypatch.setenv('RADARR_URL', 'http://test:7878')
    monkeypatch.setenv('RADARR_API_KEY', 'test_key')
    monkeypatch.setenv('AIOSTREAMS_URL', 'http://aio:8080')
    monkeypatch.setenv('REALDEBRID_API_KEY', 'rd_key')

    config = Config()

    assert config.radarr_url == 'http://test:7878'
    assert config.radarr_api_key == 'test_key'
    assert config.aiostreams_url == 'http://aio:8080'
    assert config.realdebrid_api_key == 'rd_key'


def test_config_uses_defaults(monkeypatch):
    """Test that configuration uses default values"""
    monkeypatch.setenv('RADARR_URL', 'http://test:7878')
    monkeypatch.setenv('RADARR_API_KEY', 'test_key')
    monkeypatch.setenv('AIOSTREAMS_URL', 'http://aio:8080')
    monkeypatch.setenv('REALDEBRID_API_KEY', 'rd_key')

    config = Config()

    assert config.poll_interval_minutes == 10
    assert config.retry_failed_hours == 24
    assert config.log_level == 'INFO'


def test_config_validates_required_fields(monkeypatch):
    """Test that missing required fields raise error"""
    monkeypatch.delenv('RADARR_URL', raising=False)
    monkeypatch.delenv('RADARR_API_KEY', raising=False)
    monkeypatch.delenv('AIOSTREAMS_URL', raising=False)
    monkeypatch.delenv('REALDEBRID_API_KEY', raising=False)

    with pytest.raises(ValueError, match="RADARR_URL is required"):
        Config()
