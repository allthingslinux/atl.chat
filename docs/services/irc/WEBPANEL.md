# UnrealIRCd WebPanel

The UnrealIRCd WebPanel provides a web-based administration interface for managing your IRC network. It connects to UnrealIRCd via JSON-RPC API and offers user management, channel administration, and server monitoring.

## Quick Start

1. **Start the WebPanel:**
   ```bash
   make up
   ```

2. **Access the interface:**
   ```
   http://localhost:8080
   ```

3. **Default credentials:**
   - Username: `admin`
   - Password: `admin` (change immediately!)

## Configuration

The WebPanel is automatically configured through Docker. Key settings:

- **Port**: `8080` (configurable via `WEBPANEL_PORT` in `.env`)
- **RPC Connection**: Automatically connects to UnrealIRCd on port `8600`
- **Authentication**: File-based (default) or SQL
- **Database**: SQLite (stored in Docker volume)

## Features

### Dashboard
- Server status and uptime
- User count and channel statistics
- Recent activity logs

### User Management
- View online users
- Manage user bans (K-line, Z-line, G-line)
- User search and details

### Channel Administration
- Channel list and details
- Channel mode management
- Topic editing

### Server Configuration
- Remote configuration editing
- Module management
- Log viewing

## Troubleshooting

### Connection Issues

**WebPanel shows "Connection failed":**

1. **Check RPC connectivity:**
   ```bash
   docker exec atl-irc-webpanel nc -z unrealircd 8600
   ```

2. **Check UnrealIRCd logs:**
   ```bash
   make logs-ircd | grep -i rpc
   ```

3. **Verify RPC configuration:**
   ```bash
   grep -A5 "listen.*rpc" src/backend/unrealircd/conf/unrealircd.conf
   ```

### Performance Issues

**Slow loading:**

1. **Restart WebPanel:**
   ```bash
   docker restart atl-irc-webpanel
   ```

2. **Clear cache:**
   ```bash
   docker exec atl-irc-webpanel rm -rf /tmp/*
   ```

## Backup

**Backup WebPanel data:**
```bash
docker run --rm -v atl-irc-webpanel-data:/data \
    alpine tar czf - -C /data . > webpanel-backup-$(date +%Y%m%d).tar.gz
```

**Restore WebPanel data:**
```bash
docker run --rm -v atl-irc-webpanel-data:/data \
    -v $(pwd):/backup alpine \
    tar xzf /backup/webpanel-backup-latest.tar.gz -C /data
```

## Related Documentation

- [UNREALIRCD.md](UNREALIRCD.md) - IRC server configuration
- [CONFIG.md](CONFIG.md) - Configuration management
- [API.md](API.md) - JSON-RPC API documentation
- [TROUBLESHOOTING.md](TROUBLESHOOTING.md) - Common issues and solutions