from unittest.mock import Mock, patch

from src.config import Config
from src.media_processor import MediaProcessor


@patch("src.media_processor.SonarrClient")
@patch("src.media_processor.RadarrClient")
@patch("src.media_processor.AIOStreamsClient")
def test_media_processor_initializes_notifier_when_webhook_configured(
    mock_aiostreams, mock_radarr, mock_sonarr, monkeypatch
):
    """Test MediaProcessor initializes DiscordNotifier when webhook URL is set"""
    monkeypatch.setenv("AIOSTREAMS_URL", "http://aiostreams")
    monkeypatch.setenv("RADARR_URL", "http://radarr")
    monkeypatch.setenv("RADARR_API_KEY", "test-key")
    monkeypatch.setenv("DISCORD_WEBHOOK_URL", "https://discord.com/api/webhooks/123/abc")

    config = Config()

    with patch("src.media_processor.DiscordNotifier") as mock_notifier_class:
        processor = MediaProcessor(config)

        mock_notifier_class.assert_called_once_with("https://discord.com/api/webhooks/123/abc")
        assert processor.notifier is not None


@patch("src.media_processor.SonarrClient")
@patch("src.media_processor.RadarrClient")
@patch("src.media_processor.AIOStreamsClient")
def test_media_processor_no_notifier_when_webhook_not_configured(
    mock_aiostreams, mock_radarr, mock_sonarr, monkeypatch
):
    """Test MediaProcessor doesn't initialize DiscordNotifier when webhook URL is empty"""
    monkeypatch.setenv("AIOSTREAMS_URL", "http://aiostreams")
    monkeypatch.setenv("RADARR_URL", "http://radarr")
    monkeypatch.setenv("RADARR_API_KEY", "test-key")
    monkeypatch.delenv("DISCORD_WEBHOOK_URL", raising=False)

    config = Config()
    processor = MediaProcessor(config)

    assert processor.notifier is None


@patch("src.media_processor.SonarrClient")
@patch("src.media_processor.RadarrClient")
@patch("src.media_processor.AIOStreamsClient")
def test_process_movie_calls_notify_success(
    mock_aiostreams_class, mock_radarr_class, mock_sonarr, monkeypatch
):
    """Test _process_movie calls notify_success on successful processing"""
    monkeypatch.setenv("AIOSTREAMS_URL", "http://aiostreams")
    monkeypatch.setenv("RADARR_URL", "http://radarr")
    monkeypatch.setenv("RADARR_API_KEY", "test-key")
    monkeypatch.setenv("DISCORD_WEBHOOK_URL", "https://discord.com/api/webhooks/123/abc")

    config = Config()

    # Mock successful movie processing
    mock_radarr = mock_radarr_class.return_value
    mock_radarr.unmonitor_movie.return_value = True

    mock_aiostreams = mock_aiostreams_class.return_value
    mock_aiostreams.search_movie.return_value = [
        {
            "title": "The Matrix 1080p",
            "url": "http://stream-url",
            "description": "1080p WEB-DL",
        }
    ]

    with patch("src.media_processor.DiscordNotifier") as mock_notifier_class:
        mock_notifier = Mock()
        mock_notifier_class.return_value = mock_notifier

        processor = MediaProcessor(config)

        with patch.object(processor, "_trigger_aiostreams_download", return_value=True):
            movie = {
                "id": 1,
                "title": "The Matrix",
                "year": 1999,
                "imdbId": "tt0133093",
            }
            result = processor._process_movie(movie)

            assert result is True
            mock_notifier.notify_success.assert_called_once()

            call_args = mock_notifier.notify_success.call_args
            assert call_args[1]["media_type"] == "movie"
            assert "The Matrix" in call_args[1]["title"]


@patch("src.media_processor.SonarrClient")
@patch("src.media_processor.RadarrClient")
@patch("src.media_processor.AIOStreamsClient")
def test_process_movie_calls_collect_failure_on_no_streams(
    mock_aiostreams_class, mock_radarr_class, mock_sonarr, monkeypatch
):
    """Test _process_movie calls collect_failure when no streams found"""
    monkeypatch.setenv("AIOSTREAMS_URL", "http://aiostreams")
    monkeypatch.setenv("RADARR_URL", "http://radarr")
    monkeypatch.setenv("RADARR_API_KEY", "test-key")
    monkeypatch.setenv("DISCORD_WEBHOOK_URL", "https://discord.com/api/webhooks/123/abc")

    config = Config()

    mock_aiostreams = mock_aiostreams_class.return_value
    mock_aiostreams.search_movie.return_value = []  # No streams

    with patch("src.media_processor.DiscordNotifier") as mock_notifier_class:
        mock_notifier = Mock()
        mock_notifier_class.return_value = mock_notifier

        processor = MediaProcessor(config)

        movie = {
            "id": 1,
            "title": "The Matrix",
            "year": 1999,
            "imdbId": "tt0133093",
        }
        result = processor._process_movie(movie)

        assert result is False
        mock_notifier.collect_failure.assert_called_once()

        call_args = mock_notifier.collect_failure.call_args
        assert call_args[1]["media_type"] == "movie"
        assert "The Matrix" in call_args[1]["title"]
        assert "No cached streams" in call_args[1]["reason"]


@patch("src.media_processor.SonarrClient")
@patch("src.media_processor.RadarrClient")
@patch("src.media_processor.AIOStreamsClient")
def test_process_movie_calls_collect_failure_on_no_imdb(
    mock_aiostreams_class, mock_radarr_class, mock_sonarr, monkeypatch
):
    """Test _process_movie calls collect_failure when no IMDB ID"""
    monkeypatch.setenv("AIOSTREAMS_URL", "http://aiostreams")
    monkeypatch.setenv("RADARR_URL", "http://radarr")
    monkeypatch.setenv("RADARR_API_KEY", "test-key")
    monkeypatch.setenv("DISCORD_WEBHOOK_URL", "https://discord.com/api/webhooks/123/abc")

    config = Config()

    with patch("src.media_processor.DiscordNotifier") as mock_notifier_class:
        mock_notifier = Mock()
        mock_notifier_class.return_value = mock_notifier

        processor = MediaProcessor(config)

        movie = {
            "id": 1,
            "title": "The Matrix",
            "year": 1999,
            "imdbId": "",  # No IMDB ID
        }
        result = processor._process_movie(movie)

        assert result is False
        mock_notifier.collect_failure.assert_called_once()

        call_args = mock_notifier.collect_failure.call_args
        assert "No IMDB ID" in call_args[1]["reason"]


@patch("src.media_processor.SonarrClient")
@patch("src.media_processor.RadarrClient")
@patch("src.media_processor.AIOStreamsClient")
def test_process_movie_calls_collect_failure_on_no_playback_url(
    mock_aiostreams_class, mock_radarr_class, mock_sonarr, monkeypatch
):
    """Test _process_movie calls collect_failure when stream has no URL"""
    monkeypatch.setenv("AIOSTREAMS_URL", "http://aiostreams")
    monkeypatch.setenv("RADARR_URL", "http://radarr")
    monkeypatch.setenv("RADARR_API_KEY", "test-key")
    monkeypatch.setenv("DISCORD_WEBHOOK_URL", "https://discord.com/api/webhooks/123/abc")

    config = Config()

    mock_aiostreams = mock_aiostreams_class.return_value
    mock_aiostreams.search_movie.return_value = [
        {"title": "The Matrix 1080p", "url": "", "description": "1080p"}
    ]

    with patch("src.media_processor.DiscordNotifier") as mock_notifier_class:
        mock_notifier = Mock()
        mock_notifier_class.return_value = mock_notifier

        processor = MediaProcessor(config)

        movie = {
            "id": 1,
            "title": "The Matrix",
            "year": 1999,
            "imdbId": "tt0133093",
        }
        result = processor._process_movie(movie)

        assert result is False
        mock_notifier.collect_failure.assert_called_once()

        call_args = mock_notifier.collect_failure.call_args
        assert "No playback URL" in call_args[1]["reason"]


@patch("src.media_processor.SonarrClient")
@patch("src.media_processor.RadarrClient")
@patch("src.media_processor.AIOStreamsClient")
def test_process_movie_calls_collect_failure_on_download_failed(
    mock_aiostreams_class, mock_radarr_class, mock_sonarr, monkeypatch
):
    """Test _process_movie calls collect_failure when download trigger fails"""
    monkeypatch.setenv("AIOSTREAMS_URL", "http://aiostreams")
    monkeypatch.setenv("RADARR_URL", "http://radarr")
    monkeypatch.setenv("RADARR_API_KEY", "test-key")
    monkeypatch.setenv("DISCORD_WEBHOOK_URL", "https://discord.com/api/webhooks/123/abc")

    config = Config()

    mock_aiostreams = mock_aiostreams_class.return_value
    mock_aiostreams.search_movie.return_value = [
        {"title": "The Matrix 1080p", "url": "http://stream-url", "description": "1080p"}
    ]

    with patch("src.media_processor.DiscordNotifier") as mock_notifier_class:
        mock_notifier = Mock()
        mock_notifier_class.return_value = mock_notifier

        processor = MediaProcessor(config)

        with patch.object(processor, "_trigger_aiostreams_download", return_value=False):
            movie = {
                "id": 1,
                "title": "The Matrix",
                "year": 1999,
                "imdbId": "tt0133093",
            }
            result = processor._process_movie(movie)

            assert result is False
            mock_notifier.collect_failure.assert_called_once()

            call_args = mock_notifier.collect_failure.call_args
            assert "Download trigger failed" in call_args[1]["reason"]


@patch("src.media_processor.SonarrClient")
@patch("src.media_processor.RadarrClient")
@patch("src.media_processor.AIOStreamsClient")
def test_process_episode_calls_notify_success(
    mock_aiostreams_class, mock_radarr, mock_sonarr_class, monkeypatch
):
    """Test _process_episode calls notify_success on successful processing"""
    monkeypatch.setenv("AIOSTREAMS_URL", "http://aiostreams")
    monkeypatch.setenv("SONARR_URL", "http://sonarr")
    monkeypatch.setenv("SONARR_API_KEY", "test-key")
    monkeypatch.setenv("DISCORD_WEBHOOK_URL", "https://discord.com/api/webhooks/123/abc")

    config = Config()

    mock_sonarr = mock_sonarr_class.return_value
    mock_sonarr.unmonitor_episode.return_value = True

    mock_aiostreams = mock_aiostreams_class.return_value
    mock_aiostreams.search_episode.return_value = [
        {
            "title": "Breaking Bad S01E01 1080p",
            "url": "http://stream-url",
            "description": "1080p WEB-DL",
        }
    ]

    with patch("src.media_processor.DiscordNotifier") as mock_notifier_class:
        mock_notifier = Mock()
        mock_notifier_class.return_value = mock_notifier

        processor = MediaProcessor(config)

        with patch.object(processor, "_trigger_aiostreams_download", return_value=True):
            episode = {
                "id": 1,
                "seasonNumber": 1,
                "episodeNumber": 1,
                "title": "Pilot",
                "series": {"title": "Breaking Bad", "imdbId": "tt0959621"},
            }
            result = processor._process_episode(episode)

            assert result is True
            mock_notifier.notify_success.assert_called_once()

            call_args = mock_notifier.notify_success.call_args
            assert call_args[1]["media_type"] == "episode"
            assert "Breaking Bad" in call_args[1]["title"]


@patch("src.media_processor.SonarrClient")
@patch("src.media_processor.RadarrClient")
@patch("src.media_processor.AIOStreamsClient")
def test_process_episode_calls_collect_failure_on_no_streams(
    mock_aiostreams_class, mock_radarr, mock_sonarr_class, monkeypatch
):
    """Test _process_episode calls collect_failure when no streams found"""
    monkeypatch.setenv("AIOSTREAMS_URL", "http://aiostreams")
    monkeypatch.setenv("SONARR_URL", "http://sonarr")
    monkeypatch.setenv("SONARR_API_KEY", "test-key")
    monkeypatch.setenv("DISCORD_WEBHOOK_URL", "https://discord.com/api/webhooks/123/abc")

    config = Config()

    mock_aiostreams = mock_aiostreams_class.return_value
    mock_aiostreams.search_episode.return_value = []  # No streams

    with patch("src.media_processor.DiscordNotifier") as mock_notifier_class:
        mock_notifier = Mock()
        mock_notifier_class.return_value = mock_notifier

        processor = MediaProcessor(config)

        episode = {
            "id": 1,
            "seasonNumber": 1,
            "episodeNumber": 1,
            "title": "Pilot",
            "series": {"title": "Breaking Bad", "imdbId": "tt0959621"},
        }
        result = processor._process_episode(episode)

        assert result is False
        mock_notifier.collect_failure.assert_called_once()

        call_args = mock_notifier.collect_failure.call_args
        assert call_args[1]["media_type"] == "episode"
        assert "Breaking Bad" in call_args[1]["title"]
        assert "No cached streams" in call_args[1]["reason"]


@patch("src.media_processor.SonarrClient")
@patch("src.media_processor.RadarrClient")
@patch("src.media_processor.AIOStreamsClient")
def test_process_episode_calls_collect_failure_on_no_ids(
    mock_aiostreams_class, mock_radarr, mock_sonarr_class, monkeypatch
):
    """Test _process_episode calls collect_failure when no IMDB/TVDB ID"""
    monkeypatch.setenv("AIOSTREAMS_URL", "http://aiostreams")
    monkeypatch.setenv("SONARR_URL", "http://sonarr")
    monkeypatch.setenv("SONARR_API_KEY", "test-key")
    monkeypatch.setenv("DISCORD_WEBHOOK_URL", "https://discord.com/api/webhooks/123/abc")

    config = Config()

    with patch("src.media_processor.DiscordNotifier") as mock_notifier_class:
        mock_notifier = Mock()
        mock_notifier_class.return_value = mock_notifier

        processor = MediaProcessor(config)

        episode = {
            "id": 1,
            "seasonNumber": 1,
            "episodeNumber": 1,
            "title": "Pilot",
            "series": {"title": "Breaking Bad", "imdbId": "", "tvdbId": ""},
        }
        result = processor._process_episode(episode)

        assert result is False
        mock_notifier.collect_failure.assert_called_once()

        call_args = mock_notifier.collect_failure.call_args
        assert "No IMDB/TVDB ID" in call_args[1]["reason"]


@patch("src.media_processor.SonarrClient")
@patch("src.media_processor.RadarrClient")
@patch("src.media_processor.AIOStreamsClient")
def test_process_episode_calls_collect_failure_on_no_playback_url(
    mock_aiostreams_class, mock_radarr, mock_sonarr_class, monkeypatch
):
    """Test _process_episode calls collect_failure when stream has no URL"""
    monkeypatch.setenv("AIOSTREAMS_URL", "http://aiostreams")
    monkeypatch.setenv("SONARR_URL", "http://sonarr")
    monkeypatch.setenv("SONARR_API_KEY", "test-key")
    monkeypatch.setenv("DISCORD_WEBHOOK_URL", "https://discord.com/api/webhooks/123/abc")

    config = Config()

    mock_aiostreams = mock_aiostreams_class.return_value
    mock_aiostreams.search_episode.return_value = [
        {"title": "Breaking Bad S01E01", "url": "", "description": "1080p"}
    ]

    with patch("src.media_processor.DiscordNotifier") as mock_notifier_class:
        mock_notifier = Mock()
        mock_notifier_class.return_value = mock_notifier

        processor = MediaProcessor(config)

        episode = {
            "id": 1,
            "seasonNumber": 1,
            "episodeNumber": 1,
            "title": "Pilot",
            "series": {"title": "Breaking Bad", "imdbId": "tt0959621"},
        }
        result = processor._process_episode(episode)

        assert result is False
        mock_notifier.collect_failure.assert_called_once()

        call_args = mock_notifier.collect_failure.call_args
        assert "No playback URL" in call_args[1]["reason"]


@patch("src.media_processor.SonarrClient")
@patch("src.media_processor.RadarrClient")
@patch("src.media_processor.AIOStreamsClient")
def test_process_episode_calls_collect_failure_on_download_failed(
    mock_aiostreams_class, mock_radarr, mock_sonarr_class, monkeypatch
):
    """Test _process_episode calls collect_failure when download trigger fails"""
    monkeypatch.setenv("AIOSTREAMS_URL", "http://aiostreams")
    monkeypatch.setenv("SONARR_URL", "http://sonarr")
    monkeypatch.setenv("SONARR_API_KEY", "test-key")
    monkeypatch.setenv("DISCORD_WEBHOOK_URL", "https://discord.com/api/webhooks/123/abc")

    config = Config()

    mock_aiostreams = mock_aiostreams_class.return_value
    mock_aiostreams.search_episode.return_value = [
        {"title": "Breaking Bad S01E01", "url": "http://stream-url", "description": "1080p"}
    ]

    with patch("src.media_processor.DiscordNotifier") as mock_notifier_class:
        mock_notifier = Mock()
        mock_notifier_class.return_value = mock_notifier

        processor = MediaProcessor(config)

        with patch.object(processor, "_trigger_aiostreams_download", return_value=False):
            episode = {
                "id": 1,
                "seasonNumber": 1,
                "episodeNumber": 1,
                "title": "Pilot",
                "series": {"title": "Breaking Bad", "imdbId": "tt0959621"},
            }
            result = processor._process_episode(episode)

            assert result is False
            mock_notifier.collect_failure.assert_called_once()

            call_args = mock_notifier.collect_failure.call_args
            assert "Download trigger failed" in call_args[1]["reason"]


@patch("src.media_processor.SonarrClient")
@patch("src.media_processor.RadarrClient")
@patch("src.media_processor.AIOStreamsClient")
def test_process_all_calls_send_failure_summary(
    mock_aiostreams, mock_radarr_class, mock_sonarr, monkeypatch
):
    """Test process_all calls send_failure_summary at end of cycle"""
    monkeypatch.setenv("AIOSTREAMS_URL", "http://aiostreams")
    monkeypatch.setenv("RADARR_URL", "http://radarr")
    monkeypatch.setenv("RADARR_API_KEY", "test-key")
    monkeypatch.setenv("DISCORD_WEBHOOK_URL", "https://discord.com/api/webhooks/123/abc")

    config = Config()

    mock_radarr = mock_radarr_class.return_value
    mock_radarr.get_wanted_movies.return_value = []

    with patch("src.media_processor.DiscordNotifier") as mock_notifier_class:
        mock_notifier = Mock()
        mock_notifier_class.return_value = mock_notifier

        processor = MediaProcessor(config)
        processor.process_all()

        mock_notifier.send_failure_summary.assert_called_once()


@patch("src.media_processor.SonarrClient")
@patch("src.media_processor.RadarrClient")
@patch("src.media_processor.AIOStreamsClient")
def test_process_all_no_failure_summary_without_notifier(
    mock_aiostreams, mock_radarr_class, mock_sonarr, monkeypatch
):
    """Test process_all doesn't crash when notifier is None"""
    monkeypatch.setenv("AIOSTREAMS_URL", "http://aiostreams")
    monkeypatch.setenv("RADARR_URL", "http://radarr")
    monkeypatch.setenv("RADARR_API_KEY", "test-key")
    monkeypatch.delenv("DISCORD_WEBHOOK_URL", raising=False)

    config = Config()

    mock_radarr = mock_radarr_class.return_value
    mock_radarr.get_wanted_movies.return_value = []

    processor = MediaProcessor(config)
    # Should not raise an exception
    processor.process_all()

    assert processor.notifier is None
