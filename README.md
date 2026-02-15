# AIODarr - AIOStreams-Radarr/Sonarr Bridge

Automatically adds wanted movies and TV shows from Radarr/Sonarr to Real-Debrid using AIOStreams.

## Overview

This service bridges the gap between Radarr/Sonarr and AIOStreams, automatically:
1. Monitors Radarr for wanted movies and/or Sonarr for wanted episodes
2. Searches AIOStreams for cached Real-Debrid torrents
3. Triggers AIOStreams to add the torrent to Real-Debrid
4. Unmonitors the media in Radarr/Sonarr
5. Zurg creates symlinks automatically
6. Radarr/Sonarr imports the media when it detects the file

## How It Works

Instead of managing Real-Debrid API calls directly, this service leverages AIOStreams' existing integration:
- Makes a HEAD request to the AIOStreams playback URL
- AIOStreams handles adding the torrent to your Real-Debrid account
- No need for separate Real-Debrid API keys (already encoded in your AIOStreams manifest)

## Prerequisites

- **Radarr** (optional) - Movie management (v3+)
- **Sonarr** (optional) - TV show management (v3+)
- **At least one** of Radarr or Sonarr must be configured
- **AIOStreams** - Configured with Real-Debrid (via Stremio manifest URL)
- **Real-Debrid** - Debrid service account (configured in AIOStreams)
- **Zurg + rclone** - Mounted Real-Debrid filesystem
- **Docker** (recommended) or **Python 3.13+** with **uv**

## Installation

### Option 1: Docker (Recommended)

#### Using Docker Compose

1. Clone the repository:
```bash
git clone https://github.com/yourusername/aiodarr.git
cd aiodarr
```

2. Create `.env` file:
```bash
cp .env.example .env
nano .env  # Edit with your settings
```

3. Start the service:
```bash
docker-compose up -d
```

#### Using Docker CLI

```bash
docker run -d \
  --name aiodarr \
  --restart unless-stopped \
  -e RADARR_URL=http://radarr:7878 \
  -e RADARR_API_KEY=your_radarr_api_key \
  -e AIOSTREAMS_URL=https://aiostreams.elfhosted.com/your_config/ \
  ghcr.io/yourusername/aiodarr:latest
```

#### Using Pre-built Image

```bash
docker pull ghcr.io/yourusername/aiodarr:latest
```

### Option 2: Python/uv

1. Install uv:
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

2. Clone and configure:
```bash
git clone https://github.com/yourusername/aiodarr.git
cd aiodarr
cp .env.example .env
nano .env  # Edit with your settings
```

3. Install dependencies:
```bash
uv sync
```

Or use the run script:
```bash
./run.sh
```

## Configuration

Required environment variables:
```env
RADARR_URL=http://localhost:7878
RADARR_API_KEY=your_radarr_api_key

# Your Stremio manifest URL with "/manifest.json" removed
AIOSTREAMS_URL=https://aiostreams.elfhosted.com/eyJkZWJyaWRBcGlLZXkiOiJ.../
```

**Getting Configuration Values:**
- **Radarr API Key**: Settings → General → Security → API Key
- **AIOStreams URL**: Take your Stremio manifest URL and remove `/manifest.json` from the end
  - Example Stremio URL: `https://aiostreams.elfhosted.com/eyJ.../manifest.json`
  - Use this: `https://aiostreams.elfhosted.com/eyJ.../`
  - Make sure it ends with a `/`

## Usage

### Docker

**View logs:**
```bash
docker-compose logs -f
# or
docker logs -f aiodarr
```

**Stop service:**
```bash
docker-compose down
```

**Update to latest version:**
```bash
docker-compose pull
docker-compose up -d
```

### Python/uv

**Option 1: Using run script (recommended)**
```bash
./run.sh
```

**Option 2: Direct with uv**
```bash
uv run python -m src.main
```

**Option 3: As systemd service**

Create `/etc/systemd/system/aiodarr.service`:
```ini
[Unit]
Description=AIODarr - AIOStreams-Radarr Bridge
After=network.target

[Service]
Type=simple
User=your_user
WorkingDirectory=/path/to/aiodarr
ExecStart=/home/your_user/.cargo/bin/uv run python -m src.main
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable aiodarr
sudo systemctl start aiodarr
sudo systemctl status aiodarr
```

### Monitoring Logs

**When running directly:**
Logs appear in console with timestamps

**When running as systemd service:**
```bash
sudo journalctl -u aiodarr -f
```

## How It Works

```
┌─────────────┐
│  Radarr     │ ← Service polls every 10 minutes
│  (Wanted)   │
└──────┬──────┘
       │
       ↓
┌─────────────┐
│   Service   │ ← Searches for cached torrents
│   Queries   │
└──────┬──────┘
       │
       ↓
┌─────────────┐
│ AIOStreams  │ ← Returns cached streams with playback URLs
└──────┬──────┘
       │
       ↓
┌─────────────┐
│   Service   │ ← Makes HEAD request to trigger download
│   Triggers  │
└──────┬──────┘
       │
       ↓
┌─────────────┐
│ AIOStreams  │ ← Adds torrent to Real-Debrid automatically
└──────┬──────┘
       │
       ↓
┌─────────────┐
│   Service   │ ← Unmonitors movie in Radarr
└──────┬──────┘
       │
       ↓
┌─────────────┐
│    Zurg     │ ← Creates symlinks automatically
└──────┬──────┘
       │
       ↓
┌─────────────┐
│   Radarr    │ ← Detects file and imports
│  (Import)   │
└─────────────┘
```

## Configuration Options

| Variable | Default | Description |
|----------|---------|-------------|
| `POLL_INTERVAL_MINUTES` | `10` | How often to check Radarr |
| `RETRY_FAILED_HOURS` | `24` | Wait time before retrying failed movies |
| `LOG_LEVEL` | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR) |

## Troubleshooting

### No streams found
- Verify your AIOStreams URL includes the encoded config (not just the base URL)
- Test manually: `curl "${AIOSTREAMS_URL}/stream/movie/tt0133093.json"`
- Should return JSON with cached streams marked with ⚡

### Movies not being added to Real-Debrid
- Check AIOStreams logs for errors
- Verify your Real-Debrid account is properly configured in AIOStreams
- Make sure the stream has a `url` field in the AIOStreams response

### Movies not importing to Radarr
- Verify Zurg + rclone mount is working
- Check Radarr's root folder path matches Zurg mount
- Look at Radarr logs for import errors
- Movies are unmonitored after processing, so they won't re-download

### Service keeps retrying same movie
- Movie might not be cached on Real-Debrid
- Check `RETRY_FAILED_HOURS` setting (increase if needed)
- Verify IMDB ID is correct in Radarr

## Development

### Running Tests

```bash
uv run python -m pytest tests/ -v
```

With coverage:
```bash
uv run python -m pytest tests/ -v --cov=src --cov-report=term-missing
```

### Project Structure

```
src/
├── main.py              # Entry point
├── config.py            # Configuration
├── processor.py         # Business logic
├── storage.py           # Track processed movies
└── clients/
    ├── radarr.py       # Radarr API
    └── aiostreams.py   # AIOStreams API
```

## License

MIT License - See LICENSE file

## Support

For issues or questions, please open an issue on GitHub.
