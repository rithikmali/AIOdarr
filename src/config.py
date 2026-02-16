import os

from dotenv import load_dotenv

load_dotenv()


class Config:
    """Application configuration loaded from environment variables"""

    def __init__(self):
        # Required configuration
        self.aiostreams_url = self._get_required("AIOSTREAMS_URL")

        # At least one of Radarr or Sonarr must be configured
        self.radarr_url = os.getenv("RADARR_URL", "").rstrip("/")
        self.radarr_api_key = os.getenv("RADARR_API_KEY", "")
        self.sonarr_url = os.getenv("SONARR_URL", "").rstrip("/")
        self.sonarr_api_key = os.getenv("SONARR_API_KEY", "")

        # Validate at least one is configured
        radarr_configured = self.radarr_url and self.radarr_api_key
        sonarr_configured = self.sonarr_url and self.sonarr_api_key
        if not radarr_configured and not sonarr_configured:
            raise ValueError("At least one of Radarr or Sonarr must be configured")

        # Optional configuration
        self.poll_interval_minutes = int(os.getenv("POLL_INTERVAL_MINUTES", "10"))
        self.retry_failed_hours = int(os.getenv("RETRY_FAILED_HOURS", "24"))
        self.discord_webhook_url = os.getenv("DISCORD_WEBHOOK_URL", "")
        self.log_level = os.getenv("LOG_LEVEL", "INFO")

        self.aiostreams_url = self.aiostreams_url.rstrip("/")

    @property
    def radarr_enabled(self) -> bool:
        """Check if Radarr is configured"""
        return bool(self.radarr_url and self.radarr_api_key)

    @property
    def sonarr_enabled(self) -> bool:
        """Check if Sonarr is configured"""
        return bool(self.sonarr_url and self.sonarr_api_key)

    def _get_required(self, key: str) -> str:
        value = os.getenv(key)
        if not value:
            raise ValueError(f"{key} is required")
        return value
