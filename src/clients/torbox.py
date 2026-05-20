import logging

import requests

logger = logging.getLogger(__name__)


class TorBoxClient:
    """Client for interacting with the TorBox API."""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.torbox.app/v1/api"
        self.headers = {"Authorization": f"Bearer {api_key}"}

    def _log_curl(
        self,
        method: str,
        url: str,
        json: dict | None = None,
    ) -> None:
        """Log the equivalent curl command, redacting the Bearer token."""
        parts = [
            "curl",
            "-X",
            method,
            "--max-time 30",
            "-H 'Authorization: Bearer ***'",
        ]
        if json is not None:
            parts.extend([
                "-H 'Content-Type: application/json'",
                f"--data '{json}'",
            ])
        parts.append(f"'{url}'")
        logger.info("Equivalent curl command:\n  %s", " ".join(parts))

    def list_torrents(self) -> list[dict] | None:
        """List TorBox torrents, or None on API failure."""
        url = f"{self.base_url}/torrents/mylist"
        self._log_curl("GET", url)
        try:
            response = requests.get(url, headers=self.headers, timeout=30)
            response.raise_for_status()
            data = response.json()
            if isinstance(data, dict):
                if not data.get("success", True):
                    logger.warning("TorBox /torrents/mylist returned success=false: %s", data)
                    return None
                if isinstance(data.get("data"), list):
                    return data["data"]
            if isinstance(data, list):
                return data
            logger.warning(
                "Unexpected TorBox torrent list response shape: %s",
                type(data).__name__,
            )
            return None
        except Exception as e:
            logger.error(f"Error listing TorBox torrents: {e}")
            return None

    def delete_torrent(self, torrent_id: int | str) -> bool:
        """Delete a torrent from TorBox."""
        url = f"{self.base_url}/torrents/controltorrent"
        payload = {"torrent_id": int(torrent_id), "operation": "delete"}
        self._log_curl("POST", url, json=payload)
        try:
            response = requests.post(
                url,
                headers={**self.headers, "Content-Type": "application/json"},
                json=payload,
                timeout=30,
            )
            response.raise_for_status()
            logger.info(f"Deleted torrent {torrent_id} from TorBox")
            return True
        except Exception as e:
            logger.error(f"Error deleting torrent {torrent_id} from TorBox: {e}")
            return False
