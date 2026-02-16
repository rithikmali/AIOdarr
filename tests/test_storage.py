from datetime import datetime, timedelta

import pytest

from src.storage import ProcessedMoviesStorage


@pytest.fixture
def storage():
    return ProcessedMoviesStorage()


def test_storage_initialization(storage):
    """Test storage initializes with empty dict"""
    assert storage.processed == {}


def test_mark_success(storage):
    """Test marking movie as successfully processed"""
    storage.mark_processed(1, success=True)

    assert 1 in storage.processed
    assert storage.processed[1]["success"] is True
    assert isinstance(storage.processed[1]["time"], datetime)


def test_mark_failed(storage):
    """Test marking movie as failed"""
    storage.mark_processed(2, success=False)

    assert 2 in storage.processed
    assert storage.processed[2]["success"] is False


def test_should_skip_successful_movie(storage):
    """Test that successful movies are skipped"""
    storage.mark_processed(1, success=True)

    assert storage.should_skip(1) is True


def test_should_skip_recent_failure(storage):
    """Test that recent failures are skipped"""
    storage.mark_processed(2, success=False)

    assert storage.should_skip(2, retry_hours=24) is True


def test_should_not_skip_old_failure(storage):
    """Test that old failures are retried"""
    storage.mark_processed(3, success=False)

    # Manually set time to 25 hours ago
    storage.processed[3]["time"] = datetime.now() - timedelta(hours=25)

    assert storage.should_skip(3, retry_hours=24) is False


def test_should_not_skip_new_movie(storage):
    """Test that new movies are not skipped"""
    assert storage.should_skip(999) is False


def test_get_stats(storage):
    """Test getting storage statistics"""
    storage.mark_processed(1, success=True)
    storage.mark_processed(2, success=True)
    storage.mark_processed(3, success=False)

    stats = storage.get_stats()

    assert stats["total"] == 3
    assert stats["successful"] == 2
    assert stats["failed"] == 1
