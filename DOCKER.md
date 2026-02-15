# Docker Deployment Guide

## Quick Start

### Using Docker Compose (Recommended)

1. Create `docker-compose.yml`:
```yaml
version: '3.8'

services:
  aiodarr:
    image: ghcr.io/yourusername/aiodarr:latest
    container_name: aiodarr
    restart: unless-stopped
    environment:
      - RADARR_URL=http://radarr:7878
      - RADARR_API_KEY=your_radarr_api_key
      - AIOSTREAMS_URL=https://aiostreams.elfhosted.com/your_config/
      - POLL_INTERVAL_MINUTES=10
      - RETRY_FAILED_HOURS=24
      - LOG_LEVEL=INFO
```

2. Start the service:
```bash
docker-compose up -d
```

### Using Docker CLI

```bash
docker run -d \
  --name aiodarr \
  --restart unless-stopped \
  -e RADARR_URL=http://radarr:7878 \
  -e RADARR_API_KEY=your_radarr_api_key \
  -e AIOSTREAMS_URL=https://aiostreams.elfhosted.com/your_config/ \
  -e POLL_INTERVAL_MINUTES=10 \
  -e RETRY_FAILED_HOURS=24 \
  -e LOG_LEVEL=INFO \
  ghcr.io/yourusername/aiodarr:latest
```

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `RADARR_URL` | Yes | - | URL of your Radarr instance |
| `RADARR_API_KEY` | Yes | - | Radarr API key |
| `AIOSTREAMS_URL` | Yes | - | AIOStreams manifest URL (without /manifest.json) |
| `POLL_INTERVAL_MINUTES` | No | `10` | How often to check Radarr for wanted movies |
| `RETRY_FAILED_HOURS` | No | `24` | Hours to wait before retrying failed movies |
| `LOG_LEVEL` | No | `INFO` | Log level (DEBUG, INFO, WARNING, ERROR) |

## Docker Tags

- `latest` - Latest stable release from main branch
- `v1.0.0` - Specific version (semantic versioning)
- `main` - Latest build from main branch
- `main-sha-abc123` - Specific commit from main branch

## Networking

### Accessing Local Services

If Radarr is running on the host machine, use:
- **Linux**: `http://172.17.0.1:7878` (Docker bridge IP)
- **macOS/Windows**: `http://host.docker.internal:7878`

### Using Docker Network

```yaml
services:
  radarr:
    image: linuxserver/radarr
    container_name: radarr
    networks:
      - media

  aiodarr:
    image: ghcr.io/yourusername/aiodarr:latest
    container_name: aiodarr
    environment:
      - RADARR_URL=http://radarr:7878  # Use service name
    networks:
      - media

networks:
  media:
    driver: bridge
```

## Managing the Container

### View Logs
```bash
# Docker Compose
docker-compose logs -f

# Docker CLI
docker logs -f aiodarr
```

### Restart Container
```bash
# Docker Compose
docker-compose restart

# Docker CLI
docker restart aiodarr
```

### Stop Container
```bash
# Docker Compose
docker-compose down

# Docker CLI
docker stop aiodarr
docker rm aiodarr
```

### Update to Latest Version
```bash
# Docker Compose
docker-compose pull
docker-compose up -d

# Docker CLI
docker pull ghcr.io/yourusername/aiodarr:latest
docker stop aiodarr
docker rm aiodarr
# Then run the docker run command again
```

## Building from Source

### Build Local Image
```bash
docker build -t aiodarr:local .
```

### Build for Multiple Platforms
```bash
docker buildx build --platform linux/amd64,linux/arm64 -t aiodarr:local .
```

## Troubleshooting

### Container Exits Immediately
Check logs for configuration errors:
```bash
docker logs aiodarr
```

Common issues:
- Missing required environment variables
- Invalid AIOSTREAMS_URL format
- Cannot reach Radarr (check networking)

### Permission Issues
The container runs as user `aiodarr` (UID 1000). If you mount volumes, ensure they're readable by UID 1000.

### Network Connectivity
Test if container can reach Radarr:
```bash
docker exec aiodarr curl -I http://radarr:7878
```

## Health Check

Add health check to your docker-compose.yml:
```yaml
services:
  aiodarr:
    image: ghcr.io/yourusername/aiodarr:latest
    healthcheck:
      test: ["CMD", "python3", "-c", "import sys; sys.exit(0)"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 10s
```

## Security

- Container runs as non-root user (UID 1000)
- No privileged mode required
- Only requires network access (no volume mounts needed)
- Environment variables for sensitive data (consider using Docker secrets for production)
