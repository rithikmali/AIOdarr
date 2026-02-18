from unittest.mock import Mock, patch

import pytest

from src.clients.realdebrid import RealDebridClient


@pytest.fixture
def rd_client():
    return RealDebridClient("test_api_key")


def test_realdebrid_client_initialization(rd_client):
    """Test Real-Debrid client initializes correctly"""
    assert rd_client.api_key == "test_api_key"
    assert rd_client.base_url == "https://api.real-debrid.com/rest/1.0"
    assert rd_client.headers == {"Authorization": "Bearer test_api_key"}


@patch("requests.post")
@patch("requests.get")
@patch("time.sleep")
def test_add_magnet_with_infohash(mock_sleep, mock_get, mock_post, rd_client):
    """Test adding torrent by infohash"""
    # Mock add magnet response
    add_response = Mock()
    add_response.json.return_value = {"id": "rd_torrent_123"}
    add_response.raise_for_status = Mock()

    # Mock torrent info response
    info_response = Mock()
    info_response.json.return_value = {
        "id": "rd_torrent_123",
        "status": "waiting_files_selection",
        "files": [{"id": 1, "path": "movie.mkv"}, {"id": 2, "path": "sample.mkv"}],
    }
    info_response.raise_for_status = Mock()

    # Mock select files response
    select_response = Mock()
    select_response.raise_for_status = Mock()

    mock_post.side_effect = [add_response, select_response]
    mock_get.return_value = info_response

    torrent_id = rd_client.add_magnet("abc123def456")

    assert torrent_id == "rd_torrent_123"

    # Verify magnet was converted from infohash
    assert mock_post.call_args_list[0][1]["data"]["magnet"].startswith("magnet:?xt=urn:btih:")

    # Verify files were selected
    assert mock_post.call_args_list[1][1]["data"]["files"] == "1,2"


@patch("requests.post")
@patch("requests.get")
@patch("time.sleep")
def test_add_magnet_with_magnet_url(mock_sleep, mock_get, mock_post, rd_client):
    """Test adding torrent with magnet URL"""
    add_response = Mock()
    add_response.json.return_value = {"id": "rd_torrent_123"}
    add_response.raise_for_status = Mock()

    info_response = Mock()
    info_response.json.return_value = {"id": "rd_torrent_123", "status": "downloaded"}
    info_response.raise_for_status = Mock()

    mock_post.return_value = add_response
    mock_get.return_value = info_response

    magnet = "magnet:?xt=urn:btih:abc123"
    torrent_id = rd_client.add_magnet(magnet)

    assert torrent_id == "rd_torrent_123"
    assert mock_post.call_args_list[0][1]["data"]["magnet"] == magnet


@patch("requests.post")
def test_add_magnet_handles_error(mock_post, rd_client):
    """Test add magnet handles errors gracefully"""
    mock_post.side_effect = Exception("API Error")

    torrent_id = rd_client.add_magnet("abc123")

    assert torrent_id is None


@patch("requests.get")
def test_check_torrent_status(mock_get, rd_client):
    """Test checking torrent status"""
    mock_response = Mock()
    mock_response.json.return_value = {"status": "downloaded"}
    mock_response.raise_for_status = Mock()
    mock_get.return_value = mock_response

    status = rd_client.check_torrent_status("rd_torrent_123")

    assert status == "downloaded"
    mock_get.assert_called_once_with(
        "https://api.real-debrid.com/rest/1.0/torrents/info/rd_torrent_123",
        headers={"Authorization": "Bearer test_api_key"},
    )


@patch("requests.get")
def test_list_torrents_returns_torrent_list(mock_get, rd_client):
    """list_torrents returns list of torrent dicts from RD API"""
    mock_response = Mock()
    mock_response.json.return_value = [
        {
            "id": "abc123",
            "filename": "Shrinking S03E04 The Field 2160p ATVP WEB-DL DDP5 1 DV H 265-NTb.mkv",
            "hash": "deadbeef",
            "status": "downloaded",
        },
        {
            "id": "def456",
            "filename": "Breaking Bad S01E01 1080p WEB-DL.mkv",
            "hash": "cafebabe",
            "status": "downloaded",
        },
    ]
    mock_response.raise_for_status = Mock()
    mock_get.return_value = mock_response

    torrents = rd_client.list_torrents()

    assert len(torrents) == 2
    assert (
        torrents[0]["filename"]
        == "Shrinking S03E04 The Field 2160p ATVP WEB-DL DDP5 1 DV H 265-NTb.mkv"
    )
    mock_get.assert_called_once_with(
        "https://api.real-debrid.com/rest/1.0/torrents",
        headers={"Authorization": "Bearer test_api_key"},
    )


@patch("requests.get")
def test_list_torrents_returns_none_on_error(mock_get, rd_client):
    """list_torrents returns None on API error (distinguishes from empty account)"""
    mock_get.side_effect = Exception("API Error")

    torrents = rd_client.list_torrents()

    assert torrents is None
