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

        # Add episode-specific fields
        if media_type == "episode":
            season = details.get("season")
            episode = details.get("episode")
            if season is not None and episode is not None:
                embed["fields"].append(
                    {"name": "Episode", "value": f"S{season:02d}E{episode:02d}", "inline": True}
                )
            if episode_title := details.get("episode_title"):
                embed["fields"].append(
                    {"name": "Episode Title", "value": episode_title, "inline": True}
                )

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

        self.failures.append(
            {"media_type": media_type, "title": title, "reason": reason, "details": details}
        )

    def send_failure_summary(self) -> None:
        """
        Send batched failure summary notification to Discord and clear failures list
        """
        if not self.webhook_url:
            return

        if not self.failures:
            return

        embed = self._format_failure_summary_embed()
        success = self._send_webhook(embed)
        if success:
            logger.info(f"Sent Discord failure summary for {len(self.failures)} items")
            self.failures.clear()

    def _format_failure_summary_embed(self) -> dict[str, Any]:
        """
        Format batched failures as Discord embed, grouped by media type

        Returns:
            Discord embed dict
        """
        total_count = len(self.failures)
        embed = {
            "title": f"✗ Failed to process {total_count} items",
            "description": "",
            "color": 0xFF0000,  # Red
            "timestamp": datetime.now(UTC).isoformat(),
        }

        # Group failures by media type
        movies = [f for f in self.failures if f["media_type"] == "movie"]
        episodes = [f for f in self.failures if f["media_type"] == "episode"]

        # Format movies section
        if movies:
            movie_label = "Movies" if len(movies) > 1 else "Movie"
            embed["description"] += f"**{movie_label} ({len(movies)})**\n"
            for failure in movies:
                title = failure["title"]
                reason = failure["reason"]
                embed["description"] += f"• {title} - {reason}\n"
            embed["description"] += "\n"

        # Format episodes section
        if episodes:
            episode_label = "Episodes" if len(episodes) > 1 else "Episode"
            embed["description"] += f"**{episode_label} ({len(episodes)})**\n"
            for failure in episodes:
                title = failure["title"]
                reason = failure["reason"]
                details = failure["details"]
                # Add episode info if available
                season = details.get("season")
                episode_num = details.get("episode")
                if season is not None and episode_num is not None:
                    title = f"{title} S{season:02d}E{episode_num:02d}"
                embed["description"] += f"• {title} - {reason}\n"

        # Remove trailing newline
        embed["description"] = embed["description"].rstrip()

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
