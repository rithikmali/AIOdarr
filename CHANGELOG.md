# Changelog

All notable changes to this project will be documented in this file.

## [2.0.0] - 2026-02-16

### Added
- **Sonarr support** for TV shows
  - Process wanted episodes from Sonarr
  - Search AIOStreams for cached episode torrents
  - Unmonitor episodes after successful download
- **Flexible configuration**
  - Can use Radarr only, Sonarr only, or both
  - At least one must be configured
- **MediaProcessor** class that handles both movies and TV shows
- **SonarrClient** for Sonarr API interactions
- **Episode search** in AIOStreams client (`/stream/series/{imdb}:{season}:{episode}`)
- Comprehensive configuration guide (CONFIGURATION.md)
- Docker build tested with new changes

### Changed
- Renamed from "Radarr Bridge" to "Radarr/Sonarr Bridge"
- Updated main.py to use MediaProcessor instead of MovieProcessor
- Config now validates at least one service is configured
- Updated documentation to reflect both services
- Docker compose includes Sonarr environment variables

### Technical Details
- Storage uses composite keys for episodes (`episode_{id}`)
- Same retry logic applies to both movies and episodes
- Both services share the same poll interval

## [1.0.0] - 2026-02-16

### Added
- Initial release
- Radarr API client for fetching wanted movies
- AIOStreams API client for searching cached torrents
- Trigger downloads via AIOStreams playback URL (HEAD request)
- Main processor with retry logic
- In-memory storage for tracking processed movies
- Configurable polling interval
- Comprehensive logging
- Unit and integration tests (39 tests, 95%+ coverage)
- Docker support with multi-platform builds (amd64, arm64)
- GitHub Actions CI/CD for automatic builds
- Documentation and setup scripts

### Features
- Automatic detection of wanted movies from Radarr
- Trigger AIOStreams to add torrents to Real-Debrid
- Unmonitor movies in Radarr after successful download
- Retry logic for failed downloads
- Statistics tracking
- Environment-based configuration
- Non-root Docker container
- Published to GitHub Container Registry

### Removed
- Direct Real-Debrid API integration (uses AIOStreams instead)
- Real-Debrid API key requirement (encoded in AIOStreams manifest)
