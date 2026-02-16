# Discord Notifications Design

**Date**: 2026-02-16
**Status**: Approved

## Overview

Add Discord webhook notifications to AIODarr to alert when media is successfully added or fails to process. Notifications provide detailed information including title, quality, stream metadata, and failure reasons.

## Requirements

- Accept Discord webhook URL from `DISCORD_WEBHOOK_URL` environment variable (optional)
- Send immediate notifications for successful downloads with detailed metadata
- Batch failure notifications and send summary at end of poll cycle
- Include detailed information: title, quality, stream info, IMDB ID, failure reasons
- Gracefully handle webhook failures without affecting media processing
- Keep tests fast and focused

## Architecture

### New Component

`DiscordNotifier` class in `src/notifiers/discord.py`

### Integration Points

- **Config**: Loads optional `DISCORD_WEBHOOK_URL` env var
- **MediaProcessor**: Initializes `DiscordNotifier` (or None if webhook not configured)
- **Processing Methods**: `_process_movie()` and `_process_episode()` call notifier methods after processing
- **Poll Cycle**: `process_all()` triggers batch failure summary at end of cycle

### Message Flow

1. **Immediate success**: When processing succeeds, immediately send rich Discord embed with media details
2. **Batched failures**: When processing fails, collect failure details in memory during poll cycle
3. **End of cycle**: After processing all media, send one summary embed with all failures

### Graceful Degradation

- If webhook URL not configured, all notifier methods are no-ops
- If webhook calls fail, log error and continue processing
- Webhook failures never block media downloads

## Components

### DiscordNotifier Class

**Location**: `src/notifiers/discord.py`

**Methods**:
```python
class DiscordNotifier:
    def __init__(self, webhook_url: str | None)
    def notify_success(self, media_type: str, title: str, details: dict) -> None
    def collect_failure(self, media_type: str, title: str, reason: str, details: dict) -> None
    def send_failure_summary(self) -> None
    def _send_webhook(self, embed: dict) -> bool
    def _format_success_embed(self, media_type: str, title: str, details: dict) -> dict
    def _format_failure_summary_embed(self, failures: list) -> dict
```

**Key Data**:
- `webhook_url`: Discord webhook URL (None if disabled)
- `failures`: List accumulating failures during current poll cycle

### Config Changes

**File**: `src/config.py`

Add optional configuration:
```python
self.discord_webhook_url = os.getenv("DISCORD_WEBHOOK_URL", "")
```

### MediaProcessor Changes

**File**: `src/media_processor.py`

**Initialization**:
```python
self.notifier: DiscordNotifier | None = None
if config.discord_webhook_url:
    self.notifier = DiscordNotifier(config.discord_webhook_url)
```

**Success Notifications**:
- Call `notifier.notify_success()` in `_process_movie()` after successful processing
- Call `notifier.notify_success()` in `_process_episode()` after successful processing

**Failure Collection**:
- Call `notifier.collect_failure()` after failed processing in both methods

**Batch Summary**:
- Call `notifier.send_failure_summary()` at end of `process_all()`

### Discord Embed Format

**Success** (Green):
- ✓ icon and success message
- Media title with year/season/episode info
- Quality (parsed from stream description)
- Stream title
- IMDB ID
- Timestamp

**Failure Summary** (Red):
- ✗ icon and failure summary header
- Count of failed items
- List of failures grouped by media type
- Each failure shows: title, reason (e.g., "No cached streams", "No IMDB ID", "Download trigger failed")
- Timestamp

## Data Flow

### Success Path (Immediate)

1. `MediaProcessor._process_movie()` finds cached stream and triggers download successfully
2. Method calls `self.notifier.notify_success("movie", title, details)` with:
   - `year`, `imdb_id`, `quality`, `stream_title`
3. `DiscordNotifier.notify_success()` formats green Discord embed
4. Calls `_send_webhook()` which POSTs to Discord webhook URL
5. If webhook fails, logs error but doesn't raise exception
6. Processing continues normally

**Same flow for episodes** with `media_type="episode"` and details: `series_title`, `season`, `episode_number`

### Failure Path (Batched)

1. `MediaProcessor._process_movie()` fails (no streams, no IMDB, download trigger failed)
2. Method calls `self.notifier.collect_failure("movie", title, reason, details)` with reason:
   - "No IMDB ID found"
   - "No cached streams available"
   - "Download trigger failed"
   - "No playback URL in stream"
3. `DiscordNotifier.collect_failure()` appends to `self.failures` list (doesn't send yet)
4. Processing continues

### End of Poll Cycle

1. `MediaProcessor.process_all()` completes processing all movies and episodes
2. Calls `self.notifier.send_failure_summary()`
3. If `self.failures` not empty, formats red embed with grouped failures
4. Sends single webhook message, clears `self.failures` list
5. Logs stats as usual

### Webhook Disabled

If `self.notifier` is None (no webhook configured), all method calls skipped via `if self.notifier:` checks.

## Error Handling

### Webhook Configuration Errors

- If `DISCORD_WEBHOOK_URL` empty/not set: `DiscordNotifier` not initialized, notifications silently skipped
- If webhook URL malformed: Fails on first webhook call, logged as error, processing continues

### Webhook Request Failures

All errors caught in `_send_webhook()`, logged, returns False:
- Network errors (timeout, connection refused)
- HTTP errors (404, 401, 429 rate limit)
- Invalid JSON/payload errors

**Critical**: Webhook failures NEVER raise exceptions that would stop media processing

### Edge Cases

- **Empty failure list**: `send_failure_summary()` checks `if not self.failures:` and returns early
- **Discord rate limiting**: Not explicitly handled initially (hybrid approach naturally reduces message volume)
- **Long failure lists**: Discord embeds have 6000 char limit; truncate with "... and N more failures" if exceeded
- **Missing metadata**: Use `.get()` with defaults when formatting embeds (e.g., `quality = details.get('quality', 'Unknown')`)

### Logging Strategy

- **Debug**: Skipped notifications when webhook not configured
- **Info**: Successful webhook sends
- **Warning**: Webhook send failures
- **Error**: Unexpected exceptions in notification code

### Timeouts

Set 10-second timeout on webhook POST requests to prevent blocking media processing.

## Testing

**Focus**: Fast, focused unit tests with mocked HTTP calls

### Unit Tests for DiscordNotifier

**File**: `tests/test_discord_notifier.py`

- Test `notify_success()` formats correct embed structure (green color, includes all fields)
- Test `collect_failure()` appends to failures list without sending
- Test `send_failure_summary()` sends batched embed and clears list
- Test `send_failure_summary()` skips when failures list empty
- Test webhook disabled case (webhook_url=None) - all methods are no-ops
- Test `_send_webhook()` error handling with mocked `requests.post` failures
- Test embed truncation when failure list exceeds character limit
- Mock `requests.post` to verify correct payload structure

### Integration Tests in MediaProcessor

**File**: `tests/test_media_processor.py`

- Mock DiscordNotifier and verify `notify_success()` called on successful processing
- Mock DiscordNotifier and verify `collect_failure()` called on failed processing
- Verify `send_failure_summary()` called at end of `process_all()`
- Test webhook failures don't affect media processing success/failure

### Config Tests

**File**: `tests/test_config.py`

- Test `DISCORD_WEBHOOK_URL` loads correctly when set
- Test defaults to empty string when not set
- Test MediaProcessor doesn't initialize notifier when webhook URL empty

### Mocking Strategy

- Use `@patch("requests.post")` for webhook HTTP calls
- Use `@patch("src.notifiers.discord.DiscordNotifier")` when testing MediaProcessor integration
- Keep test fixtures minimal and fast

## Implementation Notes

- Use `requests.post()` for webhook calls (consistent with existing HTTP client usage)
- Discord webhook payload format: `{"embeds": [...]}`
- Embed color codes: Green success = `0x00ff00`, Red failure = `0xff0000`
- Quality parsing: Extract from stream `description` field (already done in AIOStreamsClient filtering)
- Clear failure list after sending to avoid duplicate notifications on next cycle
