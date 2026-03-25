from unittest.mock import Mock, patch

import pytest

from src.clients.aiostreams import AIOStreamsClient


@pytest.fixture
def aio_client():
    return AIOStreamsClient("http://localhost:8080")


def test_aiostreams_client_initialization(aio_client):
    """Test AIOStreams client initializes correctly"""
    assert aio_client.url == "http://localhost:8080"


@patch("requests.get")
def test_search_movie_with_streams(mock_get, aio_client):
    """Test searching for a movie returns streams in the new v2 format"""
    mock_response = Mock()
    mock_response.json.return_value = {
        "streams": [
            {
                "name": "2160p BluRay REMUX ",
                "description": "HDR10+ | DV | IMAX  | Atmos | TrueHD \n103 GB 📊 81 Mbps | 🏷️ somegroup \nMovie.2024.2160p.REMUX.mkv ",
                "url": "https://aiostreams.example.com/playback/test1",
                "behaviorHints": {
                    "filename": "Movie.2024.2160p.REMUX.mkv",
                    "videoSize": 102682361361,
                },
            },
            {
                "name": "1080p WEB-DL ",
                "description": "1080p\nMovie.2024.1080p.WEB.mkv",
                "url": "https://aiostreams.example.com/playback/test2",
                "behaviorHints": {
                    "filename": "Movie.2024.1080p.WEB.mkv",
                    "videoSize": 8000000000,
                },
            },
            # Stream with no URL should be skipped
            {
                "name": "720p WEB-DL ",
                "description": "720p",
                "url": None,
                "behaviorHints": {},
            },
        ]
    }
    mock_response.raise_for_status = Mock()
    mock_get.return_value = mock_response

    streams = aio_client.search_movie("tt1234567")

    assert len(streams) == 2
    assert streams[0]["title"] == "2160p BluRay REMUX "
    assert streams[0]["quality"] == 2160
    assert streams[0]["filename"] == "Movie.2024.2160p.REMUX.mkv"
    assert streams[0]["url"] == "https://aiostreams.example.com/playback/test1"
    assert streams[1]["title"] == "1080p WEB-DL "
    assert streams[1]["quality"] == 1080
    mock_get.assert_called_once_with(
        "http://localhost:8080/stream/movie/tt1234567.json", timeout=30
    )


@patch("requests.get")
def test_search_movie_skips_streams_without_url(mock_get, aio_client):
    """Streams without a playback URL are excluded"""
    mock_response = Mock()
    mock_response.json.return_value = {
        "streams": [
            {
                "name": "2160p BluRay",
                "description": "HDR",
                "url": None,
                "behaviorHints": {"filename": "Movie.mkv"},
            }
        ]
    }
    mock_response.raise_for_status = Mock()
    mock_get.return_value = mock_response

    streams = aio_client.search_movie("tt1234567")
    assert len(streams) == 0


@patch("requests.get")
def test_search_movie_no_streams(mock_get, aio_client):
    """Test searching for movie with no streams"""
    mock_response = Mock()
    mock_response.json.return_value = {"streams": []}
    mock_response.raise_for_status = Mock()
    mock_get.return_value = mock_response

    streams = aio_client.search_movie("tt1234567")
    assert len(streams) == 0


@patch("requests.get")
def test_search_movie_handles_error(mock_get, aio_client):
    """Test search handles API errors gracefully"""
    mock_get.side_effect = Exception("API Error")

    streams = aio_client.search_movie("tt1234567")
    assert len(streams) == 0


@patch("requests.get")
def test_search_episode(mock_get, aio_client):
    """Test searching for a TV episode"""
    mock_response = Mock()
    mock_response.json.return_value = {
        "streams": [
            {
                "name": "2160p WEB-DL ",
                "description": "HDR | Atmos\n7 GB 📊 55 Mbps | 🏷️ NTb \nShow.S03E04.2160p.mkv ",
                "url": "https://aiostreams.example.com/playback/episode",
                "behaviorHints": {
                    "filename": "Show.S03E04.2160p.mkv",
                    "videoSize": 6697557046,
                },
            }
        ]
    }
    mock_response.raise_for_status = Mock()
    mock_get.return_value = mock_response

    streams = aio_client.search_episode("tt9999999", 3, 4)

    assert len(streams) == 1
    assert streams[0]["quality"] == 2160
    assert streams[0]["filename"] == "Show.S03E04.2160p.mkv"
    mock_get.assert_called_once_with(
        "http://localhost:8080/stream/series/tt9999999:3:4.json", timeout=30
    )


def test_parse_quality_4k(aio_client):
    """Test quality parsing for 4K/2160p"""
    assert aio_client._parse_quality("2160p BluRay REMUX") == 2160
    assert aio_client._parse_quality("Movie 4K UHD") == 2160


def test_parse_quality_1080p(aio_client):
    """Test quality parsing for 1080p"""
    assert aio_client._parse_quality("1080p WEB-DL") == 1080


def test_parse_quality_720p(aio_client):
    """Test quality parsing for 720p"""
    assert aio_client._parse_quality("720p HDTV") == 720


def test_parse_quality_default(aio_client):
    """Test quality parsing defaults to 480"""
    assert aio_client._parse_quality("DVDRip") == 480


def test_filter_streams_includes_stream_without_video_hash(aio_client):
    """Streams without videoHash are accepted as long as they have a URL"""
    streams = [
        {
            "name": "2160p WEB-DL ",
            "description": "HDR | Atmos\n7 GB\nShow.S03E04.2160p.mkv ",
            "url": "https://aiostreams.elfhosted.com/playback/test",
            "behaviorHints": {
                "filename": "Show.S03E04.2160p.mkv",
                "videoSize": 6697557046,
            },
        }
    ]
    result = aio_client._filter_streams(streams)
    assert len(result) == 1
    assert result[0]["filename"] == "Show.S03E04.2160p.mkv"
    assert result[0]["quality"] == 2160


def test_filter_streams_captures_empty_filename_when_absent(aio_client):
    """filename defaults to empty string when behaviorHints has no filename"""
    streams = [
        {
            "name": "1080p WEB-DL",
            "description": "1080p",
            "url": "https://example.com/playback/test",
            "behaviorHints": {"videoHash": "abc123"},
        }
    ]
    result = aio_client._filter_streams(streams)
    assert len(result) == 1
    assert result[0]["filename"] == ""


def test_filter_streams_skips_streams_without_url(aio_client):
    """Streams without a URL are filtered out"""
    streams = [
        {
            "name": "1080p WEB-DL",
            "description": "1080p",
            "url": None,
            "behaviorHints": {},
        },
        {
            "name": "720p WEB",
            "description": "720p",
            # url key missing entirely
            "behaviorHints": {},
        },
        {
            "name": "2160p BluRay",
            "description": "2160p",
            "url": "https://example.com/playback/valid",
            "behaviorHints": {"filename": "Movie.mkv"},
        },
    ]
    result = aio_client._filter_streams(streams)
    assert len(result) == 1
    assert result[0]["title"] == "2160p BluRay"
