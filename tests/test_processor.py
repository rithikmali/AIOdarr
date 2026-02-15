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
    monkeypatch.setenv('REALDEBRID_API_KEY', 'rd_key')
    return Config()


@pytest.fixture
def processor(mock_config):
    """Create processor with mocked clients"""
    with patch('src.processor.RadarrClient'), \
         patch('src.processor.AIOStreamsClient'), \
         patch('src.processor.RealDebridClient'):
        return MovieProcessor(mock_config)


def test_processor_initialization(processor):
    """Test processor initializes with all clients"""
    assert processor.radarr is not None
    assert processor.aiostreams is not None
    assert processor.rd is not None
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


def test_process_movie_success(processor):
    """Test successful movie processing"""
    processor.aiostreams.search_movie = Mock(return_value=[
        {
            'title': '⚡ Test Movie 1080p',
            'infoHash': 'abc123',
            'quality': 1080
        }
    ])
    processor.rd.add_magnet = Mock(return_value='rd_123')

    movie = {
        'id': 1,
        'title': 'Test Movie',
        'year': 2024,
        'imdbId': 'tt1234567'
    }

    result = processor._process_movie(movie)

    assert result is True
    processor.rd.add_magnet.assert_called_once_with('abc123')
    assert processor.storage.should_skip(1) is True


def test_process_movie_uses_first_stream(processor):
    """Test that processor uses first stream from AIOStreams (pre-sorted)"""
    processor.aiostreams.search_movie = Mock(return_value=[
        {'title': 'Stream 1', 'infoHash': 'hash1', 'quality': 1080},
        {'title': 'Stream 2', 'infoHash': 'hash2', 'quality': 720},
        {'title': 'Stream 3', 'infoHash': 'hash3', 'quality': 480}
    ])
    processor.rd.add_magnet = Mock(return_value='rd_123')

    movie = {
        'id': 1,
        'title': 'Test Movie',
        'year': 2024,
        'imdbId': 'tt1234567'
    }

    result = processor._process_movie(movie)

    assert result is True
    # Should only try first stream
    assert processor.rd.add_magnet.call_count == 1
    processor.rd.add_magnet.assert_called_once_with('hash1')


def test_process_wanted_movies(processor):
    """Test processing all wanted movies"""
    processor.radarr.get_wanted_movies = Mock(return_value=[
        {'id': 1, 'title': 'Movie 1', 'year': 2024, 'imdbId': 'tt1111111'},
        {'id': 2, 'title': 'Movie 2', 'year': 2024, 'imdbId': 'tt2222222'}
    ])
    processor._process_movie = Mock(side_effect=[True, False])

    processor.process_wanted_movies()

    assert processor._process_movie.call_count == 2
