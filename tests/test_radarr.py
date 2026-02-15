import pytest
from unittest.mock import Mock, patch
from src.clients.radarr import RadarrClient


@pytest.fixture
def radarr_client():
    return RadarrClient('http://localhost:7878', 'test_api_key')


def test_radarr_client_initialization(radarr_client):
    """Test Radarr client initializes correctly"""
    assert radarr_client.url == 'http://localhost:7878'
    assert radarr_client.api_key == 'test_api_key'
    assert radarr_client.headers == {'X-Api-Key': 'test_api_key'}


@patch('requests.get')
def test_get_wanted_movies(mock_get, radarr_client):
    """Test fetching wanted movies from Radarr"""
    mock_response = Mock()
    mock_response.json.return_value = {
        'records': [
            {
                'id': 1,
                'title': 'Test Movie',
                'year': 2024,
                'imdbId': 'tt1234567'
            }
        ]
    }
    mock_response.raise_for_status = Mock()
    mock_get.return_value = mock_response

    movies = radarr_client.get_wanted_movies()

    assert len(movies) == 1
    assert movies[0]['title'] == 'Test Movie'
    mock_get.assert_called_once_with(
        'http://localhost:7878/api/v3/wanted/missing',
        headers={'X-Api-Key': 'test_api_key'},
        params={'pageSize': 1000}
    )


@patch('requests.get')
def test_get_movie_by_id(mock_get, radarr_client):
    """Test fetching single movie by ID"""
    mock_response = Mock()
    mock_response.json.return_value = {
        'id': 1,
        'title': 'Test Movie',
        'year': 2024,
        'imdbId': 'tt1234567'
    }
    mock_response.raise_for_status = Mock()
    mock_get.return_value = mock_response

    movie = radarr_client.get_movie(1)

    assert movie['title'] == 'Test Movie'
    mock_get.assert_called_once_with(
        'http://localhost:7878/api/v3/movie/1',
        headers={'X-Api-Key': 'test_api_key'}
    )


@patch('requests.put')
@patch('requests.get')
def test_unmonitor_movie(mock_get, mock_put, radarr_client):
    """Test unmonitoring a movie"""
    # Mock get_movie response
    mock_get_response = Mock()
    mock_get_response.json.return_value = {
        'id': 1,
        'title': 'Test Movie',
        'year': 2024,
        'imdbId': 'tt1234567',
        'monitored': True
    }
    mock_get_response.raise_for_status = Mock()
    mock_get.return_value = mock_get_response

    # Mock PUT response
    mock_put_response = Mock()
    mock_put_response.raise_for_status = Mock()
    mock_put.return_value = mock_put_response

    result = radarr_client.unmonitor_movie(1)

    assert result is True
    # Verify GET was called
    mock_get.assert_called_once_with(
        'http://localhost:7878/api/v3/movie/1',
        headers={'X-Api-Key': 'test_api_key'}
    )
    # Verify PUT was called with monitored=False
    mock_put.assert_called_once()
    put_call_args = mock_put.call_args
    assert put_call_args[1]['json']['monitored'] is False


@patch('requests.put')
@patch('requests.get')
def test_unmonitor_movie_handles_error(mock_get, mock_put, radarr_client):
    """Test unmonitoring handles errors gracefully"""
    mock_get.side_effect = Exception("API Error")

    result = radarr_client.unmonitor_movie(1)

    assert result is False
