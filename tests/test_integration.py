"""
Integration tests for the full service
These tests verify the complete workflow
"""

import pytest
from unittest.mock import Mock, patch
from src.main import main


@pytest.fixture
def mock_env(monkeypatch):
    """Set up test environment variables"""
    monkeypatch.setenv('RADARR_URL', 'http://test:7878')
    monkeypatch.setenv('RADARR_API_KEY', 'test_key')
    monkeypatch.setenv('AIOSTREAMS_URL', 'http://aio:8080')
    monkeypatch.setenv('REALDEBRID_API_KEY', 'rd_key')
    monkeypatch.setenv('POLL_INTERVAL_MINUTES', '1')


@patch('schedule.run_pending')
@patch('src.processor.MovieProcessor.process_wanted_movies')
@patch('src.clients.radarr.RadarrClient.get_wanted_movies')
def test_full_workflow_integration(mock_get_wanted, mock_process, mock_schedule, mock_env):
    """Test complete workflow from startup to processing"""
    # Mock Radarr returning wanted movies
    mock_get_wanted.return_value = [
        {
            'id': 1,
            'title': 'Test Movie',
            'year': 2024,
            'imdbId': 'tt1234567'
        }
    ]

    # Mock the schedule to run once then stop
    call_count = {'count': 0}
    def run_once():
        call_count['count'] += 1
        if call_count['count'] >= 2:
            raise KeyboardInterrupt()

    mock_schedule.side_effect = run_once

    # Run main function
    result = main()

    # Verify it ran successfully
    assert result == 0
    assert mock_process.call_count >= 1


def test_configuration_error_handling(monkeypatch):
    """Test that missing configuration is handled gracefully"""
    # Don't set any environment variables
    monkeypatch.delenv('RADARR_URL', raising=False)
    monkeypatch.delenv('RADARR_API_KEY', raising=False)
    monkeypatch.delenv('AIOSTREAMS_URL', raising=False)
    monkeypatch.delenv('REALDEBRID_API_KEY', raising=False)

    result = main()

    # Should exit with error code
    assert result == 1
