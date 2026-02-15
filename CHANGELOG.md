# Changelog

All notable changes to this project will be documented in this file.

## [1.0.0] - 2026-02-16

### Added
- Initial release
- Radarr API client for fetching wanted movies
- AIOStreams API client for searching cached torrents
- Real-Debrid API client for adding magnets
- Main processor with retry logic
- In-memory storage for tracking processed movies
- Configurable polling interval
- Comprehensive logging
- Unit and integration tests (35 tests, 95% coverage)
- Documentation and setup scripts

### Features
- Automatic detection of wanted movies from Radarr
- Quality-based stream selection (prefers higher quality)
- Retry logic for failed downloads
- Statistics tracking
- Environment-based configuration
