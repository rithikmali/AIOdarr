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


def test_collect_failure_appends_to_list():
    """Test collect_failure appends failure to list without sending"""
    webhook_url = "https://discord.com/api/webhooks/123/abc"
    notifier = DiscordNotifier(webhook_url)

    with patch.object(notifier, "_send_webhook") as mock_send:
        notifier.collect_failure(
            media_type="movie",
            title="The Matrix (1999)",
            reason="No cached streams available",
            details={"imdb_id": "tt0133093"},
        )

        # Should NOT send webhook immediately
        mock_send.assert_not_called()

        # Should append to failures list
        assert len(notifier.failures) == 1
        assert notifier.failures[0]["media_type"] == "movie"
        assert notifier.failures[0]["title"] == "The Matrix (1999)"
        assert notifier.failures[0]["reason"] == "No cached streams available"


def test_collect_failure_with_webhook_disabled():
    """Test collect_failure does nothing when webhook is None"""
    notifier = DiscordNotifier(None)

    # Should not raise exception
    notifier.collect_failure(
        media_type="movie",
        title="The Matrix (1999)",
        reason="No cached streams available",
        details={},
    )

    # Failures list should remain empty when webhook disabled
    assert len(notifier.failures) == 0


def test_send_failure_summary_sends_and_clears():
    """Test send_failure_summary sends batched failures and clears list"""
    webhook_url = "https://discord.com/api/webhooks/123/abc"
    notifier = DiscordNotifier(webhook_url)

    # Collect multiple failures
    notifier.collect_failure(
        media_type="movie",
        title="The Matrix (1999)",
        reason="No cached streams available",
        details={"imdb_id": "tt0133093"},
    )
    notifier.collect_failure(
        media_type="episode",
        title="Breaking Bad",
        reason="Quality threshold not met",
        details={"season": 1, "episode": 1, "imdb_id": "tt0959621"},
    )
    notifier.collect_failure(
        media_type="movie",
        title="Inception (2010)",
        reason="No cached streams available",
        details={"imdb_id": "tt1375666"},
    )

    assert len(notifier.failures) == 3

    with patch.object(notifier, "_send_webhook", return_value=True) as mock_send:
        notifier.send_failure_summary()

        # Should send webhook
        mock_send.assert_called_once()
        embed = mock_send.call_args[0][0]

        # Verify embed format
        assert embed["color"] == 0xFF0000  # Red
        assert "Failed to process" in embed["title"]
        assert "3 items" in embed["title"]

        # Verify failures are grouped by media type
        description = embed["description"]
        assert "Movies (2)" in description or "Movie (2)" in description
        assert "The Matrix (1999)" in description
        assert "Inception (2010)" in description
        assert "Episodes (1)" in description or "Episode (1)" in description
        assert "Breaking Bad" in description
        assert "No cached streams available" in description
        assert "Quality threshold not met" in description

    # Verify failures list is cleared after sending
    assert len(notifier.failures) == 0


def test_send_failure_summary_skips_when_empty():
    """Test send_failure_summary does nothing when failures list is empty"""
    webhook_url = "https://discord.com/api/webhooks/123/abc"
    notifier = DiscordNotifier(webhook_url)

    with patch.object(notifier, "_send_webhook") as mock_send:
        notifier.send_failure_summary()

        # Should not send webhook when no failures
        mock_send.assert_not_called()


def test_send_failure_summary_with_webhook_disabled():
    """Test send_failure_summary does nothing when webhook is None"""
    notifier = DiscordNotifier(None)

    # Should not raise exception even if failures were somehow collected
    # (though collect_failure also skips when webhook is None)
    notifier.send_failure_summary()
