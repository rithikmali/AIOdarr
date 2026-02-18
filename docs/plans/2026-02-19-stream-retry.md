# Stream Retry with Real-Debrid Verification Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Remove the `videoHash` filter from stream selection and add a retry loop (up to 3 streams) that verifies each attempt via the Real-Debrid API by matching `behaviorHints.filename`.

**Architecture:** `_filter_streams` is loosened to accept any cached-indicator stream and captures `filename`. `RealDebridClient` gains `list_torrents()`. `MediaProcessor` wires in an optional `RealDebridClient` and a new `_try_stream()` method that triggers via HEAD then waits 5s and checks RD `/torrents` for a filename match. Both `_process_movie` and `_process_episode` replace single-stream logic with a loop over up to 3 streams.

**Tech Stack:** Python, requests, pytest + unittest.mock. Run all tests with `uv run pytest`. Lint with `uv run ruff check --fix src/ tests/ && uv run ruff format src/ tests/`.

---

### Task 1: Loosen `_filter_streams` — remove `videoHash` requirement, capture `filename`

**Files:**
- Modify: `src/clients/aiostreams.py:82-109`
- Modify: `tests/test_aiostreams.py`

**Step 1: Write the failing test**

Add to `tests/test_aiostreams.py` (after the existing tests):

```python
def test_filter_streams_includes_cached_stream_without_video_hash(aio_client):
    """Streams with cached indicator but no videoHash must be included after fix"""
    streams = [
        {
            "name": "    [RD⚡️]\n    4K🔥UHD",
            "description": "    🎬 Shrinking S03 • E04\n    🖥 ᴡᴇʙ-ᴅʟ | 2160p",
            "url": "https://aiostreams.elfhosted.com/playback/test",
            "behaviorHints": {
                "filename": "Shrinking S03E04 The Field 2160p ATVP WEB-DL DDP5 1 DV H 265-NTb.mkv",
                "videoSize": 6697557046,
            },
        }
    ]
    result = aio_client._filter_streams(streams)
    assert len(result) == 1
    assert result[0]["filename"] == "Shrinking S03E04 The Field 2160p ATVP WEB-DL DDP5 1 DV H 265-NTb.mkv"


def test_filter_streams_captures_empty_filename_when_absent(aio_client):
    """filename defaults to empty string when behaviorHints has no filename"""
    streams = [
        {
            "name": "[RD+] Movie 1080p",
            "description": "1080p",
            "url": "https://example.com/playback/test",
            "behaviorHints": {"videoHash": "abc123"},
        }
    ]
    result = aio_client._filter_streams(streams)
    assert len(result) == 1
    assert result[0]["filename"] == ""
```

**Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/test_aiostreams.py::test_filter_streams_includes_cached_stream_without_video_hash tests/test_aiostreams.py::test_filter_streams_captures_empty_filename_when_absent -v
```

Expected: FAIL — first test fails because current code skips streams without `videoHash`; second fails because `filename` key is absent from result.

**Step 3: Update `_filter_streams` in `src/clients/aiostreams.py`**

Replace lines 82–109 (the entire `_filter_streams` method):

```python
def _filter_streams(self, streams: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Filter streams for cached Real-Debrid results."""
    cached_streams = []
    for stream in streams:
        # AIOStreams uses 'name' field, fallback to 'title'
        title = stream.get("name") or stream.get("title", "")
        description = stream.get("description", "")

        # Check for cached indicators (⚡ or RD in title/name)
        if not ("⚡" in title or "RD+" in title or "[RD]" in title):
            continue

        behavior_hints = stream.get("behaviorHints", {})
        cached_streams.append(
            {
                "title": title,
                "url": stream.get("url"),
                "infoHash": stream.get("infoHash"),
                "filename": behavior_hints.get("filename", ""),
                "quality": self._parse_quality(description or title),
            }
        )

    return cached_streams
```

**Step 4: Run all aiostreams tests to verify they pass**

```bash
uv run pytest tests/test_aiostreams.py -v
```

Expected: All PASS.

**Step 5: Commit**

```bash
git add src/clients/aiostreams.py tests/test_aiostreams.py
git commit -m "feat: loosen stream filter — remove videoHash requirement, capture filename"
```

---

### Task 2: Add `REALDEBRID_API_KEY` to config

**Files:**
- Modify: `src/config.py:28-31`
- Modify: `tests/test_config.py`

**Step 1: Write the failing test**

Read `tests/test_config.py` first, then add at the end:

```python
def test_config_realdebrid_api_key_from_env(monkeypatch):
    """REALDEBRID_API_KEY is loaded when set"""
    monkeypatch.setenv("AIOSTREAMS_URL", "http://aiostreams")
    monkeypatch.setenv("RADARR_URL", "http://radarr")
    monkeypatch.setenv("RADARR_API_KEY", "test-key")
    monkeypatch.setenv("REALDEBRID_API_KEY", "rd-secret-key")

    config = Config()

    assert config.realdebrid_api_key == "rd-secret-key"


def test_config_realdebrid_api_key_defaults_empty(monkeypatch):
    """REALDEBRID_API_KEY defaults to empty string when not set"""
    monkeypatch.setenv("AIOSTREAMS_URL", "http://aiostreams")
    monkeypatch.setenv("RADARR_URL", "http://radarr")
    monkeypatch.setenv("RADARR_API_KEY", "test-key")
    monkeypatch.delenv("REALDEBRID_API_KEY", raising=False)

    config = Config()

    assert config.realdebrid_api_key == ""
```

**Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/test_config.py::test_config_realdebrid_api_key_from_env tests/test_config.py::test_config_realdebrid_api_key_defaults_empty -v
```

Expected: FAIL — `Config` has no `realdebrid_api_key` attribute.

**Step 3: Add `realdebrid_api_key` to `src/config.py`**

Add after the `discord_webhook_url` line (around line 30):

```python
self.realdebrid_api_key = os.getenv("REALDEBRID_API_KEY", "")
```

**Step 4: Run config tests**

```bash
uv run pytest tests/test_config.py -v
```

Expected: All PASS.

**Step 5: Commit**

```bash
git add src/config.py tests/test_config.py
git commit -m "feat: add optional REALDEBRID_API_KEY to config"
```

---

### Task 3: Add `list_torrents()` to `RealDebridClient`

**Files:**
- Modify: `src/clients/realdebrid.py`
- Modify: `tests/test_realdebrid.py`

**Step 1: Write the failing tests**

Add to `tests/test_realdebrid.py` (after existing tests):

```python
@patch("requests.get")
def test_list_torrents_returns_torrent_list(mock_get, rd_client):
    """list_torrents returns list of torrent dicts from RD API"""
    mock_response = Mock()
    mock_response.json.return_value = [
        {
            "id": "abc123",
            "filename": "Shrinking S03E04 The Field 2160p ATVP WEB-DL DDP5 1 DV H 265-NTb.mkv",
            "hash": "deadbeef",
            "status": "downloaded",
        },
        {
            "id": "def456",
            "filename": "Breaking Bad S01E01 1080p WEB-DL.mkv",
            "hash": "cafebabe",
            "status": "downloaded",
        },
    ]
    mock_response.raise_for_status = Mock()
    mock_get.return_value = mock_response

    torrents = rd_client.list_torrents()

    assert len(torrents) == 2
    assert torrents[0]["filename"] == "Shrinking S03E04 The Field 2160p ATVP WEB-DL DDP5 1 DV H 265-NTb.mkv"
    mock_get.assert_called_once_with(
        "https://api.real-debrid.com/rest/1.0/torrents",
        headers={"Authorization": "Bearer test_api_key"},
    )


@patch("requests.get")
def test_list_torrents_returns_empty_on_error(mock_get, rd_client):
    """list_torrents returns empty list on API error"""
    mock_get.side_effect = Exception("API Error")

    torrents = rd_client.list_torrents()

    assert torrents == []
```

**Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/test_realdebrid.py::test_list_torrents_returns_torrent_list tests/test_realdebrid.py::test_list_torrents_returns_empty_on_error -v
```

Expected: FAIL — `RealDebridClient` has no `list_torrents` method.

**Step 3: Add `list_torrents()` to `src/clients/realdebrid.py`**

Add after the `check_torrent_status` method:

```python
def list_torrents(self) -> list[dict]:
    """
    List all torrents in Real-Debrid account

    Returns:
        List of torrent dicts (each has 'filename', 'hash', 'status', etc.)
    """
    try:
        response = requests.get(
            f"{self.base_url}/torrents",
            headers=self.headers,
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"Error listing torrents: {e}")
        return []
```

**Step 4: Run realdebrid tests**

```bash
uv run pytest tests/test_realdebrid.py -v
```

Expected: All PASS.

**Step 5: Commit**

```bash
git add src/clients/realdebrid.py tests/test_realdebrid.py
git commit -m "feat: add list_torrents to RealDebridClient"
```

---

### Task 4: Add `_try_stream()` to `MediaProcessor` and wire `RealDebridClient`

**Files:**
- Modify: `src/media_processor.py`
- Modify: `tests/test_media_processor.py`

**Step 1: Write the failing tests**

Add to `tests/test_media_processor.py` (after existing tests):

```python
@patch("src.media_processor.SonarrClient")
@patch("src.media_processor.RadarrClient")
@patch("src.media_processor.AIOStreamsClient")
def test_try_stream_returns_true_on_trigger_success_no_rd(
    mock_aiostreams, mock_radarr, mock_sonarr, monkeypatch
):
    """_try_stream returns True when trigger succeeds and no RD client configured"""
    monkeypatch.setenv("AIOSTREAMS_URL", "http://aiostreams")
    monkeypatch.setenv("RADARR_URL", "http://radarr")
    monkeypatch.setenv("RADARR_API_KEY", "test-key")
    monkeypatch.delenv("REALDEBRID_API_KEY", raising=False)

    config = Config()
    processor = MediaProcessor(config)

    stream = {"title": "Show S01E01 1080p", "url": "http://stream-url", "filename": "Show.S01E01.mkv"}

    with patch.object(processor, "_trigger_aiostreams_download", return_value=True):
        result = processor._try_stream(stream, "Show S01E01")

    assert result is True
    assert processor.rd_client is None


@patch("src.media_processor.SonarrClient")
@patch("src.media_processor.RadarrClient")
@patch("src.media_processor.AIOStreamsClient")
def test_try_stream_returns_false_on_no_url(
    mock_aiostreams, mock_radarr, mock_sonarr, monkeypatch
):
    """_try_stream returns False immediately when stream has no URL"""
    monkeypatch.setenv("AIOSTREAMS_URL", "http://aiostreams")
    monkeypatch.setenv("RADARR_URL", "http://radarr")
    monkeypatch.setenv("RADARR_API_KEY", "test-key")
    monkeypatch.delenv("REALDEBRID_API_KEY", raising=False)

    config = Config()
    processor = MediaProcessor(config)

    stream = {"title": "Show S01E01 1080p", "url": "", "filename": "Show.S01E01.mkv"}

    with patch.object(processor, "_trigger_aiostreams_download") as mock_trigger:
        result = processor._try_stream(stream, "Show S01E01")

    assert result is False
    mock_trigger.assert_not_called()


@patch("src.media_processor.SonarrClient")
@patch("src.media_processor.RadarrClient")
@patch("src.media_processor.AIOStreamsClient")
def test_try_stream_returns_true_when_rd_verifies_filename(
    mock_aiostreams, mock_radarr, mock_sonarr, monkeypatch
):
    """_try_stream returns True when RD list_torrents contains matching filename"""
    monkeypatch.setenv("AIOSTREAMS_URL", "http://aiostreams")
    monkeypatch.setenv("RADARR_URL", "http://radarr")
    monkeypatch.setenv("RADARR_API_KEY", "test-key")
    monkeypatch.setenv("REALDEBRID_API_KEY", "rd-key")

    config = Config()

    with patch("src.media_processor.RealDebridClient") as mock_rd_class:
        mock_rd = Mock()
        mock_rd_class.return_value = mock_rd
        mock_rd.list_torrents.return_value = [
            {"filename": "Shrinking S03E04 The Field 2160p ATVP WEB-DL DDP5 1 DV H 265-NTb.mkv", "status": "downloaded"}
        ]

        processor = MediaProcessor(config)

        stream = {
            "title": "[RD⚡️] 4K",
            "url": "http://stream-url",
            "filename": "Shrinking S03E04 The Field 2160p ATVP WEB-DL DDP5 1 DV H 265-NTb.mkv",
        }

        with patch.object(processor, "_trigger_aiostreams_download", return_value=True):
            with patch("time.sleep"):
                result = processor._try_stream(stream, "Shrinking S03E04")

    assert result is True
    mock_rd.list_torrents.assert_called_once()


@patch("src.media_processor.SonarrClient")
@patch("src.media_processor.RadarrClient")
@patch("src.media_processor.AIOStreamsClient")
def test_try_stream_returns_false_when_rd_misses_filename(
    mock_aiostreams, mock_radarr, mock_sonarr, monkeypatch
):
    """_try_stream returns False when RD list_torrents does not contain matching filename"""
    monkeypatch.setenv("AIOSTREAMS_URL", "http://aiostreams")
    monkeypatch.setenv("RADARR_URL", "http://radarr")
    monkeypatch.setenv("RADARR_API_KEY", "test-key")
    monkeypatch.setenv("REALDEBRID_API_KEY", "rd-key")

    config = Config()

    with patch("src.media_processor.RealDebridClient") as mock_rd_class:
        mock_rd = Mock()
        mock_rd_class.return_value = mock_rd
        mock_rd.list_torrents.return_value = [
            {"filename": "Some.Other.Movie.mkv", "status": "downloaded"}
        ]

        processor = MediaProcessor(config)

        stream = {
            "title": "[RD⚡️] 4K",
            "url": "http://stream-url",
            "filename": "Shrinking S03E04 The Field 2160p ATVP WEB-DL DDP5 1 DV H 265-NTb.mkv",
        }

        with patch.object(processor, "_trigger_aiostreams_download", return_value=True):
            with patch("time.sleep"):
                result = processor._try_stream(stream, "Shrinking S03E04")

    assert result is False
```

**Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/test_media_processor.py::test_try_stream_returns_true_on_trigger_success_no_rd tests/test_media_processor.py::test_try_stream_returns_false_on_no_url tests/test_media_processor.py::test_try_stream_returns_true_when_rd_verifies_filename tests/test_media_processor.py::test_try_stream_returns_false_when_rd_misses_filename -v
```

Expected: FAIL — `_try_stream` and `rd_client` don't exist yet.

**Step 3: Update `src/media_processor.py`**

Add import at top (after existing imports):

```python
import time

from src.clients.realdebrid import RealDebridClient
```

In `__init__`, after the Discord notifier block (after line 37):

```python
        # Initialize Real-Debrid client for stream verification if configured
        self.rd_client: RealDebridClient | None = None
        if config.realdebrid_api_key:
            self.rd_client = RealDebridClient(config.realdebrid_api_key)
            logger.info("Real-Debrid client initialized for stream verification")
```

Add new method before `_trigger_aiostreams_download`:

```python
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
```

**Step 4: Run new tests**

```bash
uv run pytest tests/test_media_processor.py::test_try_stream_returns_true_on_trigger_success_no_rd tests/test_media_processor.py::test_try_stream_returns_false_on_no_url tests/test_media_processor.py::test_try_stream_returns_true_when_rd_verifies_filename tests/test_media_processor.py::test_try_stream_returns_false_when_rd_misses_filename -v
```

Expected: All PASS.

**Step 5: Run full test suite to check for regressions**

```bash
uv run pytest -v
```

Expected: All existing tests still PASS (no retry loop changes yet — `_process_movie` and `_process_episode` still use the old single-stream path).

**Step 6: Commit**

```bash
git add src/media_processor.py tests/test_media_processor.py
git commit -m "feat: add _try_stream with RD verification and wire RealDebridClient"
```

---

### Task 5: Replace single-stream logic in `_process_movie` with retry loop

**Files:**
- Modify: `src/media_processor.py:134-182`
- Modify: `tests/test_media_processor.py` (update 2 tests, add 2 new tests)

**Step 1: Write the new tests and update broken ones**

Add new tests to `tests/test_media_processor.py`:

```python
@patch("src.media_processor.SonarrClient")
@patch("src.media_processor.RadarrClient")
@patch("src.media_processor.AIOStreamsClient")
def test_process_movie_retries_and_succeeds_on_second_stream(
    mock_aiostreams_class, mock_radarr_class, mock_sonarr, monkeypatch
):
    """_process_movie tries next stream if first fails verification"""
    monkeypatch.setenv("AIOSTREAMS_URL", "http://aiostreams")
    monkeypatch.setenv("RADARR_URL", "http://radarr")
    monkeypatch.setenv("RADARR_API_KEY", "test-key")
    monkeypatch.delenv("DISCORD_WEBHOOK_URL", raising=False)
    monkeypatch.delenv("REALDEBRID_API_KEY", raising=False)

    config = Config()

    mock_radarr = mock_radarr_class.return_value
    mock_radarr.unmonitor_movie.return_value = True

    mock_aiostreams = mock_aiostreams_class.return_value
    mock_aiostreams.search_movie.return_value = [
        {"title": "Movie 4K", "url": "http://stream-1", "filename": "Movie.4K.mkv"},
        {"title": "Movie 1080p", "url": "http://stream-2", "filename": "Movie.1080p.mkv"},
    ]

    config = Config()
    processor = MediaProcessor(config)

    # First stream fails, second succeeds
    call_count = 0

    def mock_try_stream(stream, label):
        nonlocal call_count
        call_count += 1
        return call_count == 2  # Second call returns True

    with patch.object(processor, "_try_stream", side_effect=mock_try_stream):
        movie = {"id": 1, "title": "Movie", "year": 2024, "imdbId": "tt1234567"}
        result = processor._process_movie(movie)

    assert result is True
    assert call_count == 2
    mock_radarr.unmonitor_movie.assert_called_once_with(1)


@patch("src.media_processor.SonarrClient")
@patch("src.media_processor.RadarrClient")
@patch("src.media_processor.AIOStreamsClient")
def test_process_movie_fails_after_max_retries(
    mock_aiostreams_class, mock_radarr_class, mock_sonarr, monkeypatch
):
    """_process_movie fails after trying all available streams (up to 3)"""
    monkeypatch.setenv("AIOSTREAMS_URL", "http://aiostreams")
    monkeypatch.setenv("RADARR_URL", "http://radarr")
    monkeypatch.setenv("RADARR_API_KEY", "test-key")
    monkeypatch.delenv("DISCORD_WEBHOOK_URL", raising=False)
    monkeypatch.delenv("REALDEBRID_API_KEY", raising=False)

    config = Config()
    mock_aiostreams = mock_aiostreams_class.return_value
    mock_aiostreams.search_movie.return_value = [
        {"title": "Movie 4K", "url": "http://stream-1", "filename": "Movie.4K.mkv"},
        {"title": "Movie 1080p", "url": "http://stream-2", "filename": "Movie.1080p.mkv"},
        {"title": "Movie 720p", "url": "http://stream-3", "filename": "Movie.720p.mkv"},
        {"title": "Movie 480p", "url": "http://stream-4", "filename": "Movie.480p.mkv"},
    ]

    processor = MediaProcessor(config)

    call_count = 0

    def mock_try_stream(stream, label):
        nonlocal call_count
        call_count += 1
        return False  # All fail

    with patch.object(processor, "_try_stream", side_effect=mock_try_stream):
        movie = {"id": 1, "title": "Movie", "year": 2024, "imdbId": "tt1234567"}
        result = processor._process_movie(movie)

    assert result is False
    assert call_count == 3  # Capped at 3, not 4
```

Also update the two tests that check failure reasons that will change. Find and update `test_process_movie_calls_collect_failure_on_no_playback_url`:

Change the assertion from:
```python
assert "No playback URL" in call_args[1]["reason"]
```
to:
```python
assert "stream attempts failed" in call_args[1]["reason"]
```

Find and update `test_process_movie_calls_collect_failure_on_download_failed`:

Change the assertion from:
```python
assert "Download trigger failed" in call_args[1]["reason"]
```
to:
```python
assert "stream attempts failed" in call_args[1]["reason"]
```

**Step 2: Run modified tests to verify they fail**

```bash
uv run pytest tests/test_media_processor.py::test_process_movie_retries_and_succeeds_on_second_stream tests/test_media_processor.py::test_process_movie_fails_after_max_retries tests/test_media_processor.py::test_process_movie_calls_collect_failure_on_no_playback_url tests/test_media_processor.py::test_process_movie_calls_collect_failure_on_download_failed -v
```

Expected: new tests FAIL (no retry loop); assertion-updated tests also FAIL (still old reason text).

**Step 3: Replace single-stream logic in `_process_movie`**

Replace the section from `# Use first stream from AIOStreams` to the end of the method (lines ~134–182 in `src/media_processor.py`) with:

```python
        attempts = min(3, len(streams))
        logger.info(f"Found {len(streams)} cached streams, will try up to {attempts}")

        for i, stream in enumerate(streams[:attempts]):
            logger.info(f"Attempt {i + 1}/{attempts}: {stream['title']}")
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
```

**Step 4: Run all media processor tests**

```bash
uv run pytest tests/test_media_processor.py -v
```

Expected: All PASS.

**Step 5: Run full test suite**

```bash
uv run pytest -v
```

Expected: All PASS.

**Step 6: Commit**

```bash
git add src/media_processor.py tests/test_media_processor.py
git commit -m "feat: replace single-stream logic in _process_movie with 3-attempt retry loop"
```

---

### Task 6: Replace single-stream logic in `_process_episode` with retry loop

**Files:**
- Modify: `src/media_processor.py:246-296`
- Modify: `tests/test_media_processor.py` (update 2 tests, add 2 new tests)

**Step 1: Write the new tests and update broken ones**

Add new tests to `tests/test_media_processor.py`:

```python
@patch("src.media_processor.SonarrClient")
@patch("src.media_processor.RadarrClient")
@patch("src.media_processor.AIOStreamsClient")
def test_process_episode_retries_and_succeeds_on_second_stream(
    mock_aiostreams_class, mock_radarr, mock_sonarr_class, monkeypatch
):
    """_process_episode tries next stream if first fails verification"""
    monkeypatch.setenv("AIOSTREAMS_URL", "http://aiostreams")
    monkeypatch.setenv("SONARR_URL", "http://sonarr")
    monkeypatch.setenv("SONARR_API_KEY", "test-key")
    monkeypatch.delenv("DISCORD_WEBHOOK_URL", raising=False)
    monkeypatch.delenv("REALDEBRID_API_KEY", raising=False)

    config = Config()

    mock_sonarr = mock_sonarr_class.return_value
    mock_sonarr.unmonitor_episode.return_value = True

    mock_aiostreams = mock_aiostreams_class.return_value
    mock_aiostreams.search_episode.return_value = [
        {"title": "Show 4K", "url": "http://stream-1", "filename": "Show.S01E01.4K.mkv"},
        {"title": "Show 1080p", "url": "http://stream-2", "filename": "Show.S01E01.1080p.mkv"},
    ]

    processor = MediaProcessor(config)

    call_count = 0

    def mock_try_stream(stream, label):
        nonlocal call_count
        call_count += 1
        return call_count == 2

    with patch.object(processor, "_try_stream", side_effect=mock_try_stream):
        episode = {
            "id": 1,
            "seasonNumber": 1,
            "episodeNumber": 1,
            "title": "Pilot",
            "series": {"title": "Breaking Bad", "imdbId": "tt0959621"},
        }
        result = processor._process_episode(episode)

    assert result is True
    assert call_count == 2
    mock_sonarr.unmonitor_episode.assert_called_once_with(1)


@patch("src.media_processor.SonarrClient")
@patch("src.media_processor.RadarrClient")
@patch("src.media_processor.AIOStreamsClient")
def test_process_episode_fails_after_max_retries(
    mock_aiostreams_class, mock_radarr, mock_sonarr_class, monkeypatch
):
    """_process_episode fails after trying all streams (up to 3)"""
    monkeypatch.setenv("AIOSTREAMS_URL", "http://aiostreams")
    monkeypatch.setenv("SONARR_URL", "http://sonarr")
    monkeypatch.setenv("SONARR_API_KEY", "test-key")
    monkeypatch.delenv("DISCORD_WEBHOOK_URL", raising=False)
    monkeypatch.delenv("REALDEBRID_API_KEY", raising=False)

    config = Config()

    mock_aiostreams = mock_aiostreams_class.return_value
    mock_aiostreams.search_episode.return_value = [
        {"title": "Show 4K", "url": "http://stream-1", "filename": "Show.4K.mkv"},
        {"title": "Show 1080p", "url": "http://stream-2", "filename": "Show.1080p.mkv"},
        {"title": "Show 720p", "url": "http://stream-3", "filename": "Show.720p.mkv"},
        {"title": "Show 480p", "url": "http://stream-4", "filename": "Show.480p.mkv"},
    ]

    processor = MediaProcessor(config)

    call_count = 0

    def mock_try_stream(stream, label):
        nonlocal call_count
        call_count += 1
        return False

    with patch.object(processor, "_try_stream", side_effect=mock_try_stream):
        episode = {
            "id": 1,
            "seasonNumber": 1,
            "episodeNumber": 1,
            "title": "Pilot",
            "series": {"title": "Breaking Bad", "imdbId": "tt0959621"},
        }
        result = processor._process_episode(episode)

    assert result is False
    assert call_count == 3
```

Also update the two episode tests that check failure reasons. Find and update `test_process_episode_calls_collect_failure_on_no_playback_url`:

Change:
```python
assert "No playback URL" in call_args[1]["reason"]
```
to:
```python
assert "stream attempts failed" in call_args[1]["reason"]
```

Find and update `test_process_episode_calls_collect_failure_on_download_failed`:

Change:
```python
assert "Download trigger failed" in call_args[1]["reason"]
```
to:
```python
assert "stream attempts failed" in call_args[1]["reason"]
```

**Step 2: Run modified/new tests to verify they fail**

```bash
uv run pytest tests/test_media_processor.py::test_process_episode_retries_and_succeeds_on_second_stream tests/test_media_processor.py::test_process_episode_fails_after_max_retries tests/test_media_processor.py::test_process_episode_calls_collect_failure_on_no_playback_url tests/test_media_processor.py::test_process_episode_calls_collect_failure_on_download_failed -v
```

Expected: new tests FAIL; updated assertions also FAIL.

**Step 3: Replace single-stream logic in `_process_episode`**

Replace the section from `# Use first stream` to end of `_process_episode` (lines ~246–296) with:

```python
        attempts = min(3, len(streams))
        logger.info(f"Found {len(streams)} cached streams, will try up to {attempts}")

        for i, stream in enumerate(streams[:attempts]):
            logger.info(f"Attempt {i + 1}/{attempts}: {stream['title']}")
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
```

**Step 4: Run all tests**

```bash
uv run pytest -v
```

Expected: All PASS.

**Step 5: Lint and format**

```bash
uv run ruff check --fix src/ tests/ && uv run ruff format src/ tests/
```

**Step 6: Run tests once more after lint**

```bash
uv run pytest -v
```

Expected: All PASS.

**Step 7: Commit**

```bash
git add src/media_processor.py tests/test_media_processor.py
git commit -m "feat: replace single-stream logic in _process_episode with 3-attempt retry loop"
```
