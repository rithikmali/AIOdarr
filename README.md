# AIODarr - AIOStreams-Radarr Bridge

Automatically adds wanted movies from Radarr to Real-Debrid using AIOStreams for torrent discovery.

## Overview

This service bridges the gap between Radarr and AIOStreams, automatically:
1. Monitors Radarr for wanted movies
2. Searches AIOStreams for cached Real-Debrid torrents
3. Adds the best quality match to Real-Debrid
4. Lets Zurg create symlinks automatically
5. Radarr imports the movie when it detects the file

## Prerequisites

- **Python 3.13** or higher
- **uv** - Fast Python package installer
- **Radarr** - Media management (v3+)
- **AIOStreams** - Configured with Real-Debrid API key
- **Real-Debrid** - Debrid service account
- **Zurg + rclone** - Mounted Real-Debrid filesystem

## Installation

### 1. Install uv (if not already installed)

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 2. Clone/Download

```bash
git clone <repository-url>
cd aiodarr
```

### 3. Configure Environment

```bash
cp .env.example .env
nano .env  # Edit with your settings
```

Required configuration:
```env
RADARR_URL=http://localhost:7878
RADARR_API_KEY=your_radarr_api_key

AIOSTREAMS_URL=http://localhost:8080

REALDEBRID_API_KEY=your_realdebrid_api_key
```

**Getting API Keys:**
- **Radarr**: Settings → General → Security → API Key
- **Real-Debrid**: https://real-debrid.com/apitoken

### 4. Install Dependencies

```bash
uv sync
```

Or use the provided run script:
```bash
./run.sh
```

## Usage

### Running the Service

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
│ AIOStreams  │ ← Returns cached RD streams
└──────┬──────┘
       │
       ↓
┌─────────────┐
│Real-Debrid  │ ← Adds torrent to account
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
- Verify AIOStreams is configured with Real-Debrid API key
- Check AIOStreams is working: `curl http://your-aiostreams/stream/movie/tt0133093.json`
- Ensure movie is available on Real-Debrid (check manually in Stremio)

### Movies not importing to Radarr
- Verify Zurg + rclone mount is working
- Check Radarr's root folder path matches Zurg mount
- Look at Radarr logs for import errors

### Service keeps retrying same movie
- Movie might not be cached on Real-Debrid
- Check `RETRY_FAILED_HOURS` setting (increase if needed)
- Verify IMDB ID is correct in Radarr

## Development

### Running Tests

```bash
uv run pytest tests/ -v
```

With coverage:
```bash
uv run pytest tests/ -v --cov=src --cov-report=term-missing
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
    ├── aiostreams.py   # AIOStreams API
    └── realdebrid.py   # Real-Debrid API
```

## License

MIT License - See LICENSE file

## Support

For issues or questions, please open an issue on GitHub.
