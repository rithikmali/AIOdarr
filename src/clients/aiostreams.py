import logging
from typing import Any

import requests

logger = logging.getLogger(__name__)


class AIOStreamsClient:
    """Client for querying AIOStreams Stremio API"""

    def __init__(self, url: str):
        self.url = url.rstrip('/')

    def search_movie(self, imdb_id: str) -> list[dict[str, Any]]:
        """
        Search for movie streams using IMDB ID

        Args:
            imdb_id: IMDB ID (e.g., 'tt1234567')

        Returns:
            List of cached stream dictionaries with title, infoHash, quality
        """
        endpoint = f'{self.url}/stream/movie/{imdb_id}.json'

        try:
            response = requests.get(endpoint, timeout=30)
            response.raise_for_status()
            data = response.json()

            streams = data.get('streams', [])

            # Filter for cached Real-Debrid streams
            cached_streams = []
            for stream in streams:
                # AIOStreams uses 'name' field, fallback to 'title'
                title = stream.get('name') or stream.get('title', '')
                description = stream.get('description', '')

                # Check for cached indicators (⚡ or RD in title/name)
                if '⚡' in title or 'RD+' in title or '[RD]' in title:
                    url = stream.get('url')
                    magnet = url if url and url.startswith('magnet:') else None
                    cached_streams.append({
                        'title': title,
                        'infoHash': stream.get('infoHash'),
                        'magnet': magnet,
                        'quality': self._parse_quality(description or title)
                    })

            return cached_streams

        except Exception as e:
            logger.error(f"Error querying AIOStreams for {imdb_id}: {e}")
            return []

    def _parse_quality(self, title: str) -> int:
        """
        Extract quality from stream title

        Args:
            title: Stream title string

        Returns:
            Quality as integer (2160, 1080, 720, or 480)
        """
        title_upper = title.upper()

        if '2160P' in title_upper or '4K' in title_upper:
            return 2160
        elif '1080P' in title_upper:
            return 1080
        elif '720P' in title_upper:
            return 720
        else:
            return 480
