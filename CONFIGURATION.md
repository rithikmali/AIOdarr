# Configuration Guide

## Environment Variables

### Required Configuration

At least **one** of Radarr or Sonarr must be configured:

```env
# AIOStreams (Required)
AIOSTREAMS_URL=https://aiostreams.elfhosted.com/your_config/
```

### Optional Media Servers

Configure one or both:

```env
# Radarr (for movies)
RADARR_URL=http://localhost:7878
RADARR_API_KEY=your_radarr_api_key

# Sonarr (for TV shows)
SONARR_URL=http://localhost:8989
SONARR_API_KEY=your_sonarr_api_key
```

### Optional Settings

```env
POLL_INTERVAL_MINUTES=10    # How often to check for wanted media
RETRY_FAILED_HOURS=24        # Wait time before retrying failed downloads
LOG_LEVEL=INFO               # DEBUG, INFO, WARNING, ERROR
```

### Discord Notifications (Optional)

Send notifications to a Discord channel when media is successfully processed or when failures occur.

```env
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/YOUR_WEBHOOK_ID/YOUR_WEBHOOK_TOKEN
```

**Setup:**
1. Open your Discord server
2. Go to **Server Settings → Integrations → Webhooks**
3. Click **New Webhook**
4. Choose a channel and copy the **Webhook URL**
5. Set the `DISCORD_WEBHOOK_URL` environment variable

**Behavior:**
- **Success notifications** are sent immediately when a movie or episode is added
- **Failure notifications** are batched and sent as a summary at the end of each polling cycle
- If the webhook URL is not set, notifications are silently disabled
- Webhook errors never block media processing

## Configuration Examples

### Movies Only (Radarr)

```env
RADARR_URL=http://radarr:7878
RADARR_API_KEY=abc123...
AIOSTREAMS_URL=https://aiostreams.elfhosted.com/eyJ.../
```

### TV Shows Only (Sonarr)

```env
SONARR_URL=http://sonarr:8989
SONARR_API_KEY=xyz789...
AIOSTREAMS_URL=https://aiostreams.elfhosted.com/eyJ.../
```

### Both Movies and TV Shows

```env
# Movies
RADARR_URL=http://radarr:7878
RADARR_API_KEY=abc123...

# TV Shows
SONARR_URL=http://sonarr:8989
SONARR_API_KEY=xyz789...

# AIOStreams
AIOSTREAMS_URL=https://aiostreams.elfhosted.com/eyJ.../
```

## Getting API Keys

### Radarr API Key
1. Open Radarr web interface
2. Go to Settings → General
3. Scroll to Security section
4. Copy the API Key

### Sonarr API Key
1. Open Sonarr web interface
2. Go to Settings → General
3. Scroll to Security section
4. Copy the API Key

### AIOStreams URL
1. Open Stremio
2. Go to Addons → AIOStreams
3. Copy your manifest URL
4. Remove `/manifest.json` from the end
5. Ensure it ends with `/`

Example transformation:
```
From: https://aiostreams.elfhosted.com/eyJkZWJy.../manifest.json
To:   https://aiostreams.elfhosted.com/eyJkZWJy.../
```

## Docker Configuration

### Docker Compose with Both Services

```yaml
version: '3.8'

services:
  aiodarr:
    image: ghcr.io/yourusername/aiodarr:latest
    container_name: aiodarr
    restart: unless-stopped
    environment:
      # Movies
      - RADARR_URL=http://radarr:7878
      - RADARR_API_KEY=${RADARR_API_KEY}
      # TV Shows
      - SONARR_URL=http://sonarr:8989
      - SONARR_API_KEY=${SONARR_API_KEY}
      # AIOStreams
      - AIOSTREAMS_URL=${AIOSTREAMS_URL}
      # Optional
      - POLL_INTERVAL_MINUTES=10
      - RETRY_FAILED_HOURS=24
      - LOG_LEVEL=INFO
    networks:
      - media

  radarr:
    image: linuxserver/radarr
    container_name: radarr
    networks:
      - media
    # ... other radarr config

  sonarr:
    image: linuxserver/sonarr
    container_name: sonarr
    networks:
      - media
    # ... other sonarr config

networks:
  media:
    driver: bridge
```

### Docker Run with Both Services

```bash
docker run -d \
  --name aiodarr \
  --restart unless-stopped \
  -e RADARR_URL=http://radarr:7878 \
  -e RADARR_API_KEY=your_radarr_key \
  -e SONARR_URL=http://sonarr:8989 \
  -e SONARR_API_KEY=your_sonarr_key \
  -e AIOSTREAMS_URL=https://aiostreams.elfhosted.com/config/ \
  ghcr.io/yourusername/aiodarr:latest
```

## Networking Considerations

### Same Docker Network
If all services are on the same Docker network, use service names:
```env
RADARR_URL=http://radarr:7878
SONARR_URL=http://sonarr:8989
```

### Host Network
If services are on the host machine:

**Linux:**
```env
RADARR_URL=http://172.17.0.1:7878
SONARR_URL=http://172.17.0.1:8989
```

**macOS/Windows:**
```env
RADARR_URL=http://host.docker.internal:7878
SONARR_URL=http://host.docker.internal:8989
```

### Different Hosts
If services are on different machines:
```env
RADARR_URL=http://192.168.1.10:7878
SONARR_URL=http://192.168.1.11:8989
```

## Validation

The service will validate on startup:
- At least one of Radarr or Sonarr is configured
- All required fields are present
- URLs are properly formatted

Error messages will indicate what's missing.

## Advanced Configuration

### Different Poll Intervals
You can't set different intervals for movies vs TV shows, but you can run two instances:

**Movies instance:**
```yaml
services:
  aiodarr-movies:
    image: ghcr.io/yourusername/aiodarr:latest
    environment:
      - RADARR_URL=http://radarr:7878
      - RADARR_API_KEY=${RADARR_API_KEY}
      - AIOSTREAMS_URL=${AIOSTREAMS_URL}
      - POLL_INTERVAL_MINUTES=5  # Check movies every 5 min
```

**TV Shows instance:**
```yaml
  aiodarr-tv:
    image: ghcr.io/yourusername/aiodarr:latest
    environment:
      - SONARR_URL=http://sonarr:8989
      - SONARR_API_KEY=${SONARR_API_KEY}
      - AIOSTREAMS_URL=${AIOSTREAMS_URL}
      - POLL_INTERVAL_MINUTES=15  # Check TV every 15 min
```

### Logging Levels

- **DEBUG**: Verbose output, shows all processing steps
- **INFO**: Standard output, shows what's being processed (default)
- **WARNING**: Only warnings and errors
- **ERROR**: Only errors

## Troubleshooting

### Service won't start
Check logs for configuration errors:
```bash
docker logs aiodarr
```

Common issues:
- Neither Radarr nor Sonarr configured
- Invalid API keys
- Malformed URLs (missing http://, trailing slashes issues)

### Movies work but TV shows don't
- Verify Sonarr is accessible: `curl http://sonarr:8989/api/v3/system/status?apikey=YOUR_KEY`
- Check Sonarr logs for import issues
- Ensure episodes have IMDB IDs (required for AIOStreams)

### TV shows work but movies don't
- Verify Radarr is accessible: `curl http://radarr:7878/api/v3/system/status?apikey=YOUR_KEY`
- Check Radarr logs for import issues
- Ensure movies have IMDB IDs

### Nothing is being processed
- Check poll interval (might be waiting)
- Verify wanted list has items: Check Radarr/Sonarr "Wanted" page
- Check AIOStreams has cached torrents for your content
- Review logs for errors
