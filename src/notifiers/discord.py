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
        Format batched failures as Discord embed, grouped by media type.
        Truncates to stay within Discord's 6000 char total and 4096 char field limits.

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

        # Discord limits: 6000 chars total, 4096 chars per field (description)
        # Reserve space for title, timestamp overhead, and truncation message
        MAX_DESCRIPTION_LENGTH = 4000  # Leave buffer for truncation message
        MAX_TOTAL_LENGTH = 5800  # Leave buffer for title and other fields
        TRUNCATION_MESSAGE_LENGTH = 50  # Estimated length of "...and X more items" message

        # Group failures by media type
        movies = [f for f in self.failures if f["media_type"] == "movie"]
        episodes = [f for f in self.failures if f["media_type"] == "episode"]

        description_parts = []
        truncated_movies = 0
        truncated_episodes = 0

        def get_current_length():
            """Helper to get current accumulated description length"""
            return len("".join(description_parts))

        # Format movies section
        if movies:
            movie_label = "Movies" if len(movies) > 1 else "Movie"
            section_header = f"**{movie_label} ({len(movies)})**\n"
            section_content = []

            for failure in movies:
                title = failure["title"]
                reason = failure["reason"]
                line = f"• {title} - {reason}\n"

                # Calculate what total length would be with this line
                current_total = get_current_length()
                new_total = (
                    current_total
                    + len(section_header)
                    + len("".join(section_content))
                    + len(line)
                    + TRUNCATION_MESSAGE_LENGTH
                    + 2  # for trailing "\n"
                )

                # Check both total and field limits
                if new_total > MAX_TOTAL_LENGTH or new_total > MAX_DESCRIPTION_LENGTH:
                    truncated_movies = len(movies) - len(section_content)
                    break

                section_content.append(line)

            # Add the movies section
            description_parts.append(section_header)
            description_parts.extend(section_content)

            if truncated_movies > 0:
                description_parts.append(f"_...and {truncated_movies} more movies_\n")

            description_parts.append("\n")

        # Format episodes section
        if episodes:
            episode_label = "Episodes" if len(episodes) > 1 else "Episode"
            section_header = f"**{episode_label} ({len(episodes)})**\n"
            section_content = []

            for failure in episodes:
                title = failure["title"]
                reason = failure["reason"]
                details = failure["details"]
                # Add episode info if available
                season = details.get("season")
                episode_num = details.get("episode")
                if season is not None and episode_num is not None:
                    title = f"{title} S{season:02d}E{episode_num:02d}"
                line = f"• {title} - {reason}\n"

                # Calculate what total length would be with this line
                current_total = get_current_length()
                new_total = (
                    current_total
                    + len(section_header)
                    + len("".join(section_content))
                    + len(line)
                    + TRUNCATION_MESSAGE_LENGTH
                )

                # Check both total and field limits
                if new_total > MAX_TOTAL_LENGTH or new_total > MAX_DESCRIPTION_LENGTH:
                    truncated_episodes = len(episodes) - len(section_content)
                    break

                section_content.append(line)

            # Add the episodes section
            description_parts.append(section_header)
            description_parts.extend(section_content)

            if truncated_episodes > 0:
                description_parts.append(f"_...and {truncated_episodes} more episodes_\n")

        # Combine all parts
        embed["description"] = "".join(description_parts).rstrip()

        return embed

    def _send_webhook(self, embed: dict[str, Any]) -> bool:
        """
        Send embed to Discord webhook

        Args:
            embed: Discord embed dict

        Returns:
            True if successful, False otherwise
        """
        import requests

        try:
            response = requests.post(self.webhook_url, json={"embeds": [embed]}, timeout=10)
            response.raise_for_status()
            return True
        except requests.HTTPError as e:
            logger.error(f"HTTP error sending Discord webhook: {e}")
            return False
        except requests.RequestException as e:
            logger.error(f"Network error sending Discord webhook: {e}")
            return False
