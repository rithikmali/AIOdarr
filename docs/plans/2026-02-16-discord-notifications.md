# Discord Notifications Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add Discord webhook notifications for successful/failed media processing in AIODarr

**Architecture:** Create DiscordNotifier abstraction layer that MediaProcessor uses to send immediate success notifications and batched failure summaries. Webhook is optional and failures never block media processing.

**Tech Stack:** Python 3.11+, requests library, Discord webhook API, pytest with unittest.mock

---

## Task 1: Add Discord Webhook URL to Config

**Files:**
- Modify: `src/config.py:31`
- Test: `tests/test_config.py`

**Step 1: Write the failing test**

Add to `tests/test_config.py`:

```python
def test_discord_webhook_url_loads_when_set(monkeypatch):
    """Test Discord webhook URL loads from environment"""
    monkeypatch.setenv("AIOSTREAMS_URL", "http://aiostreams")
    monkeypatch.setenv("RADARR_URL", "http://radarr")
    monkeypatch.setenv("RADARR_API_KEY", "test-key")
    monkeypatch.setenv("DISCORD_WEBHOOK_URL", "https://discord.com/api/webhooks/123/abc")

    config = Config()
    assert config.discord_webhook_url == "https://discord.com/api/webhooks/123/abc"


def test_discord_webhook_url_defaults_to_empty_string(monkeypatch):
    """Test Discord webhook URL defaults to empty string when not set"""
    monkeypatch.setenv("AIOSTREAMS_URL", "http://aiostreams")
    monkeypatch.setenv("RADARR_URL", "http://radarr")
    monkeypatch.setenv("RADARR_API_KEY", "test-key")
    monkeypatch.delenv("DISCORD_WEBHOOK_URL", raising=False)

    config = Config()
    assert config.discord_webhook_url == ""
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_config.py::test_discord_webhook_url_loads_when_set -v`

Expected: FAIL with "AttributeError: 'Config' object has no attribute 'discord_webhook_url'"

**Step 3: Write minimal implementation**

In `src/config.py`, add after line 30 (after `retry_failed_hours`):

```python
self.discord_webhook_url = os.getenv("DISCORD_WEBHOOK_URL", "")
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_config.py::test_discord_webhook_url_loads_when_set tests/test_config.py::test_discord_webhook_url_defaults_to_empty_string -v`

Expected: PASS (both tests)

**Step 5: Commit**

```bash
git add src/config.py tests/test_config.py
git commit -m "feat: add DISCORD_WEBHOOK_URL config option"
```

---

## Task 2: Create DiscordNotifier Class Structure

**Files:**
- Create: `src/notifiers/__init__.py`
- Create: `src/notifiers/discord.py`
- Create: `tests/test_discord_notifier.py`

**Step 1: Write the failing test**

Create `tests/test_discord_notifier.py`:

```python
import pytest
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
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_discord_notifier.py::test_discord_notifier_initialization_with_url -v`

Expected: FAIL with "ModuleNotFoundError: No module named 'src.notifiers'"

**Step 3: Write minimal implementation**

Create `src/notifiers/__init__.py` (empty file):

```python
"""Notification integrations for AIODarr"""
```

Create `src/notifiers/discord.py`:

```python
import logging
from typing import Any

logger = logging.getLogger(__name__)


class DiscordNotifier:
    """Discord webhook notifier for media processing events"""

    def __init__(self, webhook_url: str | None):
        """
        Initialize Discord notifier

        Args:
            webhook_url: Discord webhook URL (None to disable notifications)
        """
        self.webhook_url = webhook_url
        self.failures: list[dict[str, Any]] = []
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_discord_notifier.py::test_discord_notifier_initialization_with_url tests/test_discord_notifier.py::test_discord_notifier_initialization_with_none -v`

Expected: PASS (both tests)

**Step 5: Commit**

```bash
git add src/notifiers/__init__.py src/notifiers/discord.py tests/test_discord_notifier.py
git commit -m "feat: create DiscordNotifier class structure"
```

---

## Task 3: Implement notify_success for Movies

**Files:**
- Modify: `src/notifiers/discord.py`
- Modify: `tests/test_discord_notifier.py`

**Step 1: Write the failing test**

Add to `tests/test_discord_notifier.py`:

```python
from unittest.mock import patch, MagicMock


def test_notify_success_sends_movie_embed():
    """Test notify_success sends formatted movie embed"""
    webhook_url = "https://discord.com/api/webhooks/123/abc"
    notifier = DiscordNotifier(webhook_url)

    with patch.object(notifier, '_send_webhook', return_value=True) as mock_send:
        notifier.notify_success(
            media_type="movie",
            title="The Matrix (1999)",
            details={
                "year": 1999,
                "imdb_id": "tt0133093",
                "quality": "1080p",
                "stream_title": "The.Matrix.1999.1080p.BluRay"
            }
        )

        mock_send.assert_called_once()
        embed = mock_send.call_args[0][0]

        assert embed["color"] == 0x00ff00  # Green
        assert "✓" in embed["title"]
        assert "The Matrix (1999)" in embed["title"]
        assert any("1080p" in field["value"] for field in embed["fields"])
        assert any("tt0133093" in field["value"] for field in embed["fields"])


def test_notify_success_with_webhook_disabled():
    """Test notify_success does nothing when webhook is None"""
    notifier = DiscordNotifier(None)

    # Should not raise exception
    notifier.notify_success(
        media_type="movie",
        title="The Matrix (1999)",
        details={"year": 1999}
    )
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_discord_notifier.py::test_notify_success_sends_movie_embed -v`

Expected: FAIL with "AttributeError: 'DiscordNotifier' object has no attribute 'notify_success'"

**Step 3: Write minimal implementation**

Add to `src/notifiers/discord.py`:

```python
from datetime import datetime


def notify_success(self, media_type: str, title: str, details: dict[str, Any]) -> None:
    """
    Send immediate success notification to Discord

    Args:
        media_type: Type of media ("movie" or "episode")
        title: Media title
        details: Additional details (year, quality, imdb_id, etc.)
    """
    if not self.webhook_url:
        return

    embed = self._format_success_embed(media_type, title, details)
    success = self._send_webhook(embed)
    if success:
        logger.info(f"Sent Discord notification for {media_type}: {title}")


def _format_success_embed(self, media_type: str, title: str, details: dict[str, Any]) -> dict[str, Any]:
    """
    Format success notification as Discord embed

    Args:
        media_type: Type of media ("movie" or "episode")
        title: Media title
        details: Additional details

    Returns:
        Discord embed dict
    """
    embed = {
        "title": f"✓ Successfully Added {media_type.title()}",
        "description": title,
        "color": 0x00ff00,  # Green
        "fields": [],
        "timestamp": datetime.utcnow().isoformat()
    }

    # Add quality if available
    if quality := details.get("quality"):
        embed["fields"].append({
            "name": "Quality",
            "value": quality,
            "inline": True
        })

    # Add IMDB ID if available
    if imdb_id := details.get("imdb_id"):
        embed["fields"].append({
            "name": "IMDB",
            "value": imdb_id,
            "inline": True
        })

    # Add stream title if available
    if stream_title := details.get("stream_title"):
        embed["fields"].append({
            "name": "Stream",
            "value": stream_title,
            "inline": False
        })

    return embed


def _send_webhook(self, embed: dict[str, Any]) -> bool:
    """
    Send embed to Discord webhook

    Args:
        embed: Discord embed dict

    Returns:
        True if successful, False otherwise
    """
    # Placeholder - will implement in later task
    return True
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_discord_notifier.py::test_notify_success_sends_movie_embed tests/test_discord_notifier.py::test_notify_success_with_webhook_disabled -v`

Expected: PASS (both tests)

**Step 5: Commit**

```bash
git add src/notifiers/discord.py tests/test_discord_notifier.py
git commit -m "feat: implement notify_success for movies"
```

---

## Task 4: Implement notify_success for Episodes

**Files:**
- Modify: `src/notifiers/discord.py`
- Modify: `tests/test_discord_notifier.py`

**Step 1: Write the failing test**

Add to `tests/test_discord_notifier.py`:

```python
def test_notify_success_sends_episode_embed():
    """Test notify_success sends formatted episode embed"""
    webhook_url = "https://discord.com/api/webhooks/123/abc"
    notifier = DiscordNotifier(webhook_url)

    with patch.object(notifier, '_send_webhook', return_value=True) as mock_send:
        notifier.notify_success(
            media_type="episode",
            title="Breaking Bad S01E01 - Pilot",
            details={
                "series_title": "Breaking Bad",
                "season": 1,
                "episode_number": 1,
                "imdb_id": "tt0959621",
                "quality": "1080p",
                "stream_title": "Breaking.Bad.S01E01.1080p.WEB"
            }
        )

        mock_send.assert_called_once()
        embed = mock_send.call_args[0][0]

        assert embed["color"] == 0x00ff00  # Green
        assert "✓" in embed["title"]
        assert "Breaking Bad S01E01" in embed["title"] or "Pilot" in embed["description"]
        assert any("1080p" in field["value"] for field in embed["fields"])
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_discord_notifier.py::test_notify_success_sends_episode_embed -v`

Expected: PASS (current implementation already handles episodes generically)

Note: If test passes immediately, that's fine - the generic implementation works for both.

**Step 3: Enhance implementation for episodes (if needed)**

In `src/notifiers/discord.py`, update `_format_success_embed` to add episode-specific fields:

```python
def _format_success_embed(self, media_type: str, title: str, details: dict[str, Any]) -> dict[str, Any]:
    """
    Format success notification as Discord embed

    Args:
        media_type: Type of media ("movie" or "episode")
        title: Media title
        details: Additional details

    Returns:
        Discord embed dict
    """
    embed = {
        "title": f"✓ Successfully Added {media_type.title()}",
        "description": title,
        "color": 0x00ff00,  # Green
        "fields": [],
        "timestamp": datetime.utcnow().isoformat()
    }

    # Add episode-specific info
    if media_type == "episode":
        if series_title := details.get("series_title"):
            season = details.get("season", "?")
            episode = details.get("episode_number", "?")
            embed["fields"].append({
                "name": "Series",
                "value": f"{series_title} S{season:02d}E{episode:02d}" if isinstance(season, int) else series_title,
                "inline": True
            })

    # Add movie-specific info
    if media_type == "movie":
        if year := details.get("year"):
            embed["fields"].append({
                "name": "Year",
                "value": str(year),
                "inline": True
            })

    # Add quality if available
    if quality := details.get("quality"):
        embed["fields"].append({
            "name": "Quality",
            "value": quality,
            "inline": True
        })

    # Add IMDB ID if available
    if imdb_id := details.get("imdb_id"):
        embed["fields"].append({
            "name": "IMDB",
            "value": imdb_id,
            "inline": True
        })

    # Add stream title if available
    if stream_title := details.get("stream_title"):
        embed["fields"].append({
            "name": "Stream",
            "value": stream_title,
            "inline": False
        })

    return embed
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_discord_notifier.py::test_notify_success_sends_episode_embed -v`

Expected: PASS

**Step 5: Commit**

```bash
git add src/notifiers/discord.py tests/test_discord_notifier.py
git commit -m "feat: enhance notify_success for episodes with series info"
```

---

## Task 5: Implement collect_failure

**Files:**
- Modify: `src/notifiers/discord.py`
- Modify: `tests/test_discord_notifier.py`

**Step 1: Write the failing test**

Add to `tests/test_discord_notifier.py`:

```python
def test_collect_failure_appends_to_list():
    """Test collect_failure appends failure to list without sending"""
    webhook_url = "https://discord.com/api/webhooks/123/abc"
    notifier = DiscordNotifier(webhook_url)

    with patch.object(notifier, '_send_webhook') as mock_send:
        notifier.collect_failure(
            media_type="movie",
            title="The Matrix (1999)",
            reason="No cached streams available",
            details={"imdb_id": "tt0133093"}
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
        details={}
    )

    # Failures list should remain empty when webhook disabled
    assert len(notifier.failures) == 0
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_discord_notifier.py::test_collect_failure_appends_to_list -v`

Expected: FAIL with "AttributeError: 'DiscordNotifier' object has no attribute 'collect_failure'"

**Step 3: Write minimal implementation**

Add to `src/notifiers/discord.py`:

```python
def collect_failure(
    self, media_type: str, title: str, reason: str, details: dict[str, Any]
) -> None:
    """
    Collect failure for batched summary notification

    Args:
        media_type: Type of media ("movie" or "episode")
        title: Media title
        reason: Failure reason
        details: Additional details
    """
    if not self.webhook_url:
        return

    self.failures.append({
        "media_type": media_type,
        "title": title,
        "reason": reason,
        "details": details
    })
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_discord_notifier.py::test_collect_failure_appends_to_list tests/test_discord_notifier.py::test_collect_failure_with_webhook_disabled -v`

Expected: PASS (both tests)

**Step 5: Commit**

```bash
git add src/notifiers/discord.py tests/test_discord_notifier.py
git commit -m "feat: implement collect_failure for batched notifications"
```

---

## Task 6: Implement send_failure_summary

**Files:**
- Modify: `src/notifiers/discord.py`
- Modify: `tests/test_discord_notifier.py`

**Step 1: Write the failing test**

Add to `tests/test_discord_notifier.py`:

```python
def test_send_failure_summary_sends_and_clears():
    """Test send_failure_summary sends embed and clears list"""
    webhook_url = "https://discord.com/api/webhooks/123/abc"
    notifier = DiscordNotifier(webhook_url)

    # Add some failures
    notifier.failures = [
        {"media_type": "movie", "title": "Movie 1", "reason": "No streams", "details": {}},
        {"media_type": "episode", "title": "Show S01E01", "reason": "No IMDB ID", "details": {}}
    ]

    with patch.object(notifier, '_send_webhook', return_value=True) as mock_send:
        notifier.send_failure_summary()

        mock_send.assert_called_once()
        embed = mock_send.call_args[0][0]

        assert embed["color"] == 0xff0000  # Red
        assert "✗" in embed["title"] or "Failed" in embed["title"]
        assert "2" in embed["description"] or "2" in embed["title"]

    # Failures list should be cleared
    assert len(notifier.failures) == 0


def test_send_failure_summary_skips_when_empty():
    """Test send_failure_summary skips when no failures"""
    webhook_url = "https://discord.com/api/webhooks/123/abc"
    notifier = DiscordNotifier(webhook_url)

    with patch.object(notifier, '_send_webhook') as mock_send:
        notifier.send_failure_summary()

        # Should not send when list is empty
        mock_send.assert_not_called()


def test_send_failure_summary_with_webhook_disabled():
    """Test send_failure_summary does nothing when webhook is None"""
    notifier = DiscordNotifier(None)
    notifier.failures = [{"media_type": "movie", "title": "Movie 1", "reason": "test", "details": {}}]

    # Should not raise exception
    notifier.send_failure_summary()
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_discord_notifier.py::test_send_failure_summary_sends_and_clears -v`

Expected: FAIL with "AttributeError: 'DiscordNotifier' object has no attribute 'send_failure_summary'"

**Step 3: Write minimal implementation**

Add to `src/notifiers/discord.py`:

```python
def send_failure_summary(self) -> None:
    """Send batched failure summary notification and clear failures list"""
    if not self.webhook_url or not self.failures:
        return

    embed = self._format_failure_summary_embed(self.failures)
    success = self._send_webhook(embed)
    if success:
        logger.info(f"Sent Discord failure summary ({len(self.failures)} items)")

    # Clear failures list
    self.failures = []


def _format_failure_summary_embed(self, failures: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Format failure summary as Discord embed

    Args:
        failures: List of failure dicts

    Returns:
        Discord embed dict
    """
    count = len(failures)
    embed = {
        "title": f"✗ Failed to Process {count} Item{'s' if count != 1 else ''}",
        "description": "The following media could not be added:",
        "color": 0xff0000,  # Red
        "fields": [],
        "timestamp": datetime.utcnow().isoformat()
    }

    # Group by media type
    movies = [f for f in failures if f["media_type"] == "movie"]
    episodes = [f for f in failures if f["media_type"] == "episode"]

    # Add movie failures
    if movies:
        movie_text = "\n".join([
            f"• **{f['title']}**: {f['reason']}" for f in movies
        ])
        embed["fields"].append({
            "name": f"Movies ({len(movies)})",
            "value": movie_text,
            "inline": False
        })

    # Add episode failures
    if episodes:
        episode_text = "\n".join([
            f"• **{f['title']}**: {f['reason']}" for f in episodes
        ])
        embed["fields"].append({
            "name": f"Episodes ({len(episodes)})",
            "value": episode_text,
            "inline": False
        })

    return embed
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_discord_notifier.py::test_send_failure_summary_sends_and_clears tests/test_discord_notifier.py::test_send_failure_summary_skips_when_empty tests/test_discord_notifier.py::test_send_failure_summary_with_webhook_disabled -v`

Expected: PASS (all three tests)

**Step 5: Commit**

```bash
git add src/notifiers/discord.py tests/test_discord_notifier.py
git commit -m "feat: implement send_failure_summary with batched failures"
```

---

## Task 7: Implement _send_webhook with Error Handling

**Files:**
- Modify: `src/notifiers/discord.py`
- Modify: `tests/test_discord_notifier.py`

**Step 1: Write the failing test**

Add to `tests/test_discord_notifier.py`:

```python
@patch("requests.post")
def test_send_webhook_success(mock_post):
    """Test _send_webhook successfully sends to Discord"""
    mock_response = MagicMock()
    mock_response.status_code = 204
    mock_post.return_value = mock_response

    webhook_url = "https://discord.com/api/webhooks/123/abc"
    notifier = DiscordNotifier(webhook_url)

    embed = {"title": "Test", "color": 0x00ff00}
    result = notifier._send_webhook(embed)

    assert result is True
    mock_post.assert_called_once_with(
        webhook_url,
        json={"embeds": [embed]},
        timeout=10
    )


@patch("requests.post")
def test_send_webhook_handles_http_error(mock_post):
    """Test _send_webhook handles HTTP errors gracefully"""
    mock_post.side_effect = Exception("HTTP 404: Not Found")

    webhook_url = "https://discord.com/api/webhooks/123/abc"
    notifier = DiscordNotifier(webhook_url)

    embed = {"title": "Test", "color": 0x00ff00}
    result = notifier._send_webhook(embed)

    # Should return False and not raise exception
    assert result is False


@patch("requests.post")
def test_send_webhook_handles_network_error(mock_post):
    """Test _send_webhook handles network errors gracefully"""
    mock_post.side_effect = ConnectionError("Network unreachable")

    webhook_url = "https://discord.com/api/webhooks/123/abc"
    notifier = DiscordNotifier(webhook_url)

    embed = {"title": "Test", "color": 0x00ff00}
    result = notifier._send_webhook(embed)

    # Should return False and not raise exception
    assert result is False
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_discord_notifier.py::test_send_webhook_success -v`

Expected: FAIL with "ImportError: cannot import name 'post'" or actual HTTP call attempt

**Step 3: Write minimal implementation**

Update `_send_webhook` in `src/notifiers/discord.py`:

```python
import requests


def _send_webhook(self, embed: dict[str, Any]) -> bool:
    """
    Send embed to Discord webhook

    Args:
        embed: Discord embed dict

    Returns:
        True if successful, False otherwise
    """
    if not self.webhook_url:
        return False

    try:
        response = requests.post(
            self.webhook_url,
            json={"embeds": [embed]},
            timeout=10
        )
        response.raise_for_status()
        logger.debug(f"Discord webhook sent successfully")
        return True
    except Exception as e:
        logger.warning(f"Failed to send Discord webhook: {e}")
        return False
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_discord_notifier.py::test_send_webhook_success tests/test_discord_notifier.py::test_send_webhook_handles_http_error tests/test_discord_notifier.py::test_send_webhook_handles_network_error -v`

Expected: PASS (all three tests)

**Step 5: Commit**

```bash
git add src/notifiers/discord.py tests/test_discord_notifier.py
git commit -m "feat: implement _send_webhook with error handling"
```

---

## Task 8: Test Embed Truncation for Long Failure Lists

**Files:**
- Modify: `src/notifiers/discord.py`
- Modify: `tests/test_discord_notifier.py`

**Step 1: Write the failing test**

Add to `tests/test_discord_notifier.py`:

```python
def test_send_failure_summary_truncates_long_lists():
    """Test send_failure_summary truncates when exceeding Discord limits"""
    webhook_url = "https://discord.com/api/webhooks/123/abc"
    notifier = DiscordNotifier(webhook_url)

    # Create many failures to exceed character limit
    notifier.failures = [
        {
            "media_type": "movie",
            "title": f"Very Long Movie Title That Takes Up Space {i} (2024)",
            "reason": "No cached streams available for this specific movie title",
            "details": {}
        }
        for i in range(100)
    ]

    with patch.object(notifier, '_send_webhook', return_value=True) as mock_send:
        notifier.send_failure_summary()

        mock_send.assert_called_once()
        embed = mock_send.call_args[0][0]

        # Calculate total embed size
        embed_str = str(embed)
        assert len(embed_str) < 6000, "Embed should be under Discord 6000 char limit"

        # Should mention truncation
        assert any("more" in str(field.get("value", "")).lower() for field in embed.get("fields", []))
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_discord_notifier.py::test_send_failure_summary_truncates_long_lists -v`

Expected: FAIL with assertion about embed size or missing truncation message

**Step 3: Write minimal implementation**

Update `_format_failure_summary_embed` in `src/notifiers/discord.py`:

```python
def _format_failure_summary_embed(self, failures: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Format failure summary as Discord embed

    Args:
        failures: List of failure dicts

    Returns:
        Discord embed dict
    """
    count = len(failures)
    embed = {
        "title": f"✗ Failed to Process {count} Item{'s' if count != 1 else ''}",
        "description": "The following media could not be added:",
        "color": 0xff0000,  # Red
        "fields": [],
        "timestamp": datetime.utcnow().isoformat()
    }

    # Group by media type
    movies = [f for f in failures if f["media_type"] == "movie"]
    episodes = [f for f in failures if f["media_type"] == "episode"]

    # Add movie failures (with truncation)
    if movies:
        movie_lines = [f"• **{f['title']}**: {f['reason']}" for f in movies]
        movie_text = "\n".join(movie_lines)

        # Truncate if too long (Discord field limit is 1024 chars)
        if len(movie_text) > 1000:
            truncated_lines = []
            current_length = 0
            shown_count = 0

            for line in movie_lines:
                if current_length + len(line) + 1 < 900:  # Leave room for truncation message
                    truncated_lines.append(line)
                    current_length += len(line) + 1
                    shown_count += 1
                else:
                    break

            remaining = len(movies) - shown_count
            truncated_lines.append(f"\n... and {remaining} more movies")
            movie_text = "\n".join(truncated_lines)

        embed["fields"].append({
            "name": f"Movies ({len(movies)})",
            "value": movie_text,
            "inline": False
        })

    # Add episode failures (with truncation)
    if episodes:
        episode_lines = [f"• **{f['title']}**: {f['reason']}" for f in episodes]
        episode_text = "\n".join(episode_lines)

        # Truncate if too long
        if len(episode_text) > 1000:
            truncated_lines = []
            current_length = 0
            shown_count = 0

            for line in episode_lines:
                if current_length + len(line) + 1 < 900:
                    truncated_lines.append(line)
                    current_length += len(line) + 1
                    shown_count += 1
                else:
                    break

            remaining = len(episodes) - shown_count
            truncated_lines.append(f"\n... and {remaining} more episodes")
            episode_text = "\n".join(truncated_lines)

        embed["fields"].append({
            "name": f"Episodes ({len(episodes)})",
            "value": episode_text,
            "inline": False
        })

    return embed
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_discord_notifier.py::test_send_failure_summary_truncates_long_lists -v`

Expected: PASS

**Step 5: Commit**

```bash
git add src/notifiers/discord.py tests/test_discord_notifier.py
git commit -m "feat: add embed truncation for long failure lists"
```

---

## Task 9: Integrate DiscordNotifier into MediaProcessor

**Files:**
- Modify: `src/media_processor.py:16-30`
- Modify: `tests/test_media_processor.py`

**Step 1: Write the failing test**

Check if `tests/test_media_processor.py` exists. If not, create it. Add:

```python
from unittest.mock import Mock, patch
import pytest
from src.media_processor import MediaProcessor
from src.config import Config


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
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_media_processor.py::test_media_processor_initializes_notifier_when_webhook_configured -v`

Expected: FAIL with "AttributeError: 'MediaProcessor' object has no attribute 'notifier'"

**Step 3: Write minimal implementation**

In `src/media_processor.py`, add import at top:

```python
from src.notifiers.discord import DiscordNotifier
```

In `MediaProcessor.__init__`, add after line 30 (after Sonarr initialization):

```python
# Initialize Discord notifier if webhook URL is configured
self.notifier: DiscordNotifier | None = None
if config.discord_webhook_url:
    self.notifier = DiscordNotifier(config.discord_webhook_url)
    logger.info("Discord notifier initialized")
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_media_processor.py::test_media_processor_initializes_notifier_when_webhook_configured tests/test_media_processor.py::test_media_processor_no_notifier_when_webhook_not_configured -v`

Expected: PASS (both tests)

**Step 5: Commit**

```bash
git add src/media_processor.py tests/test_media_processor.py
git commit -m "feat: integrate DiscordNotifier into MediaProcessor"
```

---

## Task 10: Add Success Notifications to _process_movie

**Files:**
- Modify: `src/media_processor.py:120-127`
- Modify: `tests/test_media_processor.py`

**Step 1: Write the failing test**

Add to `tests/test_media_processor.py`:

```python
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
    mock_aiostreams.search_movie.return_value = [{
        "title": "The Matrix 1080p",
        "url": "http://stream-url",
        "description": "1080p WEB-DL"
    }]

    with patch("src.media_processor.DiscordNotifier") as mock_notifier_class:
        mock_notifier = Mock()
        mock_notifier_class.return_value = mock_notifier

        processor = MediaProcessor(config)

        with patch.object(processor, '_trigger_aiostreams_download', return_value=True):
            movie = {
                "id": 1,
                "title": "The Matrix",
                "year": 1999,
                "imdbId": "tt0133093"
            }
            result = processor._process_movie(movie)

            assert result is True
            mock_notifier.notify_success.assert_called_once()

            call_args = mock_notifier.notify_success.call_args
            assert call_args[1]["media_type"] == "movie"
            assert "The Matrix" in call_args[1]["title"]
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_media_processor.py::test_process_movie_calls_notify_success -v`

Expected: FAIL with "AssertionError: Expected 'notify_success' to have been called once."

**Step 3: Write minimal implementation**

In `src/media_processor.py`, in `_process_movie` method, add after line 125 (after successful trigger and unmonitor):

```python
# Notify Discord of success
if self.notifier:
    self.notifier.notify_success(
        media_type="movie",
        title=f"{title} ({year})",
        details={
            "year": year,
            "imdb_id": imdb_id,
            "quality": stream.get("description", "Unknown"),
            "stream_title": stream.get("title", "")
        }
    )
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_media_processor.py::test_process_movie_calls_notify_success -v`

Expected: PASS

**Step 5: Commit**

```bash
git add src/media_processor.py tests/test_media_processor.py
git commit -m "feat: add success notifications to _process_movie"
```

---

## Task 11: Add Failure Notifications to _process_movie

**Files:**
- Modify: `src/media_processor.py:95-131`
- Modify: `tests/test_media_processor.py`

**Step 1: Write the failing test**

Add to `tests/test_media_processor.py`:

```python
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
            "imdbId": "tt0133093"
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
            "imdbId": ""  # No IMDB ID
        }
        result = processor._process_movie(movie)

        assert result is False
        mock_notifier.collect_failure.assert_called_once()

        call_args = mock_notifier.collect_failure.call_args
        assert "No IMDB ID" in call_args[1]["reason"]
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_media_processor.py::test_process_movie_calls_collect_failure_on_no_streams -v`

Expected: FAIL with "AssertionError: Expected 'collect_failure' to have been called once."

**Step 3: Write minimal implementation**

In `src/media_processor.py`, update `_process_movie` to add failure notifications:

After line 96 (no IMDB ID warning):
```python
if self.notifier:
    self.notifier.collect_failure(
        media_type="movie",
        title=f"{title} ({year})",
        reason="No IMDB ID found",
        details={"movie_id": movie_id}
    )
```

After line 106 (no streams warning):
```python
if self.notifier:
    self.notifier.collect_failure(
        media_type="movie",
        title=f"{title} ({year})",
        reason="No cached streams available",
        details={"imdb_id": imdb_id}
    )
```

After line 117 (no playback URL error):
```python
if self.notifier:
    self.notifier.collect_failure(
        media_type="movie",
        title=f"{title} ({year})",
        reason="No playback URL in stream",
        details={"imdb_id": imdb_id}
    )
```

After line 129 (download trigger failed):
```python
if self.notifier:
    self.notifier.collect_failure(
        media_type="movie",
        title=f"{title} ({year})",
        reason="Download trigger failed",
        details={"imdb_id": imdb_id, "stream_url": stream["url"]}
    )
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_media_processor.py::test_process_movie_calls_collect_failure_on_no_streams tests/test_media_processor.py::test_process_movie_calls_collect_failure_on_no_imdb -v`

Expected: PASS (both tests)

**Step 5: Commit**

```bash
git add src/media_processor.py tests/test_media_processor.py
git commit -m "feat: add failure notifications to _process_movie"
```

---

## Task 12: Add Success Notifications to _process_episode

**Files:**
- Modify: `src/media_processor.py:180-187`
- Modify: `tests/test_media_processor.py`

**Step 1: Write the failing test**

Add to `tests/test_media_processor.py`:

```python
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
    mock_aiostreams.search_episode.return_value = [{
        "title": "Breaking Bad S01E01 1080p",
        "url": "http://stream-url",
        "description": "1080p WEB-DL"
    }]

    with patch("src.media_processor.DiscordNotifier") as mock_notifier_class:
        mock_notifier = Mock()
        mock_notifier_class.return_value = mock_notifier

        processor = MediaProcessor(config)

        with patch.object(processor, '_trigger_aiostreams_download', return_value=True):
            episode = {
                "id": 1,
                "seasonNumber": 1,
                "episodeNumber": 1,
                "title": "Pilot",
                "series": {
                    "title": "Breaking Bad",
                    "imdbId": "tt0959621"
                }
            }
            result = processor._process_episode(episode)

            assert result is True
            mock_notifier.notify_success.assert_called_once()

            call_args = mock_notifier.notify_success.call_args
            assert call_args[1]["media_type"] == "episode"
            assert "Breaking Bad" in call_args[1]["title"]
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_media_processor.py::test_process_episode_calls_notify_success -v`

Expected: FAIL with "AssertionError: Expected 'notify_success' to have been called once."

**Step 3: Write minimal implementation**

In `src/media_processor.py`, in `_process_episode` method, add after line 185 (after successful trigger and unmonitor):

```python
# Notify Discord of success
if self.notifier:
    self.notifier.notify_success(
        media_type="episode",
        title=episode_label,
        details={
            "series_title": series_title,
            "season": season_number,
            "episode_number": episode_number,
            "imdb_id": imdb_id,
            "quality": stream.get("description", "Unknown"),
            "stream_title": stream.get("title", "")
        }
    )
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_media_processor.py::test_process_episode_calls_notify_success -v`

Expected: PASS

**Step 5: Commit**

```bash
git add src/media_processor.py tests/test_media_processor.py
git commit -m "feat: add success notifications to _process_episode"
```

---

## Task 13: Add Failure Notifications to _process_episode

**Files:**
- Modify: `src/media_processor.py:146-191`
- Modify: `tests/test_media_processor.py`

**Step 1: Write the failing test**

Add to `tests/test_media_processor.py`:

```python
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
            "series": {
                "title": "Breaking Bad",
                "imdbId": "tt0959621"
            }
        }
        result = processor._process_episode(episode)

        assert result is False
        mock_notifier.collect_failure.assert_called_once()

        call_args = mock_notifier.collect_failure.call_args
        assert call_args[1]["media_type"] == "episode"
        assert "Breaking Bad" in call_args[1]["title"]
        assert "No cached streams" in call_args[1]["reason"]
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_media_processor.py::test_process_episode_calls_collect_failure_on_no_streams -v`

Expected: FAIL with "AssertionError: Expected 'collect_failure' to have been called once."

**Step 3: Write minimal implementation**

In `src/media_processor.py`, update `_process_episode` to add failure notifications:

After line 147 (no IMDB/TVDB ID warning):
```python
if self.notifier:
    self.notifier.collect_failure(
        media_type="episode",
        title=f"{series_title} S{season_number:02d}E{episode_number:02d}",
        reason="No IMDB/TVDB ID found",
        details={"episode_id": episode_id}
    )
```

After line 162 (no IMDB ID warning):
```python
if self.notifier:
    self.notifier.collect_failure(
        media_type="episode",
        title=episode_label,
        reason="No IMDB ID for series",
        details={"series_title": series_title}
    )
```

After line 167 (no streams warning):
```python
if self.notifier:
    self.notifier.collect_failure(
        media_type="episode",
        title=episode_label,
        reason="No cached streams available",
        details={"imdb_id": imdb_id, "season": season_number, "episode": episode_number}
    )
```

After line 177 (no playback URL error):
```python
if self.notifier:
    self.notifier.collect_failure(
        media_type="episode",
        title=episode_label,
        reason="No playback URL in stream",
        details={"imdb_id": imdb_id}
    )
```

After line 189 (download trigger failed):
```python
if self.notifier:
    self.notifier.collect_failure(
        media_type="episode",
        title=episode_label,
        reason="Download trigger failed",
        details={"imdb_id": imdb_id, "stream_url": stream["url"]}
    )
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_media_processor.py::test_process_episode_calls_collect_failure_on_no_streams -v`

Expected: PASS

**Step 5: Commit**

```bash
git add src/media_processor.py tests/test_media_processor.py
git commit -m "feat: add failure notifications to _process_episode"
```

---

## Task 14: Add Failure Summary to process_all

**Files:**
- Modify: `src/media_processor.py:32-46`
- Modify: `tests/test_media_processor.py`

**Step 1: Write the failing test**

Add to `tests/test_media_processor.py`:

```python
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
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_media_processor.py::test_process_all_calls_send_failure_summary -v`

Expected: FAIL with "AssertionError: Expected 'send_failure_summary' to have been called once."

**Step 3: Write minimal implementation**

In `src/media_processor.py`, in `process_all` method, add after line 45 (after logging statistics):

```python
# Send batched failure summary
if self.notifier:
    self.notifier.send_failure_summary()
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_media_processor.py::test_process_all_calls_send_failure_summary -v`

Expected: PASS

**Step 5: Commit**

```bash
git add src/media_processor.py tests/test_media_processor.py
git commit -m "feat: add failure summary to process_all cycle end"
```

---

## Task 15: Run Full Test Suite

**Files:**
- N/A (verification step)

**Step 1: Run all tests**

Run: `uv run pytest -v`

Expected: All tests pass

**Step 2: Run tests with coverage (optional)**

Run: `uv run pytest --cov=src --cov-report=term-missing`

Expected: Good coverage on new code

**Step 3: Fix any failing tests**

If any tests fail, debug and fix them before proceeding.

**Step 4: Run linting**

Run: `uv run ruff check src/ tests/`

Expected: No linting errors

**Step 5: Format code**

Run: `uv run ruff format src/ tests/`

Expected: Code formatted successfully

**Step 6: Commit if any fixes were made**

```bash
git add -A
git commit -m "test: fix any test failures and format code"
```

---

## Task 16: Update Documentation

**Files:**
- Create: `.env.example` (if doesn't exist) or modify existing
- Modify: `README.md` (if exists)

**Step 1: Check if .env.example exists**

Run: `ls .env.example`

If exists, read it. If not, create it.

**Step 2: Add DISCORD_WEBHOOK_URL to .env.example**

Add or update `.env.example`:

```bash
# Required
AIOSTREAMS_URL=http://your-aiostreams-url

# At least one of Radarr or Sonarr required
RADARR_URL=http://your-radarr-url
RADARR_API_KEY=your-radarr-api-key
SONARR_URL=http://your-sonarr-url
SONARR_API_KEY=your-sonarr-api-key

# Optional
POLL_INTERVAL_MINUTES=10
RETRY_FAILED_HOURS=24
LOG_LEVEL=INFO

# Discord Notifications (optional)
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/YOUR_WEBHOOK_ID/YOUR_WEBHOOK_TOKEN
```

**Step 3: Update README if it documents environment variables**

Check README.md for environment variable documentation and add DISCORD_WEBHOOK_URL section if applicable.

**Step 4: Commit documentation updates**

```bash
git add .env.example README.md
git commit -m "docs: add DISCORD_WEBHOOK_URL configuration option"
```

---

## Task 17: Manual Testing (Optional)

**Files:**
- N/A (manual verification)

**Step 1: Create test Discord webhook**

1. Open Discord
2. Go to Server Settings → Integrations → Webhooks
3. Create new webhook
4. Copy webhook URL

**Step 2: Set up test environment**

Create `.env` file with test webhook:

```bash
cp .env.example .env
# Edit .env and add your test webhook URL
```

**Step 3: Run the service**

Run: `uv run python -m src.main`

**Step 4: Verify notifications**

- Check Discord channel for success notifications
- Check Discord channel for failure summary
- Verify message formatting and content

**Step 5: Test error scenarios**

- Set invalid webhook URL and verify graceful failure
- Remove webhook URL and verify service works without notifications

---

## Summary

This plan implements Discord webhook notifications for AIODarr following TDD principles:

1. **Config** - Added optional DISCORD_WEBHOOK_URL environment variable
2. **DiscordNotifier** - Created notifier class with success/failure handling
3. **Integration** - Integrated notifier into MediaProcessor workflow
4. **Testing** - Comprehensive unit and integration tests with mocks
5. **Documentation** - Updated configuration examples

**Key Principles Applied:**
- ✅ **TDD** - Tests written before implementation
- ✅ **DRY** - Reusable embed formatting methods
- ✅ **YAGNI** - Simple implementation, no over-engineering
- ✅ **Error Handling** - Graceful degradation, no blocking errors
- ✅ **Separation of Concerns** - Clean notifier abstraction
- ✅ **Frequent Commits** - Small, logical commits per feature

**Total Estimated Time:** 90-120 minutes for full implementation
