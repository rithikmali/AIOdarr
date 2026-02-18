# Stream Retry with Real-Debrid Verification

**Date**: 2026-02-19

## Problem

`_filter_streams` in `aiostreams.py` requires `videoHash` in `behaviorHints`. Valid cached RD streams may lack this field, so the filter returns empty even when streams are available. This causes "No cached streams found" warnings despite real results existing.

## Solution

Remove the `videoHash` requirement and replace it with a retry loop that triggers streams one at a time, verifying each via the Real-Debrid API before moving on.

## Architecture

### 1. Filter Changes (`src/clients/aiostreams.py`)

Remove the `videoHash` check from `_filter_streams`. Keep only the cached indicator check (⚡/RD+/[RD]). Capture `behaviorHints.filename` in the returned stream dict for use during RD verification.

### 2. Config (`src/config.py`)

Add optional `REALDEBRID_API_KEY` env var. RD verification activates only when this key is present.

### 3. RealDebridClient (`src/clients/realdebrid.py`)

Add `list_torrents()` method: calls `GET /rest/1.0/torrents` and returns the list. Each item has a `filename` field.

### 4. Retry Loop (`src/media_processor.py`)

Wire in `RealDebridClient` when `REALDEBRID_API_KEY` is configured.

New `_try_stream(stream, label) -> bool`:
- Triggers HEAD request to AIOStreams playback URL
- If RD client configured: waits 5s, calls `list_torrents()`, checks if `stream['filename']` appears in any torrent's `filename` (case-insensitive)
- Returns `True` on verified success

Both `_process_movie` and `_process_episode` replace single-stream logic with a loop:
- Iterate up to `min(3, len(streams))` streams
- Call `_try_stream` on each
- Stop on first success, proceed to failure handling if all 3 miss

## Data Flow

```
AIOStreams search → filter (cached indicator only, + capture filename)
  → for each stream (up to 3):
      HEAD trigger → wait 5s → RD list_torrents()
        → filename match? → success (unmonitor + Discord)
        → no match?       → try next stream
  → all failed → mark failure
```

## Error Handling

- If `list_torrents()` errors, fall back to treating HEAD success as sufficient (graceful degradation)
- If fewer than 3 streams available, attempt all of them
- Failure after all attempts: mark processed with `success=False`, collect Discord failure notification

## Testing

- Unit tests for `_filter_streams` without `videoHash` requirement
- Unit tests for `list_torrents()` on `RealDebridClient`
- Unit tests for `_try_stream` covering: success on first, success on second, all fail
- Mock `list_torrents()` to return matching/non-matching torrent lists
