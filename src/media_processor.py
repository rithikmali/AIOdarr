import logging
import re
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

        attempts = min(self.config.max_retry_attempts, len(streams))
        logger.info(f"Found {len(streams)} cached streams, will try up to {attempts}")

        attempt = 0
        for stream in streams:
            if attempt >= attempts:
                break
            logger.info(f"Attempt {attempt + 1}/{attempts}: {stream['title']}")
            if self._is_excluded_stream(stream):
                logger.info(f"Skipping excluded stream (not counting as attempt): {stream.get('filename') or stream.get('title')}")
                continue
            attempt += 1
            if self._try_stream(stream, f"{title} ({year})"):
                logger.info(f"✓ Successfully triggered {title} via AIOStreams")
                if self.radarr and self.radarr.unmonitor_movie(movie_id):
                    logger.info(f"Unmonitored {title} in Radarr")
                self.storage.mark_processed(movie_id, success=True)
                if self.notifier:
                    self.notifier.notify_success(
                        media_type="movie",
                        title=f"{title} ({year})",
                        details={
                            "year": year,
                            "imdb_id": imdb_id,
                            "quality": stream.get("quality", "Unknown"),
                            "stream_title": stream.get("title", ""),
                        },
                    )
                return True

        logger.error(f"All {attempts} stream attempts failed for {title}")
        self.storage.mark_processed(movie_id, success=False)
        if self.notifier:
            self.notifier.collect_failure(
                media_type="movie",
                title=f"{title} ({year})",
                reason=f"All {attempts} stream attempts failed",
                details={"imdb_id": imdb_id},
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

        attempts = min(self.config.max_retry_attempts, len(streams))
        logger.info(f"Found {len(streams)} cached streams, will try up to {attempts}")

        attempt = 0
        for stream in streams:
            if attempt >= attempts:
                break
            logger.info(f"Attempt {attempt + 1}/{attempts}: {stream['title']}")
            if self._is_excluded_stream(stream):
                logger.info(f"Skipping excluded stream (not counting as attempt): {stream.get('filename') or stream.get('title')}")
                continue
            attempt += 1
            if self._try_stream(stream, episode_label):
                logger.info(f"✓ Successfully triggered {episode_label} via AIOStreams")
                if self.sonarr and self.sonarr.unmonitor_episode(episode_id):
                    logger.info(f"Unmonitored {episode_label} in Sonarr")
                self.storage.mark_processed(f"episode_{episode_id}", success=True)
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
                            "quality": stream.get("quality", "Unknown"),
                            "stream_title": stream.get("title", ""),
                        },
                    )
                return True

        logger.error(f"All {attempts} stream attempts failed for {episode_label}")
        self.storage.mark_processed(f"episode_{episode_id}", success=False)
        if self.notifier:
            self.notifier.collect_failure(
                media_type="episode",
                title=episode_label,
                reason=f"All {attempts} stream attempts failed",
                details={
                    "imdb_id": imdb_id,
                    "season": season_number,
                    "episode": episode_number,
                },
            )
        return False

    def _is_excluded_stream(self, stream: dict[str, Any]) -> bool:
        """Return True if the stream matches any configured exclusion pattern."""
        if not self.config.excluded_stream_patterns:
            return False
        candidates = [c for c in [stream.get("filename", ""), stream.get("title", "")] if c]
        logger.debug(f"Checking exclusion patterns {self.config.excluded_stream_patterns} against: {candidates}")
        for pattern in self.config.excluded_stream_patterns:
            try:
                compiled = re.compile(pattern)
                for candidate in candidates:
                    if compiled.search(candidate):
                        logger.debug(f"Exclusion pattern '{pattern}' matched: '{candidate}'")
                        return True
            except re.error as e:
                logger.warning(f"Invalid exclusion pattern '{pattern}': {e}")
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

        # Strip [Cloud] prefix added by AIOStreams for library items — RD stores the bare filename
        clean_filename = re.sub(r"^\[Cloud\]\s*", "", filename, flags=re.IGNORECASE)
        if clean_filename != filename:
            logger.info(f"Stripped [Cloud] prefix: '{filename}' -> '{clean_filename}'")

        logger.info(f"Waiting 15s then verifying in Real-Debrid for: {clean_filename}")
        time.sleep(15)

        torrents = self.rd_client.list_torrents()
        if torrents is None:
            logger.warning("RD API error during verification, assuming HEAD trigger succeeded")
            return True

        # Find the matching torrent by filename, then fetch its full info to check original_filename
        logger.debug(f"Checking {len(torrents)} RD torrents for match against: {clean_filename}")
        filename_lower = clean_filename.lower()
        for torrent in torrents:
            torrent_filename = torrent.get("filename", "")
            torrent_filename_lower = torrent_filename.lower()
            if filename_lower in torrent_filename_lower or torrent_filename_lower in filename_lower:
                torrent_id = torrent.get("id")
                # Fetch full info to get original_filename (not available in list endpoint)
                torrent_info = self.rd_client.get_torrent_info(torrent_id) if torrent_id else None
                original_filename = torrent_info.get("original_filename", "") if torrent_info else ""
                logger.debug(f"RD torrent '{torrent_filename}' | original_filename: '{original_filename}'")

                # Check both the display filename and the original torrent folder name
                check_name = original_filename or torrent_filename
                if self._is_excluded_stream({"filename": check_name, "title": check_name}):
                    logger.warning(
                        f"Excluded RD torrent found: original='{original_filename}' "
                        f"display='{torrent_filename}' — deleting from RD"
                    )
                    if torrent_id:
                        self.rd_client.delete_torrent(torrent_id)
                    return False
                logger.info(f"Verified in Real-Debrid: {torrent_filename} (original: {original_filename or 'same'})")
                return True

        logger.warning(
            f"Not found in Real-Debrid after trigger: {clean_filename}\n"
            f"  RD has {len(torrents)} torrents. First 5 filenames:\n"
            + "\n".join(f"    - {t.get('filename', '')}" for t in torrents[:5])
        )
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
        import subprocess

        try:
            logger.info(f"Triggering AIOStreams download via curl to: {url[:100]}...")
            result = subprocess.run(
                [
                    "curl",
                    "-s",
                    "-o",
                    "/dev/null",
                    "-w",
                    "%{http_code}",
                    "-L",
                    "--max-time",
                    "30",
                    "-A",
                    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    "-H",
                    "Accept: */*",
                    url,
                ],
                capture_output=True,
                text=True,
                timeout=35,
            )
            status = int(result.stdout.strip())
            if status >= 400:
                logger.error(f"AIOStreams download trigger failed with HTTP {status}: {url[:100]}...")
                return False
            logger.info(f"Successfully triggered download for {title}")
            return True
        except Exception as e:
            logger.error(f"Error triggering AIOStreams download: {e}")
            return False
