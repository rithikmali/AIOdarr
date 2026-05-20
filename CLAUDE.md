# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Install dependencies (dev includes pytest, ruff, pre-commit)
uv sync --extra dev

# Run all tests
uv run pytest

# Run a single test file
uv run pytest tests/test_aiostreams.py

# Run a single test function
uv run pytest tests/test_aiostreams.py::test_search_movie_with_cached_streams

# Lint and format
uv run ruff check --fix src/ tests/
uv run ruff format src/ tests/

# Run the service locally
uv run python -m src.main

# Docker build and run
docker build -t aiodarr .
docker compose up
```

## Architecture

AIODarr polls Radarr/Sonarr for wanted media, searches AIOStreams for cached TorBox torrents, and triggers downloads via HEAD requests to AIOStreams playback URLs.

**Flow**: `main.py` (scheduler) → `MediaProcessor` (orchestrator) → clients (`RadarrClient`, `SonarrClient`, `AIOStreamsClient`) + `ProcessedMoviesStorage` (in-memory retry tracking)

- `src/config.py` — Loads env vars. Radarr and Sonarr are independently optional (at least one required). `AIOSTREAMS_URL` is always required.
- `src/media_processor.py` — Central orchestrator. Processes movies and episodes, triggers downloads, unmonitors after success.
- `src/clients/aiostreams.py` — Queries AIOStreams Stremio API. Stream filtering happens in `_filter_streams`: accepts any stream with a playback URL because modern AIOStreams responses no longer expose cached-debrid markers. Quality is parsed from the stream label/description.
- `src/clients/radarr.py` / `src/clients/sonarr.py` — Radarr/Sonarr v3 API clients.
- `src/clients/torbox.py` — Optional TorBox verification client. Used by `MediaProcessor` to confirm a torrent appeared in TorBox after triggering the AIOStreams HEAD request. Only active when `TORBOX_API_KEY` is set.
- `src/storage.py` — In-memory dict tracking processed items with timestamps. Episodes use `episode_{id}` composite keys.

**AIOStreams API endpoints**:
- Movies: `/stream/movie/{imdb_id}.json`
- Episodes: `/stream/series/{imdb_id}:{season}:{episode}.json`

**Download trigger**: HEAD request to the stream's playback URL (not magnet/infohash). This causes AIOStreams to add the torrent to TorBox.

## Testing

Tests use `unittest.mock` with pytest fixtures. External HTTP calls are mocked via `@patch("requests.get")` / `@patch("requests.head")`. Config tests use `monkeypatch.setenv`/`monkeypatch.delenv` to control environment variables.

Pre-commit hooks run ruff lint, ruff format, and pytest on every commit.

## Build

Uses hatchling with `src/` layout. The wheel config `[tool.hatch.build.targets.wheel] packages = ["src"]` is required for this layout. `README.md` must not be in `.dockerignore` since hatchling reads it.
