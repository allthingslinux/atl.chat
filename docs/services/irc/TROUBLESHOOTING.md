# Troubleshooting Guide

This guide covers common issues and solutions for IRC.atl.chat deployment and operation.

## Quick Diagnosis

### System Health Check

```bash
# Check service status
make status

# View service logs
make logs

# Quick environment check
make test-quick
```

## Common Issues

### Docker Not Available

**Symptoms:** `docker: command not found`

**Solutions:**

```bash
# Install Docker (Ubuntu/Debian)
sudo apt update && sudo apt install docker.io docker-compose-plugin

# Start Docker service
sudo systemctl start docker
sudo systemctl enable docker

# Add user to docker group
sudo usermod -aG docker $USER
# Logout and login again

# Verify installation
docker --version
docker compose version
```

### Permission Denied

**Symptoms:** `Permission denied` when accessing files

**Solutions:**

```bash
# Fix .env file permissions
chmod 600 .env

# Fix data directory permissions
sudo chown -R $(id -u):$(id -g) data/ logs/

# Check PUID/PGID match host user
echo "Host user: $(id -u):$(id -g)"
echo "PUID: $PUID, PGID: $PGID"
```

### Services Won't Start

**Symptoms:** Containers fail to start or exit immediately

**Solutions:**

```bash
# Check service status
make status

# View specific logs
make logs-ircd
make logs-atheme

# Check configuration
make test-env

# Restart services
make restart
```

### SSL Certificate Issues

**Symptoms:** SSL setup fails or certificates expire

**Solutions:**

```bash
# Check SSL status
make ssl-status

# View SSL logs
make ssl-logs

# Force SSL renewal
make ssl-renew

# Check Cloudflare credentials
cat cloudflare-credentials.ini
```

### Configuration Issues

**Symptoms:** Services start but don't work properly

**Solutions:**

```bash
# Validate configuration
make test-env

# Check generated configs
ls -la apps/unrealircd/config/*.conf apps/atheme/config/*.conf

# Regenerate configurations
make build

# Restart services
make restart
```

### Network Issues

**Symptoms:** Can't connect to IRC server

**Solutions:**

```bash
# Check if ports are open
netstat -tlnp | grep -E "(6697|8080|8600)"

# Test IRC connection
telnet localhost 6697

# Check firewall
sudo ufw status

# Allow IRC ports
sudo ufw allow 6697/tcp
sudo ufw allow 8080/tcp
```

## Service-Specific Issues

### UnrealIRCd Issues

```bash
# Check UnrealIRCd logs
make logs-ircd

# Test IRC functionality
make test-irc

# Check configuration syntax
docker compose exec atl-irc-server unrealircd -c /home/unrealircd/unrealircd/config/unrealircd.conf
```

### Atheme Issues

```bash
# Check Atheme logs
make logs-atheme

# Test service connection
docker compose exec atl-irc-services pgrep atheme-services

# Check database
ls -la data/atheme/data/
```

### WebPanel Issues

```bash
# Check WebPanel logs
make logs-webpanel

# Test WebPanel access
curl -I http://localhost:8080

# Check RPC connection
docker compose exec atl-irc-server nc -z localhost 8600
```

## Debug Mode

### Enable Verbose Logging

```bash
# Add debug flags
DEBUG=1 make up

# Verbose SSL operations
VERBOSE=1 make ssl-setup
```

### Manual Service Access

```bash
# Access UnrealIRCd container
docker compose exec atl-irc-server sh

# Access Atheme container
docker compose exec atl-irc-services sh

# Check container health
docker ps --filter "health=unhealthy"
```

## Recovery Procedures

### Complete Reset

```bash
# WARNING: Destroys all data
make reset

# Followed by fresh setup
make up
```

### Service Recovery

```bash
# Restart failed services
make restart

# Rebuild if needed
make rebuild

# Check logs for errors
make logs
```

## Getting Help

### Log Analysis

```bash
# All service logs
make logs

# Specific service logs
make logs-ircd
make logs-atheme
make logs-webpanel

# Follow logs in real-time
docker compose logs -f
```

### System Information

```bash
# Show system info
make info

# Check Docker status
docker system df
docker system prune
```

## Related Documentation

- [CONFIG.md](CONFIG.md) - Configuration management
- [SSL.md](SSL.md) - SSL certificate management
- [DOCKER.md](DOCKER.md) - Container setup
