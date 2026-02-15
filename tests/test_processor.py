import pytest
from unittest.mock import Mock, patch
from src.processor import MovieProcessor
from src.config import Config


@pytest.fixture
def mock_config(monkeypatch):
    """Create mock configuration"""
    monkeypatch.setenv('RADARR_URL', 'http://test:7878')
    monkeypatch.setenv('RADARR_API_KEY', 'test_key')
    monkeypatch.setenv('AIOSTREAMS_URL', 'http://aio:8080')
    return Config()


@pytest.fixture
def processor(mock_config):
    """Create processor with mocked clients"""
    with patch('src.processor.RadarrClient'), \
         patch('src.processor.AIOStreamsClient'):
        return MovieProcessor(mock_config)


def test_processor_initialization(processor):
    """Test processor initializes with all clients"""
    assert processor.radarr is not None
    assert processor.aiostreams is not None
    assert processor.storage is not None


def test_process_movie_no_imdb_id(processor):
    """Test processing skips movies without IMDB ID"""
    movie = {
        'id': 1,
        'title': 'Test Movie',
        'year': 2024,
        'imdbId': None
    }

    result = processor._process_movie(movie)

    assert result is False


def test_process_movie_no_streams_found(processor):
    """Test processing when no cached streams found"""
    processor.aiostreams.search_movie = Mock(return_value=[])

    movie = {
        'id': 1,
        'title': 'Test Movie',
        'year': 2024,
        'imdbId': 'tt1234567'
    }

    result = processor._process_movie(movie)

    assert result is False
    processor.aiostreams.search_movie.assert_called_once_with('tt1234567')


def test_process_movie_success_with_url(processor):
    """Test successful movie processing with AIOStreams URL"""
    processor.aiostreams.search_movie = Mock(return_value=[
        {
            'title': '⚡ Test Movie 1080p',
            'url': 'https://aiostreams.example.com/playback/test',
            'quality': 1080
        }
    ])
    processor._trigger_aiostreams_download = Mock(return_value=True)
    processor.radarr.unmonitor_movie = Mock(return_value=True)

    movie = {
        'id': 1,
        'title': 'Test Movie',
        'year': 2024,
        'imdbId': 'tt1234567'
    }

    result = processor._process_movie(movie)

    assert result is True
    processor._trigger_aiostreams_download.assert_called_once()
    processor.radarr.unmonitor_movie.assert_called_once_with(1)
    assert processor.storage.should_skip(1) is True


def test_process_movie_fails_without_url(processor):
    """Test that processing fails if stream has no URL"""
    processor.aiostreams.search_movie = Mock(return_value=[
        {
            'title': '⚡ Test Movie 1080p',
            'infoHash': 'abc123',  # Has infohash but no URL
            'quality': 1080
        }
    ])

    movie = {
        'id': 1,
        'title': 'Test Movie',
        'year': 2024,
        'imdbId': 'tt1234567'
    }

    result = processor._process_movie(movie)

    assert result is False
    assert processor.storage.processed[1]['success'] is False


def test_process_movie_uses_first_stream(processor):
    """Test that processor uses first stream from AIOStreams (pre-sorted)"""
    processor.aiostreams.search_movie = Mock(return_value=[
        {'title': 'Stream 1', 'url': 'https://example.com/stream1', 'quality': 1080},
        {'title': 'Stream 2', 'url': 'https://example.com/stream2', 'quality': 720},
        {'title': 'Stream 3', 'url': 'https://example.com/stream3', 'quality': 480}
    ])
    processor._trigger_aiostreams_download = Mock(return_value=True)

    movie = {
        'id': 1,
        'title': 'Test Movie',
        'year': 2024,
        'imdbId': 'tt1234567'
    }

    result = processor._process_movie(movie)

    assert result is True
    # Should only try first stream
    assert processor._trigger_aiostreams_download.call_count == 1
    assert 'stream1' in processor._trigger_aiostreams_download.call_args[0][0]


@patch('requests.head')
def test_trigger_aiostreams_download(mock_head, processor):
    """Test triggering AIOStreams download via HEAD request"""
    mock_response = Mock()
    mock_response.raise_for_status = Mock()
    mock_head.return_value = mock_response

    result = processor._trigger_aiostreams_download('https://example.com/stream', 'Test Movie')

    assert result is True
    mock_head.assert_called_once_with('https://example.com/stream', timeout=30, allow_redirects=True)


def test_process_wanted_movies(processor):
    """Test processing all wanted movies"""
    processor.radarr.get_wanted_movies = Mock(return_value=[
        {'id': 1, 'title': 'Movie 1', 'year': 2024, 'imdbId': 'tt1111111'},
        {'id': 2, 'title': 'Movie 2', 'year': 2024, 'imdbId': 'tt2222222'}
    ])
    processor._process_movie = Mock(side_effect=[True, False])

    processor.process_wanted_movies()

    assert processor._process_movie.call_count == 2
