import logging
import time
from typing import Any

from src.clients.aiostreams import AIOStreamsClient
from src.clients.radarr import RadarrClient
from src.clients.realdebrid import RealDebridClient
from src.clients.sonarr import SonarrClient
from src.config import Config
from src.notifiers.discord import DiscordNotifier
from src.storage import ProcessedMoviesStorage

logger = logging.getLogger(__name__)


class MediaProcessor:
    """Main processor for handling wanted movies and TV shows"""

    def __init__(self, config: Config):
        self.config = config
        self.aiostreams = AIOStreamsClient(config.aiostreams_url)
        self.storage = ProcessedMoviesStorage()

        # Initialize clients based on configuration
        self.radarr: RadarrClient | None = None
        if config.radarr_enabled:
            self.radarr = RadarrClient(config.radarr_url, config.radarr_api_key)
            logger.info("Radarr client initialized")

        self.sonarr: SonarrClient | None = None
        if config.sonarr_enabled:
            self.sonarr = SonarrClient(config.sonarr_url, config.sonarr_api_key)
            logger.info("Sonarr client initialized")

        # Initialize Discord notifier if webhook URL is configured
        self.notifier: DiscordNotifier | None = None
        if config.discord_webhook_url:
            self.notifier = DiscordNotifier(config.discord_webhook_url)
            logger.info("Discord notifier initialized")

        # Initialize Real-Debrid client for stream verification if configured
        self.rd_client: RealDebridClient | None = None
        if config.realdebrid_api_key:
            self.rd_client = RealDebridClient(config.realdebrid_api_key)
            logger.info("Real-Debrid client initialized for stream verification")

    def process_all(self) -> None:
        """Process both movies and TV shows"""
        if self.radarr:
            self.process_wanted_movies()

        if self.sonarr:
            self.process_wanted_episodes()

        # Log statistics
        stats = self.storage.get_stats()
        logger.info(
            f"Statistics - Total: {stats['total']}, "
            f"Successful: {stats['successful']}, "
            f"Failed: {stats['failed']}"
        )

        # Send batched failure summary
        if self.notifier:
            self.notifier.send_failure_summary()

    def process_wanted_movies(self) -> None:
        """Process all wanted movies from Radarr"""
        if not self.radarr:
            return

        logger.info("Checking for wanted movies...")
        wanted = self.radarr.get_wanted_movies()
        logger.info(f"Found {len(wanted)} wanted movies")

        for movie in wanted:
            movie_id = movie["id"]

            # Skip if recently processed
            if self.storage.should_skip(movie_id, self.config.retry_failed_hours):
                logger.debug(f"Skipping movie {movie_id} (recently processed)")
                continue

            self._process_movie(movie)

    def process_wanted_episodes(self) -> None:
        """Process all wanted episodes from Sonarr"""
        if not self.sonarr:
            return

        logger.info("Checking for wanted episodes...")
        wanted = self.sonarr.get_wanted_episodes()
        logger.info(f"Found {len(wanted)} wanted episodes")

        for episode in wanted:
            episode_id = episode["id"]

            # Skip if recently processed (using same storage for simplicity)
            # In production, you might want separate storage for episodes
            storage_key = f"episode_{episode_id}"
            if self.storage.should_skip(storage_key, self.config.retry_failed_hours):
                logger.debug(f"Skipping episode {episode_id} (recently processed)")
                continue

            self._process_episode(episode)

    def _process_movie(self, movie: dict[str, Any]) -> bool:
        """Process a single movie"""
        movie_id = movie["id"]
        title = movie["title"]
        year = movie.get("year", "")
        imdb_id = movie.get("imdbId", "")

        if not imdb_id:
            logger.warning(f"No IMDB ID for {title} ({year}), skipping")
            if self.notifier:
                self.notifier.collect_failure(
                    media_type="movie",
                    title=f"{title} ({year})",
                    reason="No IMDB ID found",
                    details={"movie_id": movie_id},
                )
            return False

        logger.info(f"Processing movie: {title} ({year}) - IMDB: {imdb_id}")

        # Query AIOStreams for cached torrents
        streams = self.aiostreams.search_movie(imdb_id)

        if not streams:
            logger.warning(f"No cached streams found for {title}")
            self.storage.mark_processed(movie_id, success=False)
            if self.notifier:
                self.notifier.collect_failure(
                    media_type="movie",
                    title=f"{title} ({year})",
                    reason="No cached streams available",
                    details={"imdb_id": imdb_id},
                )
            return False

        # Use first stream from AIOStreams (pre-sorted by their algorithm)
        logger.info(f"Found {len(streams)} cached streams, using first one")
        stream = streams[0]
        logger.info(f"Trying stream: {stream['title']}")

        # Trigger AIOStreams playback URL to add to Real-Debrid
        if not stream.get("url"):
            logger.error(f"Stream has no playback URL for {title}")
            self.storage.mark_processed(movie_id, success=False)
            if self.notifier:
                self.notifier.collect_failure(
                    media_type="movie",
                    title=f"{title} ({year})",
                    reason="No playback URL in stream",
                    details={"imdb_id": imdb_id},
                )
            return False

        success = self._trigger_aiostreams_download(stream["url"], f"{title} ({year})")
        if success:
            logger.info(f"✓ Successfully triggered {title} via AIOStreams")
            # Unmonitor the movie in Radarr
            if self.radarr and self.radarr.unmonitor_movie(movie_id):
                logger.info(f"Unmonitored {title} in Radarr")
            self.storage.mark_processed(movie_id, success=True)
            # Notify Discord of success
            if self.notifier:
                self.notifier.notify_success(
                    media_type="movie",
                    title=f"{title} ({year})",
                    details={
                        "year": year,
                        "imdb_id": imdb_id,
                        "quality": stream.get("description", "Unknown"),
                        "stream_title": stream.get("title", ""),
                    },
                )
            return True

        logger.error(f"Failed to trigger download for {title}")
        self.storage.mark_processed(movie_id, success=False)
        if self.notifier:
            self.notifier.collect_failure(
                media_type="movie",
                title=f"{title} ({year})",
                reason="Download trigger failed",
                details={"imdb_id": imdb_id, "stream_url": stream["url"]},
            )
        return False

    def _process_episode(self, episode: dict[str, Any]) -> bool:
        """Process a single TV episode"""
        episode_id = episode["id"]
        series = episode.get("series", {})
        series_title = series.get("title", "Unknown Series")
        season_number = episode.get("seasonNumber", 0)
        episode_number = episode.get("episodeNumber", 0)
        title = episode.get("title", "")

        # Get IMDB or TVDB ID from series
        imdb_id = series.get("imdbId", "")
        tvdb_id = series.get("tvdbId", "")

        if not imdb_id and not tvdb_id:
            logger.warning(f"No IMDB/TVDB ID for {series_title}, skipping")
            if self.notifier:
                self.notifier.collect_failure(
                    media_type="episode",
                    title=f"{series_title} S{season_number:02d}E{episode_number:02d}",
                    reason="No IMDB/TVDB ID found",
                    details={"episode_id": episode_id},
                )
            return False

        episode_label = f"{series_title} S{season_number:02d}E{episode_number:02d}"
        if title:
            episode_label += f" - {title}"

        logger.info(f"Processing episode: {episode_label}")

        # For TV shows, use IMDB ID with season/episode info
        # AIOStreams format: /stream/series/{imdb_id}:{season}:{episode}.json
        if imdb_id:
            streams = self.aiostreams.search_episode(imdb_id, season_number, episode_number)
        else:
            logger.warning(f"No IMDB ID for {series_title}, cannot query AIOStreams")
            self.storage.mark_processed(f"episode_{episode_id}", success=False)
            if self.notifier:
                self.notifier.collect_failure(
                    media_type="episode",
                    title=episode_label,
                    reason="No IMDB ID for series",
                    details={"series_title": series_title},
                )
            return False

        if not streams:
            logger.warning(f"No cached streams found for {episode_label}")
            self.storage.mark_processed(f"episode_{episode_id}", success=False)
            if self.notifier:
                self.notifier.collect_failure(
                    media_type="episode",
                    title=episode_label,
                    reason="No cached streams available",
                    details={
                        "imdb_id": imdb_id,
                        "season": season_number,
                        "episode": episode_number,
                    },
                )
            return False

        # Use first stream
        logger.info(f"Found {len(streams)} cached streams, using first one")
        stream = streams[0]
        logger.info(f"Trying stream: {stream['title']}")

        if not stream.get("url"):
            logger.error(f"Stream has no playback URL for {episode_label}")
            self.storage.mark_processed(f"episode_{episode_id}", success=False)
            if self.notifier:
                self.notifier.collect_failure(
                    media_type="episode",
                    title=episode_label,
                    reason="No playback URL in stream",
                    details={"imdb_id": imdb_id},
                )
            return False

        success = self._trigger_aiostreams_download(stream["url"], episode_label)
        if success:
            logger.info(f"✓ Successfully triggered {episode_label} via AIOStreams")
            # Unmonitor the episode in Sonarr
            if self.sonarr and self.sonarr.unmonitor_episode(episode_id):
                logger.info(f"Unmonitored {episode_label} in Sonarr")
            self.storage.mark_processed(f"episode_{episode_id}", success=True)
            # Notify Discord of success
            if self.notifier:
                self.notifier.notify_success(
                    media_type="episode",
                    title=episode_label,
                    details={
                        "series_title": series_title,
                        "season": season_number,
                        "episode": episode_number,
                        "episode_title": title,
                        "imdb_id": imdb_id,
                        "quality": stream.get("description", "Unknown"),
                        "stream_title": stream.get("title", ""),
                    },
                )
            return True

        logger.error(f"Failed to trigger download for {episode_label}")
        self.storage.mark_processed(f"episode_{episode_id}", success=False)
        if self.notifier:
            self.notifier.collect_failure(
                media_type="episode",
                title=episode_label,
                reason="Download trigger failed",
                details={"imdb_id": imdb_id, "stream_url": stream["url"]},
            )
        return False

    def _try_stream(self, stream: dict[str, Any], label: str) -> bool:
        """
        Trigger a single stream and verify it was added to Real-Debrid.

        Args:
            stream: Stream dict with 'url', 'filename', 'title' keys
            label: Human-readable label for logging

        Returns:
            True if stream was successfully triggered and verified, False otherwise
        """
        url = stream.get("url")
        if not url:
            logger.debug(f"Stream has no playback URL, skipping: {stream.get('title', '')}")
            return False

        if not self._trigger_aiostreams_download(url, label):
            return False

        if not self.rd_client:
            return True

        filename = stream.get("filename", "")
        if not filename:
            logger.debug("No filename for RD verification, assuming success")
            return True

        logger.info(f"Waiting 5s then verifying in Real-Debrid for: {filename}")
        time.sleep(5)

        torrents = self.rd_client.list_torrents()
        filename_lower = filename.lower()
        for torrent in torrents:
            torrent_filename = torrent.get("filename", "").lower()
            if filename_lower in torrent_filename or torrent_filename in filename_lower:
                logger.info(f"Verified in Real-Debrid: {torrent.get('filename')}")
                return True

        logger.warning(f"Not found in Real-Debrid after trigger: {filename}")
        return False

    def _trigger_aiostreams_download(self, url: str, title: str) -> bool:
        """
        Trigger AIOStreams to add torrent to Real-Debrid by streaming the URL

        Args:
            url: AIOStreams playback URL
            title: Media title for logging

        Returns:
            True if successfully triggered, False otherwise
        """
        import requests

        try:
            logger.info(f"Triggering AIOStreams download via HEAD request to: {url[:100]}...")
            # Use HEAD request to trigger the download without downloading content
            response = requests.head(url, timeout=30, allow_redirects=True)
            response.raise_for_status()
            logger.info(f"Successfully triggered download for {title}")
            return True
        except Exception as e:
            logger.error(f"Error triggering AIOStreams download: {e}")
            return False
