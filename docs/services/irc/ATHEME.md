# Atheme IRC Services

This guide covers the configuration and management of Atheme IRC Services, which provide essential IRC functionality like NickServ, ChanServ, OperServ, and other services for IRC.atl.chat.

## Overview

### Architecture

- **Version**: Atheme 7.2.12 (latest stable)
- **Purpose**: IRC services daemon providing user and channel management
- **Integration**: Connects to UnrealIRCd via server protocol
- **Database**: SQLite backend for data persistence
- **Authentication**: PBKDF2 password hashing with SASL support

### Core Services

```
Atheme Services:
├── NickServ    - Nickname registration and management
├── ChanServ    - Channel registration and access control
├── OperServ    - Administrative services
├── MemoServ    - Private messaging system
├── HelpServ    - User assistance
├── InfoServ    - Network information
├── BotServ     - Channel bot management
├── GroupServ   - Account grouping
├── HostServ    - Virtual host management
├── SASLServ    - SASL authentication
└── Other services (GameServ, etc.)
```

## Installation and Setup

### Container Configuration

Atheme runs in a dedicated Docker container:

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
    - ./data/atheme/data:/usr/local/atheme/data
    - ./data/atheme/logs:/usr/local/atheme/logs
  network_mode: service:atl-irc-server  # Shares network with IRCd
```

### Service Dependencies

- **UnrealIRCd**: Must be running and healthy before Atheme starts
- **Network**: Shares network namespace with IRCd for localhost communication
- **Configuration**: Read-only configuration mount
- **Data**: Persistent SQLite database and logs

## Configuration

### Main Configuration File

The primary configuration is generated from `atheme.conf.template`:

#### Server Connection (Uplink)
```c
serverinfo {
    name = "${ATHEME_SERVER_NAME}";           // services.atl.chat
    desc = "${ATHEME_SERVER_DESC}";           // Service description
    uplink = "127.0.0.1";                    // Local IRCd connection
    recontime = ${ATHEME_RECONTIME};         // Reconnect time (10s)
    netname = "${ATHEME_NETNAME}";           // Network name
    numeric = "${ATHEME_NUMERIC}";           // Server numeric (00A)
}
```

#### Authentication
```c
uplink {
    send_password = "${ATHEME_SEND_PASSWORD}";
    receive_password = "${ATHEME_RECEIVE_PASSWORD}";
    port = ${ATHEME_UPLINK_PORT};            // 6901
}
```

### Module Loading

#### Core Modules
```c
loadmodule "protocol/unreal4";       // UnrealIRCd protocol support
loadmodule "backend/opensex";        // SQLite database backend
loadmodule "crypto/pbkdf2v2";        // Password hashing
```

#### Service Modules
```c
// Nickname services
loadmodule "nickserv/main";
loadmodule "nickserv/identify";
loadmodule "nickserv/register";
loadmodule "nickserv/info";

// Channel services
loadmodule "chanserv/main";
loadmodule "chanserv/register";
loadmodule "chanserv/access";

// Administrative services
loadmodule "operserv/main";
loadmodule "operserv/akill";
loadmodule "operserv/clones";

// Additional services
loadmodule "memoserv/main";
loadmodule "helpserv/main";
loadmodule "infoserv/main";
```

### Database Configuration

```c
database {
    type = "opensex";
    name = "/usr/local/atheme/data/services.db";
}
```

### SASL Configuration

```c
loadmodule "saslserv/main";
loadmodule "saslserv/scram-sha";

saslserv {
    hidden = yes;
}
```

## Service Management

### Starting Services

Atheme services start automatically when the container starts:

```bash
# Check service status
docker logs atheme

# Verify services are running
docker exec atheme pgrep -f atheme-services
```

### Service Commands

#### NickServ - Nickname Management

**Registration:**
```irc
/msg NickServ REGISTER password email@example.com
/msg NickServ IDENTIFY nickname password
```

**Account Management:**
```irc
/msg NickServ SET PASSWORD newpassword
/msg NickServ SET EMAIL newemail@example.com
/msg NickServ INFO nickname
```

**Security Features:**
```irc
/msg NickServ SET HIDEMAIL ON
/msg NickServ SET PRIVATE ON
/msg NickServ GHOST nickname
```

#### ChanServ - Channel Management

**Channel Registration:**
```irc
/msg ChanServ REGISTER #channel
/msg ChanServ SET #channel FOUNDER
```

**Access Control:**
```irc
/msg ChanServ ACCESS #channel ADD nickname AOP
/msg ChanServ ACCESS #channel DEL nickname
/msg ChanServ ACCESS #channel LIST
```

**Channel Settings:**
```irc
/msg ChanServ SET #channel GUARD ON
/msg ChanServ SET #channel MLOCK +nt
/msg ChanServ TOPIC #channel New topic
```

#### OperServ - Administrative Services

**Network Management:**
```irc
/msg OperServ AKILL ADD mask reason
/msg OperServ AKILL DEL mask
/msg OperServ AKILL LIST
```

**Service Control:**
```irc
/msg OperServ RESTART
/msg OperServ SHUTDOWN
/msg OperServ JUPE server reason
```

**User Management:**
```irc
/msg OperServ MODE nickname +o
/msg OperServ KILL nickname reason
```

#### MemoServ - Private Messaging

**Sending Memos:**
```irc
/msg MemoServ SEND nickname message
/msg MemoServ SEND #channel message
```

**Managing Memos:**
```irc
/msg MemoServ LIST
/msg MemoServ READ number
/msg MemoServ DEL number
```

### SASL Authentication

SASL enables automatic authentication:

```irc
CAP REQ :sasl
AUTHENTICATE PLAIN
<base64 encoded auth>
CAP END
```

## Database Management

### SQLite Database

Atheme stores all data in a SQLite database:

```bash
# Database location
ls -la data/atheme/data/services.db

# Backup database
cp data/atheme/data/services.db backup/

# Database size
du -h data/atheme/data/services.db
```

### Data Persistence

```bash
# Persistent volumes
data/atheme/data/    # Database (services.db)
data/atheme/logs/   # Service logs
```

### Database Maintenance

```bash
# Check database integrity
sqlite3 data/atheme/data/services.db "PRAGMA integrity_check;"

# Optimize database
sqlite3 data/atheme/data/services.db "VACUUM;"

# View registered nicknames
sqlite3 data/atheme/data/services.db "SELECT * FROM nick_table LIMIT 10;"
```

## Security Features

### Password Hashing

Atheme uses PBKDF2 v2 for secure password hashing:

```c
crypto {
    pbkdf2v2_digest = "SHA-512";
    pbkdf2v2_rounds = 32768;
}
```

### Access Controls

#### Operator Permissions
```c
operclass "sra" {
    privileges = "admin:*";
}

oper "admin" {
    operclass = "sra";
}
```

#### Service Restrictions
```c
nickserv {
    register_enabled = yes;
    maxnicks = 5;
    spam = yes;
}
```

### Flood Protection

```c
floodserv {
    enabled = yes;
    threshold = 5;
    action = "AKILL";
}
```

## Monitoring and Logging

### Log Configuration

```c
log {
    file = "/usr/local/atheme/logs/atheme.log";
    level = "info";
    source = "*";
}
```

### Log Analysis

```bash
# View recent logs
tail -f data/atheme/logs/atheme.log

# Search for specific events
grep "REGISTER" data/atheme/logs/atheme.log

# Monitor failed authentications
grep "BADPASSWORD" data/atheme/logs/atheme.log
```

### Service Health Checks

```bash
# Container health
docker ps atheme

# Service process
docker exec atheme ps aux | grep atheme

# Network connectivity
docker exec atheme nc -z localhost 6901
```

## User Experience

### Registration Process

1. **Connect to IRC**
   ```irc
   /server irc.atl.chat +6697
   ```

2. **Register Nickname**
   ```irc
   /msg NickServ REGISTER mypassword user@example.com
   ```

3. **Verify Email** (if required)
   - Check email for verification code
   ```irc
   /msg NickServ VERIFY code
   ```

4. **Identify**
   ```irc
   /msg NickServ IDENTIFY mypassword
   ```

### Channel Management

1. **Register Channel**
   ```irc
   /join #mychannel
   /msg ChanServ REGISTER #mychannel
   ```

2. **Set Channel Modes**
   ```irc
   /msg ChanServ SET #mychannel MLOCK +nt
   /msg ChanServ SET #mychannel GUARD ON
   ```

3. **Manage Access**
   ```irc
   /msg ChanServ ACCESS #mychannel ADD friend AOP
   ```

## Troubleshooting

### Common Issues

#### Services Not Starting
```bash
# Check container logs
docker logs atheme

# Verify IRCd connectivity
docker exec atheme nc -z localhost 6901

# Check configuration syntax
docker exec atheme atheme-services -c /usr/local/atheme/etc/atheme.conf
```

#### Authentication Problems
```bash
# Check password hash
grep "BADPASSWORD" data/atheme/logs/atheme.log

# Verify user registration
sqlite3 data/atheme/data/services.db "SELECT * FROM nick_table WHERE nick='nickname';"
```

#### Database Issues
```bash
# Check database file
ls -la data/atheme/data/services.db

# Repair database
sqlite3 data/atheme/data/services.db ".recover" > recovery.sql

# Restore from backup
cp backup/services.db data/atheme/data/services.db
```

#### Memory Issues
```bash
# Monitor memory usage
docker stats atheme

# Check for memory leaks
docker exec atheme ps aux | grep atheme
```

### Debug Mode

Enable detailed logging:

```c
log {
    file = "/usr/local/atheme/logs/debug.log";
    level = "debug";
    source = "*";
}
```

### Service Recovery

If services become unresponsive:

```bash
# Restart container
docker restart atheme

# Force service restart
docker exec atheme pkill atheme-services
docker exec atheme atheme-services -n
```

## Advanced Configuration

### Custom Services

Add custom service modules:

```c
loadmodule "myservice/main";

service "myservice" {
    nick = "MyServ";
    user = "myserv";
    host = "services.atl.chat";
    real = "My Custom Service";
}
```

### Integration Features

#### IRCv3 Support
```c
loadmodule "extensions/ircv3";

ircv3 {
    enabled = yes;
}
```

#### Web Interface
```c
loadmodule "httpd/main";

httpd {
    host = "127.0.0.1";
    port = 8081;
}
```

### Backup and Recovery

#### Automated Backups
```bash
# Database backup script
#!/bin/bash
sqlite3 data/atheme/data/services.db ".backup backup/atheme-$(date +%Y%m%d).db"

# Configuration backup
cp apps/atheme/config/atheme.conf backup/
```

#### Recovery Process
```bash
# Stop services
docker stop atheme

# Restore database
cp backup/atheme-latest.db data/atheme/data/services.db

# Restore configuration
cp backup/atheme.conf apps/atheme/config/

# Restart services
make up
```

## Performance Tuning

### Connection Limits

```c
serverinfo {
    maxclients = 1000;
    maxchans = 100;
}
```

### Cache Settings

```c
cache {
    expiry = 3600;     // 1 hour cache
    size = 1048576;    // 1MB cache
}
```

### Database Optimization

```c
database {
    optimize = yes;
    wal_mode = yes;    // Write-ahead logging
}
```

## Maintenance

### Regular Tasks

```bash
# Check service health
make status

# Monitor logs
make logs-atheme

# Backup database
./scripts/backup-atheme.sh

# Update services
make restart
```

### Version Upgrades

```bash
# Backup current setup
./scripts/backup-atheme.sh

# Update container
make build

# Test new version
make up

# Rollback if needed
docker tag atheme:latest atheme:backup
```

## Related Documentation

- [UNREALIRCD.md](UNREALIRCD.md) - IRC server configuration
- [USERMODES.md](USERMODES.md) - IRC user mode reference
- [CONFIG.md](CONFIG.md) - Configuration management
- [Atheme Documentation](https://atheme.dev/) - Official Atheme docs
- [IRC Services](https://wiki.ircnet.net/index.php/IRC_Services) - Services overview