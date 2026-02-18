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
def test_search_movie_with_cached_streams(mock_get, aio_client):
    """Test searching for movie returns cached streams"""
    mock_response = Mock()
    mock_response.json.return_value = {
        "streams": [
            {
                "name": "[RD⚡️☁️]\n4K🔥UHD",
                "description": "🎬 Test Movie (2024)\n💎 ʀᴇᴍᴜx | 🎞️ ʜᴇᴠᴄ\n📦 50 GB\n📄 2160p",
                "infoHash": "abc123def456",
                "url": "https://aiostreams.example.com/playback/test",
                "behaviorHints": {"videoHash": "abc123"},
            },
            {
                "name": "Test Movie 2024 720p WEB-DL",
                "description": "720p WEB-DL",
                "infoHash": "xyz789",
                "url": None,
            },
        ]
    }
    mock_response.raise_for_status = Mock()
    mock_get.return_value = mock_response

    streams = aio_client.search_movie("tt1234567")

    assert len(streams) == 1  # Only cached stream (⚡)
    assert "[RD⚡️☁️]" in streams[0]["title"]
    assert streams[0]["infoHash"] == "abc123def456"
    assert streams[0]["url"] == "https://aiostreams.example.com/playback/test"
    assert streams[0]["quality"] == 2160  # Should parse from description
    mock_get.assert_called_once_with(
        "http://localhost:8080/stream/movie/tt1234567.json", timeout=30
    )


@patch("requests.get")
def test_search_movie_no_streams(mock_get, aio_client):
    """Test searching for movie with no cached streams"""
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


def test_parse_quality_4k(aio_client):
    """Test quality parsing for 4K/2160p"""
    assert aio_client._parse_quality("Movie 2160p BluRay") == 2160
    assert aio_client._parse_quality("Movie 4K UHD") == 2160


def test_parse_quality_1080p(aio_client):
    """Test quality parsing for 1080p"""
    assert aio_client._parse_quality("Movie 1080p WEB-DL") == 1080


def test_parse_quality_720p(aio_client):
    """Test quality parsing for 720p"""
    assert aio_client._parse_quality("Movie 720p HDTV") == 720


def test_parse_quality_default(aio_client):
    """Test quality parsing defaults to 480"""
    assert aio_client._parse_quality("Movie DVDRip") == 480


def test_filter_streams_includes_cached_stream_without_video_hash(aio_client):
    """Streams with cached indicator but no videoHash must be included after fix"""
    streams = [
        {
            "name": "    [RD⚡️]\n    4K🔥UHD",
            "description": "    🎬 Shrinking S03 • E04\n    🖥 ᴡᴇʙ-ᴅʟ | 2160p",
            "url": "https://aiostreams.elfhosted.com/playback/test",
            "behaviorHints": {
                "filename": "Shrinking S03E04 The Field 2160p ATVP WEB-DL DDP5 1 DV H 265-NTb.mkv",
                "videoSize": 6697557046,
            },
        }
    ]
    result = aio_client._filter_streams(streams)
    assert len(result) == 1
    assert (
        result[0]["filename"]
        == "Shrinking S03E04 The Field 2160p ATVP WEB-DL DDP5 1 DV H 265-NTb.mkv"
    )


def test_filter_streams_captures_empty_filename_when_absent(aio_client):
    """filename defaults to empty string when behaviorHints has no filename"""
    streams = [
        {
            "name": "[RD+] Movie 1080p",
            "description": "1080p",
            "url": "https://example.com/playback/test",
            "behaviorHints": {"videoHash": "abc123"},
        }
    ]
    result = aio_client._filter_streams(streams)
    assert len(result) == 1
    assert result[0]["filename"] == ""
