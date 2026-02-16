import logging
from typing import Any

import requests

logger = logging.getLogger(__name__)


class AIOStreamsClient:
    """Client for querying AIOStreams Stremio API"""

    def __init__(self, url: str):
        self.url = url.rstrip("/")

    @staticmethod
    def _log_curl(
        method: str, url: str, headers: dict | None = None, timeout: int | None = None
    ) -> None:
        """Log the equivalent curl command for an HTTP request."""
        parts = ["curl", "-X", method]
        if headers:
            for key, value in headers.items():
                parts.append(f"-H '{key}: {value}'")
        if timeout:
            parts.append(f"--max-time {timeout}")
        parts.append(f"'{url}'")
        curl_cmd = " ".join(parts)
        logger.info(f"Equivalent curl command:\n  {curl_cmd}")

    def search_movie(self, imdb_id: str) -> list[dict[str, Any]]:
        """
        Search for movie streams using IMDB ID

        Args:
            imdb_id: IMDB ID (e.g., 'tt1234567')

        Returns:
            List of cached stream dictionaries with title, infoHash, quality
        """
        endpoint = f"{self.url}/stream/movie/{imdb_id}.json"

        try:
            self._log_curl("GET", endpoint, timeout=30)
            response = requests.get(endpoint, timeout=30)
            response.raise_for_status()
            data = response.json()

            streams = data.get("streams", [])
            return self._filter_streams(streams)

        except Exception as e:
            logger.error(f"Error querying AIOStreams for {imdb_id}: {e}")
            return []

    def search_episode(self, imdb_id: str, season: int, episode: int) -> list[dict[str, Any]]:
        """
        Search for TV episode streams using IMDB ID and season/episode numbers

        Args:
            imdb_id: IMDB ID (e.g., 'tt1234567')
            season: Season number
            episode: Episode number

        Returns:
            List of cached stream dictionaries with title, url, quality
        """
        endpoint = f"{self.url}/stream/series/{imdb_id}:{season}:{episode}.json"

        try:
            self._log_curl("GET", endpoint, timeout=30)
            response = requests.get(endpoint, timeout=30)
            response.raise_for_status()
            data = response.json()

            streams = data.get("streams", [])
            return self._filter_streams(streams)

        except Exception as e:
            logger.error(f"Error querying AIOStreams for {imdb_id} S{season}E{episode}: {e}")
            return []

    def _filter_streams(self, streams: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Filter streams for cached Real-Debrid results with videoHash."""
        cached_streams = []
        for stream in streams:
            # AIOStreams uses 'name' field, fallback to 'title'
            title = stream.get("name") or stream.get("title", "")
            description = stream.get("description", "")

            # Check for cached indicators (⚡ or RD in title/name)
            if not ("⚡" in title or "RD+" in title or "[RD]" in title):
                continue

            # Only keep streams that have videoHash in behaviorHints
            behavior_hints = stream.get("behaviorHints", {})
            if not behavior_hints or not behavior_hints.get("videoHash"):
                logger.debug(f"Skipping stream without videoHash: {title}")
                continue

            cached_streams.append(
                {
                    "title": title,
                    "url": stream.get("url"),
                    "infoHash": stream.get("infoHash"),
                    "quality": self._parse_quality(description or title),
                }
            )

        return cached_streams

    def _parse_quality(self, title: str) -> int:
        """
        Extract quality from stream title

        Args:
            title: Stream title string

        Returns:
            Quality as integer (2160, 1080, 720, or 480)
        """
        title_upper = title.upper()

        if "2160P" in title_upper or "4K" in title_upper:
            return 2160
        elif "1080P" in title_upper:
            return 1080
        elif "720P" in title_upper:
            return 720
        else:
            return 480
