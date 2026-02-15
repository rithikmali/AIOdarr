import logging
import time
from typing import Optional

import requests

logger = logging.getLogger(__name__)


class RealDebridClient:
    """Client for interacting with Real-Debrid API"""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = 'https://api.real-debrid.com/rest/1.0'
        self.headers = {'Authorization': f'Bearer {api_key}'}

    def add_magnet(self, magnet_or_infohash: str) -> Optional[str]:
        """
        Add a magnet/torrent to Real-Debrid

        Args:
            magnet_or_infohash: Magnet URL or infohash string

        Returns:
            Torrent ID if successful, None otherwise
        """
        # Convert infohash to magnet if needed
        if not magnet_or_infohash.startswith('magnet:'):
            magnet = f'magnet:?xt=urn:btih:{magnet_or_infohash}'
        else:
            magnet = magnet_or_infohash

        try:
            # Step 1: Add magnet to Real-Debrid
            response = requests.post(
                f'{self.base_url}/torrents/addMagnet',
                headers=self.headers,
                data={'magnet': magnet}
            )
            response.raise_for_status()
            torrent_info = response.json()
            torrent_id = torrent_info['id']

            logger.info(f"Added magnet to Real-Debrid: {torrent_id}")

            # Step 2: Wait briefly and get torrent info
            time.sleep(2)
            response = requests.get(
                f'{self.base_url}/torrents/info/{torrent_id}',
                headers=self.headers
            )
            response.raise_for_status()
            info = response.json()

            # Step 3: Select all files if needed
            if info['status'] == 'waiting_files_selection':
                file_ids = ','.join([str(f['id']) for f in info['files']])
                requests.post(
                    f'{self.base_url}/torrents/selectFiles/{torrent_id}',
                    headers=self.headers,
                    data={'files': file_ids}
                )
                logger.info(f"Selected all files for torrent {torrent_id}")

            return torrent_id

        except Exception as e:
            logger.error(f"Error adding to Real-Debrid: {e}")
            return None

    def check_torrent_status(self, torrent_id: str) -> Optional[str]:
        """
        Check torrent download status

        Args:
            torrent_id: Real-Debrid torrent ID

        Returns:
            Status string (downloaded, downloading, queued, etc.) or None on error
        """
        try:
            response = requests.get(
                f'{self.base_url}/torrents/info/{torrent_id}',
                headers=self.headers
            )
            response.raise_for_status()
            info = response.json()
            return info['status']
        except Exception as e:
            logger.error(f"Error checking torrent status: {e}")
            return None
