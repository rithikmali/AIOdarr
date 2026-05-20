from unittest.mock import Mock, patch

from src.clients.torbox import TorBoxClient


@patch("requests.get")
def test_list_torrents_returns_data_list(mock_get):
    client = TorBoxClient("test_api_key")
    mock_response = Mock()
    mock_response.raise_for_status.return_value = None
    mock_response.json.return_value = {
        "success": True,
        "data": [{"id": 123, "name": "Movie.2024.2160p.mkv"}],
    }
    mock_get.return_value = mock_response

    torrents = client.list_torrents()

    assert torrents == [{"id": 123, "name": "Movie.2024.2160p.mkv"}]


@patch("requests.get")
def test_list_torrents_returns_none_on_api_failure(mock_get):
    client = TorBoxClient("test_api_key")
    mock_response = Mock()
    mock_response.raise_for_status.return_value = None
    mock_response.json.return_value = {"success": False, "error": "bad token"}
    mock_get.return_value = mock_response

    torrents = client.list_torrents()

    assert torrents is None


@patch("requests.post")
def test_delete_torrent_returns_true_on_success(mock_post):
    client = TorBoxClient("test_api_key")
    mock_response = Mock()
    mock_response.raise_for_status.return_value = None
    mock_post.return_value = mock_response

    result = client.delete_torrent(123)

    assert result is True
