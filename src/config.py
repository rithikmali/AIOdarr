import os

from dotenv import load_dotenv

load_dotenv()


class Config:
    """Application configuration loaded from environment variables"""

    def __init__(self):
        self.radarr_url = self._get_required('RADARR_URL')
        self.radarr_api_key = self._get_required('RADARR_API_KEY')
        self.aiostreams_url = self._get_required('AIOSTREAMS_URL')
        self.realdebrid_api_key = self._get_required('REALDEBRID_API_KEY')

        self.poll_interval_minutes = int(os.getenv('POLL_INTERVAL_MINUTES', '10'))
        self.retry_failed_hours = int(os.getenv('RETRY_FAILED_HOURS', '24'))
        self.log_level = os.getenv('LOG_LEVEL', 'INFO')

        self.radarr_url = self.radarr_url.rstrip('/')
        self.aiostreams_url = self.aiostreams_url.rstrip('/')

    def _get_required(self, key: str) -> str:
        value = os.getenv(key)
        if not value:
            raise ValueError(f"{key} is required")
        return value
