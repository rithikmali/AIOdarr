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
