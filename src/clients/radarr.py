import logging
from typing import Any

import requests

logger = logging.getLogger(__name__)


class RadarrClient:
    """Client for interacting with Radarr API"""

    def __init__(self, url: str, api_key: str):
        self.url = url.rstrip('/')
        self.api_key = api_key
        self.headers = {'X-Api-Key': api_key}

    def get_wanted_movies(self) -> list[dict[str, Any]]:
        """Get all wanted (missing) movies from Radarr"""
        try:
            response = requests.get(
                f'{self.url}/api/v3/wanted/missing',
                headers=self.headers,
                params={'pageSize': 1000}
            )
            response.raise_for_status()
            data = response.json()
            return data['records']
        except requests.RequestException as e:
            logger.error(f"Error fetching wanted movies from Radarr: {e}")
            return []

    def get_movie(self, movie_id: int) -> dict[str, Any]:
        """Get movie details by ID"""
        response = requests.get(
            f'{self.url}/api/v3/movie/{movie_id}',
            headers=self.headers
        )
        response.raise_for_status()
        return response.json()

    def unmonitor_movie(self, movie_id: int) -> bool:
        """
        Set movie as unmonitored in Radarr

        Args:
            movie_id: Radarr movie ID

        Returns:
            True if successfully unmonitored, False otherwise
        """
        try:
            # First get the movie to get its current state
            movie = self.get_movie(movie_id)

            # Update monitored status to False
            movie['monitored'] = False

            # Send PUT request to update the movie
            response = requests.put(
                f'{self.url}/api/v3/movie/{movie_id}',
                headers=self.headers,
                json=movie
            )
            response.raise_for_status()
            logger.info(f"Successfully unmonitored movie ID {movie_id}")
            return True
        except Exception as e:
            logger.error(f"Error unmonitoring movie {movie_id}: {e}")
            return False
