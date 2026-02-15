# Deployment Instructions

## GitHub Container Registry Setup

When you push this code to GitHub, the Docker image will automatically be built and published to GitHub Container Registry (ghcr.io).

### First-Time Setup

1. **Push code to GitHub:**
```bash
git remote add origin https://github.com/yourusername/aiodarr.git
git push -u origin main
```

2. **Enable GitHub Actions:**
   - Go to your repository on GitHub
   - Navigate to "Settings" → "Actions" → "General"
   - Enable "Read and write permissions" for workflows
   - Enable "Allow GitHub Actions to create and approve pull requests"

3. **First build will trigger automatically:**
   - The workflow runs on push to `main` branch
   - Image will be published to `ghcr.io/yourusername/aiodarr:latest`

4. **Make your image public (optional):**
   - Go to your package on GitHub (ghcr.io/yourusername/aiodarr)
   - Click "Package settings"
   - Change visibility to "Public"

### Using Your Docker Image

Once published, anyone can pull your image:

```bash
docker pull ghcr.io/yourusername/aiodarr:latest
```

## Deployment Options

### Option 1: Docker Compose (Recommended)

Create `docker-compose.yml`:
```yaml
version: '3.8'

services:
  aiodarr:
    image: ghcr.io/yourusername/aiodarr:latest
    container_name: aiodarr
    restart: unless-stopped
    environment:
      - RADARR_URL=http://radarr:7878
      - RADARR_API_KEY=${RADARR_API_KEY}
      - AIOSTREAMS_URL=${AIOSTREAMS_URL}
      - POLL_INTERVAL_MINUTES=10
      - RETRY_FAILED_HOURS=24
      - LOG_LEVEL=INFO
```

Create `.env`:
```env
RADARR_API_KEY=your_radarr_api_key
AIOSTREAMS_URL=https://aiostreams.elfhosted.com/your_config/
```

Deploy:
```bash
docker-compose up -d
```

### Option 2: Kubernetes

Create `aiodarr-deployment.yaml`:
```yaml
apiVersion: v1
kind: Secret
metadata:
  name: aiodarr-secrets
type: Opaque
stringData:
  radarr-api-key: "your_radarr_api_key"
  aiostreams-url: "https://aiostreams.elfhosted.com/your_config/"
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: aiodarr
spec:
  replicas: 1
  selector:
    matchLabels:
      app: aiodarr
  template:
    metadata:
      labels:
        app: aiodarr
    spec:
      containers:
      - name: aiodarr
        image: ghcr.io/yourusername/aiodarr:latest
        env:
        - name: RADARR_URL
          value: "http://radarr:7878"
        - name: RADARR_API_KEY
          valueFrom:
            secretKeyRef:
              name: aiodarr-secrets
              key: radarr-api-key
        - name: AIOSTREAMS_URL
          valueFrom:
            secretKeyRef:
              name: aiodarr-secrets
              key: aiostreams-url
        - name: POLL_INTERVAL_MINUTES
          value: "10"
        - name: LOG_LEVEL
          value: "INFO"
        resources:
          requests:
            memory: "128Mi"
            cpu: "100m"
          limits:
            memory: "256Mi"
            cpu: "500m"
```

Deploy:
```bash
kubectl apply -f aiodarr-deployment.yaml
```

### Option 3: Portainer

1. Go to Portainer → Stacks → Add stack
2. Paste the docker-compose.yml content
3. Add environment variables
4. Deploy

### Option 4: Unraid

1. Go to Docker tab
2. Add Container
3. Fill in:
   - Repository: `ghcr.io/yourusername/aiodarr:latest`
   - Add environment variables as needed

## Updating

### Automatic Updates (Watchtower)

Add watchtower to your docker-compose.yml:
```yaml
services:
  watchtower:
    image: containrrr/watchtower
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
    command: --interval 3600 --cleanup
```

### Manual Update
```bash
docker-compose pull
docker-compose up -d
```

## Monitoring

### View Logs
```bash
docker-compose logs -f aiodarr
```

### Check Status
```bash
docker-compose ps
```

### Restart
```bash
docker-compose restart aiodarr
```

## Production Considerations

1. **Resource Limits**: Set appropriate CPU/memory limits
2. **Logging**: Configure log rotation to prevent disk fill
3. **Monitoring**: Use tools like Prometheus/Grafana
4. **Backups**: Not needed (stateless service)
5. **Secrets**: Use Docker secrets or external secret management
6. **Network**: Use dedicated Docker network for media stack

## Troubleshooting

See [DOCKER.md](DOCKER.md) for detailed troubleshooting guide.

Quick checks:
```bash
# Check if container is running
docker ps | grep aiodarr

# View recent logs
docker logs --tail 50 aiodarr

# Check environment variables
docker inspect aiodarr | grep -A 20 Env

# Test Radarr connectivity
docker exec aiodarr curl -I http://radarr:7878
```
