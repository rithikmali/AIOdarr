import logging
import time

import requests

logger = logging.getLogger(__name__)


class RealDebridClient:
    """Client for interacting with Real-Debrid API"""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.real-debrid.com/rest/1.0"
        self.headers = {"Authorization": f"Bearer {api_key}"}

    def _log_curl(self, method: str, url: str, data: dict | None = None) -> None:
        """Log the equivalent curl command, redacting the Bearer token."""
        parts = ["curl", "-X", method, "--max-time 30"]
        parts.append("-H 'Authorization: Bearer ***'")
        if data:
            for key, value in data.items():
                parts.append(f"--data-urlencode '{key}={value}'")
        parts.append(f"'{url}'")
        logger.info(f"Equivalent curl command:\n  {' '.join(parts)}")

    def add_magnet(self, magnet_or_infohash: str) -> str | None:
        """
        Add a magnet/torrent to Real-Debrid

        Args:
            magnet_or_infohash: Magnet URL or infohash string

        Returns:
            Torrent ID if successful, None otherwise
        """
        # Convert infohash to magnet if needed
        if not magnet_or_infohash.startswith("magnet:"):
            magnet = f"magnet:?xt=urn:btih:{magnet_or_infohash}"
        else:
            magnet = magnet_or_infohash

        try:
            # Step 1: Add magnet to Real-Debrid
            response = requests.post(
                f"{self.base_url}/torrents/addMagnet", headers=self.headers, data={"magnet": magnet}
            )
            response.raise_for_status()
            torrent_info = response.json()
            torrent_id = torrent_info["id"]

            logger.info(f"Added magnet to Real-Debrid: {torrent_id}")

            # Step 2: Wait briefly and get torrent info
            time.sleep(2)
            response = requests.get(
                f"{self.base_url}/torrents/info/{torrent_id}", headers=self.headers
            )
            response.raise_for_status()
            info = response.json()

            # Step 3: Select all files if needed
            if info["status"] == "waiting_files_selection":
                file_ids = ",".join([str(f["id"]) for f in info["files"]])
                requests.post(
                    f"{self.base_url}/torrents/selectFiles/{torrent_id}",
                    headers=self.headers,
                    data={"files": file_ids},
                )
                logger.info(f"Selected all files for torrent {torrent_id}")

            return torrent_id

        except Exception as e:
            logger.error(f"Error adding to Real-Debrid: {e}")
            return None

    def check_torrent_status(self, torrent_id: str) -> str | None:
        """
        Check torrent download status

        Args:
            torrent_id: Real-Debrid torrent ID

        Returns:
            Status string (downloaded, downloading, queued, etc.) or None on error
        """
        try:
            response = requests.get(
                f"{self.base_url}/torrents/info/{torrent_id}", headers=self.headers
            )
            response.raise_for_status()
            info = response.json()
            return info["status"]
        except Exception as e:
            logger.error(f"Error checking torrent status: {e}")
            return None

    def list_torrents(self) -> list[dict] | None:
        """
        List all torrents in Real-Debrid account

        Returns:
            List of torrent dicts (each has 'filename', 'hash', 'status', etc.),
            or None if the API request failed (allows callers to distinguish
            between an empty account and an API error)
        """
        url = f"{self.base_url}/torrents"
        self._log_curl("GET", url)
        try:
            response = requests.get(
                url,
                headers=self.headers,
                timeout=30,
            )
            response.raise_for_status()
            if not response.content:
                logger.warning(f"RD /torrents returned HTTP {response.status_code} with empty body")
                return None
            return response.json()
        except Exception as e:
            logger.error(f"Error listing torrents: {e}")
            return None
