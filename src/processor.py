import logging
from typing import Any

from src.clients.aiostreams import AIOStreamsClient
from src.clients.radarr import RadarrClient
from src.clients.realdebrid import RealDebridClient
from src.config import Config
from src.storage import ProcessedMoviesStorage

logger = logging.getLogger(__name__)


class MovieProcessor:
    """Main processor for handling wanted movies"""

    def __init__(self, config: Config):
        self.config = config
        self.radarr = RadarrClient(config.radarr_url, config.radarr_api_key)
        self.aiostreams = AIOStreamsClient(config.aiostreams_url)
        self.rd = RealDebridClient(config.realdebrid_api_key)
        self.storage = ProcessedMoviesStorage()

    def process_wanted_movies(self) -> None:
        """Process all wanted movies from Radarr"""
        logger.info("Checking for wanted movies...")

        wanted = self.radarr.get_wanted_movies()
        logger.info(f"Found {len(wanted)} wanted movies")

        for movie in wanted:
            movie_id = movie['id']

            # Skip if recently processed
            if self.storage.should_skip(movie_id, self.config.retry_failed_hours):
                logger.debug(f"Skipping movie {movie_id} (recently processed)")
                continue

            self._process_movie(movie)

        # Log statistics
        stats = self.storage.get_stats()
        logger.info(f"Statistics - Total: {stats['total']}, "
                   f"Successful: {stats['successful']}, "
                   f"Failed: {stats['failed']}")

    def _process_movie(self, movie: dict[str, Any]) -> bool:
        """
        Process a single movie

        Args:
            movie: Movie dictionary from Radarr

        Returns:
            True if successfully added to Real-Debrid, False otherwise
        """
        movie_id = movie['id']
        title = movie['title']
        year = movie.get('year', '')
        imdb_id = movie.get('imdbId', '')

        if not imdb_id:
            logger.warning(f"No IMDB ID for {title} ({year}), skipping")
            return False

        logger.info(f"Processing: {title} ({year}) - IMDB: {imdb_id}")

        # Query AIOStreams for cached torrents
        streams = self.aiostreams.search_movie(imdb_id)

        if not streams:
            logger.warning(f"No cached streams found for {title}")
            self.storage.mark_processed(movie_id, success=False)
            return False

        # Use first stream from AIOStreams (pre-sorted by their algorithm)
        logger.info(f"Found {len(streams)} cached streams, using first one")
        stream = streams[0]
        logger.info(f"Trying stream: {stream['title']}")

        magnet = stream.get('magnet') or stream['infoHash']
        torrent_id = self.rd.add_magnet(magnet)

        if torrent_id:
            logger.info(f"✓ Successfully added {title} to Real-Debrid (ID: {torrent_id})")
            self.storage.mark_processed(movie_id, success=True)
            return True

        logger.error(f"Failed to add {title} to Real-Debrid")
        self.storage.mark_processed(movie_id, success=False)
        return False
