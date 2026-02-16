import logging
from datetime import UTC, datetime
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

    def _format_success_embed(
        self, media_type: str, title: str, details: dict[str, Any]
    ) -> dict[str, Any]:
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
            "title": f"✓ {title}",
            "description": f"Successfully added {media_type}",
            "color": 0x00FF00,  # Green
            "fields": [],
            "timestamp": datetime.now(UTC).isoformat(),
        }

        # Add quality if available
        if quality := details.get("quality"):
            embed["fields"].append({"name": "Quality", "value": quality, "inline": True})

        # Add IMDB ID if available
        if imdb_id := details.get("imdb_id"):
            embed["fields"].append({"name": "IMDB", "value": imdb_id, "inline": True})

        # Add stream title if available
        if stream_title := details.get("stream_title"):
            embed["fields"].append({"name": "Stream", "value": stream_title, "inline": False})

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
