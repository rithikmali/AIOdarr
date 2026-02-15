import logging
from typing import Any

import requests

logger = logging.getLogger(__name__)


class SonarrClient:
    """Client for interacting with Sonarr API"""

    def __init__(self, url: str, api_key: str):
        self.url = url.rstrip('/')
        self.api_key = api_key
        self.headers = {'X-Api-Key': api_key}

    def get_wanted_episodes(self) -> list[dict[str, Any]]:
        """Get all wanted (missing) episodes from Sonarr"""
        try:
            response = requests.get(
                f'{self.url}/api/v3/wanted/missing',
                headers=self.headers,
                params={'pageSize': 1000, 'includeSeries': True}
            )
            response.raise_for_status()
            data = response.json()
            return data['records']
        except requests.RequestException as e:
            logger.error(f"Error fetching wanted episodes from Sonarr: {e}")
            return []

    def get_episode(self, episode_id: int) -> dict[str, Any]:
        """Get episode details by ID"""
        response = requests.get(
            f'{self.url}/api/v3/episode/{episode_id}',
            headers=self.headers
        )
        response.raise_for_status()
        return response.json()

    def unmonitor_episode(self, episode_id: int) -> bool:
        """
        Set episode as unmonitored in Sonarr

        Args:
            episode_id: Sonarr episode ID

        Returns:
            True if successfully unmonitored, False otherwise
        """
        try:
            # First get the episode to get its current state
            episode = self.get_episode(episode_id)

            # Update monitored status to False
            episode['monitored'] = False

            # Send PUT request to update the episode
            response = requests.put(
                f'{self.url}/api/v3/episode/{episode_id}',
                headers=self.headers,
                json=episode
            )
            response.raise_for_status()
            logger.info(f"Successfully unmonitored episode ID {episode_id}")
            return True
        except Exception as e:
            logger.error(f"Error unmonitoring episode {episode_id}: {e}")
            return False
