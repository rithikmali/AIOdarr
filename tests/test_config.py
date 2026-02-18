import pytest

from src.config import Config


def test_config_loads_from_env(monkeypatch):
    """Test that configuration loads from environment variables"""
    monkeypatch.setenv("RADARR_URL", "http://test:7878")
    monkeypatch.setenv("RADARR_API_KEY", "test_key")
    monkeypatch.setenv("AIOSTREAMS_URL", "http://aio:8080")

    config = Config()

    assert config.radarr_url == "http://test:7878"
    assert config.radarr_api_key == "test_key"
    assert config.aiostreams_url == "http://aio:8080"


def test_config_uses_defaults(monkeypatch):
    """Test that configuration uses default values"""
    monkeypatch.setenv("RADARR_URL", "http://test:7878")
    monkeypatch.setenv("RADARR_API_KEY", "test_key")
    monkeypatch.setenv("AIOSTREAMS_URL", "http://aio:8080")
    # Clear optional env vars to test defaults
    monkeypatch.delenv("POLL_INTERVAL_MINUTES", raising=False)
    monkeypatch.delenv("RETRY_FAILED_HOURS", raising=False)
    monkeypatch.delenv("LOG_LEVEL", raising=False)

    config = Config()

    assert config.poll_interval_minutes == 10
    assert config.retry_failed_hours == 24
    assert config.log_level == "INFO"


def test_config_validates_aiostreams_required(monkeypatch):
    """Test that missing AIOSTREAMS_URL raises error"""
    monkeypatch.setenv("RADARR_URL", "http://test:7878")
    monkeypatch.setenv("RADARR_API_KEY", "test_key")
    monkeypatch.delenv("AIOSTREAMS_URL", raising=False)

    with pytest.raises(ValueError, match="AIOSTREAMS_URL is required"):
        Config()


def test_config_validates_at_least_one_service(monkeypatch):
    """Test that at least one of Radarr or Sonarr must be configured"""
    monkeypatch.setenv("AIOSTREAMS_URL", "http://aio:8080")
    monkeypatch.delenv("RADARR_URL", raising=False)
    monkeypatch.delenv("RADARR_API_KEY", raising=False)
    monkeypatch.delenv("SONARR_URL", raising=False)
    monkeypatch.delenv("SONARR_API_KEY", raising=False)

    with pytest.raises(ValueError, match="At least one of Radarr or Sonarr must be configured"):
        Config()


def test_discord_webhook_url_loads_when_set(monkeypatch):
    """Test Discord webhook URL loads from environment"""
    monkeypatch.setenv("AIOSTREAMS_URL", "http://aiostreams")
    monkeypatch.setenv("RADARR_URL", "http://radarr")
    monkeypatch.setenv("RADARR_API_KEY", "test-key")
    monkeypatch.setenv("DISCORD_WEBHOOK_URL", "https://discord.com/api/webhooks/123/abc")

    config = Config()
    assert config.discord_webhook_url == "https://discord.com/api/webhooks/123/abc"


def test_discord_webhook_url_defaults_to_empty_string(monkeypatch):
    """Test Discord webhook URL defaults to empty string when not set"""
    monkeypatch.setenv("AIOSTREAMS_URL", "http://aiostreams")
    monkeypatch.setenv("RADARR_URL", "http://radarr")
    monkeypatch.setenv("RADARR_API_KEY", "test-key")
    monkeypatch.delenv("DISCORD_WEBHOOK_URL", raising=False)

    config = Config()
    assert config.discord_webhook_url == ""


def test_config_realdebrid_api_key_from_env(monkeypatch):
    """REALDEBRID_API_KEY is loaded when set"""
    monkeypatch.setenv("AIOSTREAMS_URL", "http://aiostreams")
    monkeypatch.setenv("RADARR_URL", "http://radarr")
    monkeypatch.setenv("RADARR_API_KEY", "test-key")
    monkeypatch.setenv("REALDEBRID_API_KEY", "rd-secret-key")

    config = Config()

    assert config.realdebrid_api_key == "rd-secret-key"


def test_config_realdebrid_api_key_defaults_empty(monkeypatch):
    """REALDEBRID_API_KEY defaults to empty string when not set"""
    monkeypatch.setenv("AIOSTREAMS_URL", "http://aiostreams")
    monkeypatch.setenv("RADARR_URL", "http://radarr")
    monkeypatch.setenv("RADARR_API_KEY", "test-key")
    monkeypatch.delenv("REALDEBRID_API_KEY", raising=False)

    config = Config()

    assert config.realdebrid_api_key == ""
