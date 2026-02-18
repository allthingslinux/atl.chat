# Docker Setup

This guide covers the Docker containerization setup for IRC.atl.chat.

## Overview

IRC.atl.chat uses Docker Compose for orchestration with the following services:

```
Services:
├── atl-irc-server      - Main IRC server
├── atl-irc-services    - IRC services (NickServ, etc.)
├── atl-irc-webpanel    - Web administration interface
└── atl-cert-manager    - SSL certificate automation (Lego)
```

## Container Configuration

### UnrealIRCd Container
```yaml
atl-irc-server:
  build:
    context: ./apps/unrealircd
    dockerfile: Containerfile
  container_name: atl-irc-server
  volumes:
    - ./apps/unrealircd/config:/home/unrealircd/unrealircd/config
    - ./logs/atl-irc-server:/home/unrealircd/unrealircd/logs
    - ./data/atl-irc-server:/home/unrealircd/unrealircd/data
  ports:
    - '6697:6697'    # IRC over TLS
    - '6900:6900'    # Server links
    - '6901:6901'    # Atheme services
    - '8600:8600'    # JSON-RPC API
    - '8000:8000'    # WebSocket IRC
  networks:
    - atl-chat
  restart: unless-stopped
```

### Atheme Container
```yaml
atheme:
  build:
    context: ./apps/atheme
    dockerfile: Containerfile
  container_name: atl-irc-services
  depends_on:
    atl-irc-server:
      condition: service_healthy
  volumes:
    - ./apps/atheme/config:/usr/local/atheme/etc:ro
    - ./data/atheme:/usr/local/atheme/data
    - ./logs/atheme:/usr/local/atheme/logs
  network_mode: service:atl-irc-server  # Shares network with IRCd
  restart: unless-stopped
```

### WebPanel Container
```yaml
atl-irc-webpanel:
  build:
    context: ../../apps/webpanel
    dockerfile: services/webpanel/Containerfile
  container_name: atl-irc-webpanel
  depends_on:
    atl-irc-server:
      condition: service_healthy
  volumes:
    - atl-irc-webpanel-data:/var/www/html/atl-irc-webpanel/data
  ports:
    - '8080:8080'
  networks:
    - atl-chat
  restart: unless-stopped
```

## Volume Management

### Persistent Volumes
```yaml
volumes:
  atl-irc-webpanel-data:
    name: atl-irc-webpanel-data
    driver: local
```

### Bind Mounts
```yaml
volumes:
  - ./apps/irc/services/unrealircd/config:/home/unrealircd/unrealircd/config
  - ./logs/atl-irc-server:/home/unrealircd/unrealircd/logs
  - ./data/atl-irc-server:/home/unrealircd/unrealircd/data
```

## Networking

### Network Architecture
```yaml
networks:
  atl-chat:
    name: atl-chat
    driver: bridge
```

### Port Mapping
- **6697**: IRC over TLS (external)
- **6900**: Server-to-server TLS (external)
- **6901**: Atheme services connection (localhost)
- **8600**: JSON-RPC API (internal)
- **8000**: WebSocket IRC (external)
- **8080**: WebPanel (external)

## Security

### Non-Root Containers
All containers run as non-root users with proper UID/GID mapping:

```yaml
environment:
  - PUID=${PUID:-1000}
  - PGID=${PGID:-1000}
```

### File Permissions
```bash
# Set proper permissions
chmod 600 .env cloudflare-credentials.ini
chmod 755 data/ logs/
```

## Health Checks

### Container Health Monitoring
```yaml
healthcheck:
  test: ['CMD', 'nc', '-z', 'localhost', '6697']
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 30s
```

### Health Check Commands
```bash
# Check container health
docker ps --filter "health=healthy"

# Check service status
make status

# View container logs
docker compose logs atl-irc-server
```

## Management Commands

### Service Management
```bash
# Start all services
make up

# Stop all services
make down

# Restart services
make restart

# Check service status
make status
```

### Container Management
```bash
# Build containers
make build

# Rebuild from scratch
make rebuild

# View logs
make logs
make logs-ircd
make logs-atheme
make logs-webpanel
```

### Debugging
```bash
# Access container shell
docker compose exec atl-irc-server sh
docker compose exec atl-irc-services sh

# Check container health
docker inspect unrealircd | grep -A 10 "Health"

# Monitor resource usage
docker stats
```

## Troubleshooting

### Common Issues

#### Permission Errors
```bash
# Fix file ownership
sudo chown -R $(id -u):$(id -g) data/ logs/

# Check PUID/PGID
echo "PUID: $(id -u), PGID: $(id -g)"
```

#### Container Won't Start
```bash
# Check logs
docker compose logs atl-irc-server

# Validate configuration
docker compose config

# Check dependencies
docker compose ps
```

#### Network Issues
```bash
# Check network connectivity
docker network ls
docker network inspect atl-chat

# Test service communication
docker compose exec atl-irc-server nc -z localhost 6901
```

## Related Documentation

- [MAKE.md](MAKE.md) - Build automation and management commands
- [CONFIG.md](CONFIG.md) - Configuration management
- [TROUBLESHOOTING.md](TROUBLESHOOTING.md) - Common issues and solutions
