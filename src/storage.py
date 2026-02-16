from datetime import datetime
from typing import Any


class ProcessedMoviesStorage:
    """In-memory storage for tracking processed movies"""

    def __init__(self):
        self.processed: dict[int, dict[str, Any]] = {}

    def mark_processed(self, movie_id: int, success: bool) -> None:
        """
        Mark a movie as processed

        Args:
            movie_id: Radarr movie ID
            success: Whether processing was successful
        """
        self.processed[movie_id] = {"time": datetime.now(), "success": success}

    def should_skip(self, movie_id: int, retry_hours: int = 24) -> bool:
        """
        Check if a movie should be skipped

        Args:
            movie_id: Radarr movie ID
            retry_hours: Hours to wait before retrying failed movies

        Returns:
            True if movie should be skipped, False otherwise
        """
        if movie_id not in self.processed:
            return False

        entry = self.processed[movie_id]

        # Always skip successful movies
        if entry["success"]:
            return True

        # Skip recent failures
        hours_since = (datetime.now() - entry["time"]).total_seconds() / 3600
        return hours_since < retry_hours

    def get_stats(self) -> dict[str, int]:
        """
        Get statistics about processed movies

        Returns:
            Dict with total, successful, and failed counts
        """
        successful = sum(1 for entry in self.processed.values() if entry["success"])
        failed = sum(1 for entry in self.processed.values() if not entry["success"])

        return {"total": len(self.processed), "successful": successful, "failed": failed}
