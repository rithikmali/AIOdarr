from unittest.mock import patch

from src.notifiers.discord import DiscordNotifier


def test_discord_notifier_initialization_with_url():
    """Test DiscordNotifier initializes with webhook URL"""
    webhook_url = "https://discord.com/api/webhooks/123/abc"
    notifier = DiscordNotifier(webhook_url)

    assert notifier.webhook_url == webhook_url
    assert notifier.failures == []


def test_discord_notifier_initialization_with_none():
    """Test DiscordNotifier handles None webhook URL"""
    notifier = DiscordNotifier(None)

    assert notifier.webhook_url is None
    assert notifier.failures == []


def test_notify_success_sends_movie_embed():
    """Test notify_success sends formatted movie embed"""
    webhook_url = "https://discord.com/api/webhooks/123/abc"
    notifier = DiscordNotifier(webhook_url)

    with patch.object(notifier, "_send_webhook", return_value=True) as mock_send:
        notifier.notify_success(
            media_type="movie",
            title="The Matrix (1999)",
            details={
                "year": 1999,
                "imdb_id": "tt0133093",
                "quality": "1080p",
                "stream_title": "The.Matrix.1999.1080p.BluRay",
            },
        )

        mock_send.assert_called_once()
        embed = mock_send.call_args[0][0]

        assert embed["color"] == 0x00FF00  # Green
        assert "✓" in embed["title"]
        assert "The Matrix (1999)" in embed["title"]
        assert any("1080p" in field["value"] for field in embed["fields"])
        assert any("tt0133093" in field["value"] for field in embed["fields"])


def test_notify_success_with_webhook_disabled():
    """Test notify_success does nothing when webhook is None"""
    notifier = DiscordNotifier(None)

    # Should not raise exception
    notifier.notify_success(media_type="movie", title="The Matrix (1999)", details={"year": 1999})


def test_notify_success_sends_episode_embed():
    """Test notify_success sends formatted episode embed with series info"""
    webhook_url = "https://discord.com/api/webhooks/123/abc"
    notifier = DiscordNotifier(webhook_url)

    with patch.object(notifier, "_send_webhook", return_value=True) as mock_send:
        notifier.notify_success(
            media_type="episode",
            title="Breaking Bad",
            details={
                "season": 1,
                "episode": 1,
                "episode_title": "Pilot",
                "imdb_id": "tt0959621",
                "quality": "1080p",
                "stream_title": "Breaking.Bad.S01E01.1080p.WEB",
            },
        )

        mock_send.assert_called_once()
        embed = mock_send.call_args[0][0]

        assert embed["color"] == 0x00FF00  # Green
        assert "✓" in embed["title"]
        assert "Breaking Bad" in embed["title"]
        # Check for episode-specific fields
        assert any("S01E01" in field["value"] for field in embed["fields"])
        assert any("Pilot" in field["value"] for field in embed["fields"])
        assert any("1080p" in field["value"] for field in embed["fields"])
        assert any("tt0959621" in field["value"] for field in embed["fields"])
