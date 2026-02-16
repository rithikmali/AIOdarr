"""
Integration tests for the full service
These tests verify the complete workflow
"""

from unittest.mock import patch

import pytest

from src.main import main


@pytest.fixture
def mock_env(monkeypatch):
    """Set up test environment variables"""
    monkeypatch.setenv("RADARR_URL", "http://test:7878")
    monkeypatch.setenv("RADARR_API_KEY", "test_key")
    monkeypatch.setenv("AIOSTREAMS_URL", "http://aio:8080")
    monkeypatch.setenv("POLL_INTERVAL_MINUTES", "1")


@patch("time.sleep")
@patch("schedule.run_pending")
@patch("src.media_processor.MediaProcessor.process_all")
def test_full_workflow_integration(mock_process, mock_schedule, mock_sleep, mock_env):
    """Test complete workflow from startup to processing"""
    # Mock the schedule to run once then stop
    call_count = {"count": 0}

    def run_once():
        call_count["count"] += 1
        if call_count["count"] >= 2:
            raise KeyboardInterrupt()

    mock_schedule.side_effect = run_once

    # Run main function
    result = main()

    # Verify it ran successfully
    assert result == 0
    # process_all is called once on startup + potentially by scheduler
    assert mock_process.call_count >= 1


def test_configuration_error_handling(monkeypatch):
    """Test that missing configuration is handled gracefully"""
    # Don't set any environment variables
    monkeypatch.delenv("RADARR_URL", raising=False)
    monkeypatch.delenv("RADARR_API_KEY", raising=False)
    monkeypatch.delenv("SONARR_URL", raising=False)
    monkeypatch.delenv("SONARR_API_KEY", raising=False)
    monkeypatch.delenv("AIOSTREAMS_URL", raising=False)

    result = main()

    # Should exit with error code
    assert result == 1
