# UnrealIRCd Server Configuration

This guide covers the configuration and management of the UnrealIRCd IRC server, the core component of IRC.atl.chat. UnrealIRCd is a high-performance, feature-rich IRC daemon that powers the IRC network.

## Overview

### Architecture

- **Version**: UnrealIRCd 6.2.0.1 (latest stable)
- **Security**: TLS-only connections enforced
- **Features**: IRCv3 support, cloaking, services integration
- **Performance**: Multi-threaded, event-driven design
- **Configuration**: Template-based with environment variable substitution

### Core Components

```
unrealircd/
├── config/                    # Configuration files
│   ├── unrealircd.conf     # Main server configuration
│   ├── modules.*.conf      # Module loading
│   ├── operclass.*.conf    # Operator permissions
│   └── tls/               # SSL certificates
├── logs/                   # Server logs
├── data/                   # Persistent data (channel.db, etc.)
└── scripts/               # Management utilities
```

## Server Configuration

### Main Configuration File

The primary configuration is generated from `unrealircd.conf.template` using environment variables:

#### Server Identity
```c
me {
    name "${IRC_DOMAIN}";           // Server name (irc.atl.chat)
    info "${IRC_NETWORK_NAME} IRC Server";  // Server description
    sid "001";                      // Server ID (unique per server)
}
```

#### Administrator Information
```c
admin {
    "${IRC_ADMIN_NAME}";           // Admin name
    "admin";                       // Department
    "${IRC_ADMIN_EMAIL}";          // Contact email
}
```

### Connection Classes

#### Client Connections
```c
class clients {
    pingfreq 90;                   // Ping frequency in seconds
    maxclients 1000;              // Maximum concurrent clients
    sendq 200k;                   // Send queue size
    recvq 8000;                   // Receive queue buffer
}
```

#### Operator Connections
```c
class opers {
    pingfreq 90;
    maxclients 50;                // Fewer operator slots
    sendq 1M;                     // Larger send queue for ops
    recvq 8000;
}
```

#### Server Links
```c
class servers {
    pingfreq 90;
    maxclients 10;                // Limited server connections
    sendq 5M;                     // Large send queue for server data
    recvq 8000;
}
```

### Network Security

#### TLS Configuration
```c
listen {
    ip *;
    port ${IRC_TLS_PORT};         // 6697 (TLS only)
    options {
        tls;
        clientsonly;
    };
    tls-options {
        certificate "/home/unrealircd/unrealircd/certs/live/irc.atl.chat/fullchain.pem";
        key "/home/unrealircd/unrealircd/certs/live/irc.atl.chat/privkey.pem";
    };
}
```

#### Cloaking (Host Privacy)
```c
cloak {
    enabled yes;
    cloak-keys {
        "aoAr1HnR6gl3sI7hJHpOeMZ7ciaqek+vZv8EGM+HA";
        "aoAr1HnR6gl3sI7hJHpOeMZ7ciaqek+vZv8EGM+HB";
        "aoAr1HnR6gl3sI7hJHpOeMZ7ciaqek+vZv8EGM+HC";
    };
    cloak-prefix "atl";           // Network-specific prefix
}
```

### IRC Operator Configuration

#### Operator Account Setup
```c
oper yournick {
    password "$argon2id$...";      // Argon2id hashed password
    class "netadmin";             // Permission class
    modes "+xwgs";               // Default operator modes
    vhost "staff.atl.chat";      // Virtual host
    mask "127.0.0.1";           // Connection mask
}
```

#### Operator Classes
```c
class netadmin {
    maxcon 10;                   // Connection limit
    permissions {
        admin;                   // Administrative permissions
        oper;                    // Operator permissions
        stats;                   // Statistics access
    };
}
```

### Services Integration

#### Atheme Services Link
```c
listen {
    ip 127.0.0.1;               // Localhost only
    port ${ATHEME_UPLINK_PORT}; // 6901
    options {
        serversonly;            // Services only
    };
}
```

#### Services Authentication
```c
link services.atl.chat {
    incoming {
        mask *;
    };
    password "${ATHEME_RECEIVE_PASSWORD}";
    class servers;
}
```

## Module System

### Core Modules

UnrealIRCd uses a modular architecture. Core modules are loaded in `modules.default.conf`:

#### Authentication & Security
```
loadmodule "cloak_sha256";      // Hostname cloaking
loadmodule "usermodes/secureonlymsg";  // SSL-only messaging
loadmodule "usermodes/regonlymsg";     // Registered users only
```

#### User Modes
```
loadmodule "usermodes/bot";         // Bot identification
loadmodule "usermodes/censor";      // Content filtering
loadmodule "usermodes/privdeaf";    // Private message blocking
loadmodule "usermodes/noctcp";      // CTCP blocking
```

#### Channel Modes
```
loadmodule "chanmodes/admin";       // Admin channel mode
loadmodule "chanmodes/auditorium";  // Auditorium mode
loadmodule "chanmodes/ban";         // Ban management
loadmodule "chanmodes/inviteonly";  // Invite-only channels
```

### Custom Modules

Additional modules can be loaded in `modules.custom.conf`:

```c
// Third-party modules
loadmodule "third/showwebirc";   // WebIRC support

// Custom modules
// loadmodule "my_custom_module";
```

### Third-Party Modules

IRC.atl.chat includes support for third-party modules:

```bash
# List available third-party modules
ls apps/unrealircd/third-party-modules.list

# Install modules
./apps/unrealircd/scripts/install-modules.sh
```

## Security Features

### TLS-Only Enforcement

```c
set {
    modes-on-connect "+ixw";      // i=invisible, x=cloak, w=wallops
    // No plaintext port configured
}
```

### Flood Protection

```c
set {
    anti-flood {
        unknown-users {
            connect-flood 3:60;   // 3 connections per minute
            nick-flood 4:30;     // 4 nick changes per 30 seconds
        };
        known-users {
            // Less restrictive for registered users
        };
    };
}
```

### Spam Filtering

```c
spamfilter {
    // Block common spam patterns
    regex "*fuck*";
    action block;
    reason "Language filter";
}
```

### Rate Limiting

```c
set {
    max-unknown-connections-per-ip 3;
    restrict-usermode "+r";       // Registered users only
}
```

## Performance Tuning

### Connection Limits

```c
set {
    maxclients 1000;            // Global connection limit
    ping-warning 15;            // Seconds before ping warning
    ping-deadline 30;          // Seconds before disconnect
}
```

### Queue Management

```c
class clients {
    sendq 200k;                // Send queue per client
    recvq 8k;                  // Receive buffer per client
}
```

### DNS Configuration

```c
set {
    dns {
        timeout 3;             // DNS timeout in seconds
        retries 2;            // DNS retry attempts
    };
}
```

## Monitoring and Logging

### Log Configuration

```c
log "ircd.log" {
    source {
        all;
    };
    level info;               // Logging level
}
```

### JSON-RPC API

```c
listen {
    ip 127.0.0.1;            // Local API access
    port ${IRC_RPC_PORT};    // 8600
    options {
        rpc;                 // Enable RPC
    };
}
```

### Server Statistics

```c
set {
    stats-server "stats.atl.chat";
    hide-stats "opers";      // Hide operator stats
}
```

## WebSocket Support

### WebIRC Configuration

```c
listen {
    ip *;
    port ${IRC_WEBSOCKET_PORT};  // 8000
    options {
        websocket;           // Enable WebSocket
    };
    websocket-options {
        type text;          // IRC message format
    };
}
```

## IRCv3 Protocol Support

### Modern Features

UnrealIRCd 6 supports IRCv3 capabilities:

```c
set {
    ircv3-capabilities {
        echo-message;        // Message echo
        sasl;               // SASL authentication
        tls;                // TLS capability
        userhost-in-names;  // Userhost in NAMES
    };
}
```

### SASL Integration

```c
sasl {
    target localhost:${ATHEME_UPLINK_PORT};
    password "${ATHEME_SEND_PASSWORD}";
}
```

## Troubleshooting

### Common Issues

#### Connection Problems
```bash
# Check server status
docker logs atl-irc-server

# Verify TLS certificates
openssl s_client -connect localhost:6697 -servername ${IRC_DOMAIN}

# Check network connectivity
telnet localhost 6697
```

#### Module Loading Errors
```bash
# Check module dependencies
ldd /home/unrealircd/unrealircd/modules/*.so

# Verify configuration syntax
unrealircd -c /path/to/config
```

#### Performance Issues
```bash
# Monitor resource usage
docker stats atl-irc-server

# Check connection counts
unrealircd stats
```

### Debug Mode

Enable detailed logging for troubleshooting:

```bash
# In unrealircd.conf
log "debug.log" {
    source {
        all;
    };
    level debug;
}
```

## Configuration Management

### Template Processing

Configuration is generated from templates:

```bash
# Manual regeneration
./scripts/prepare-config.sh

# Check generated config
cat apps/unrealircd/config/unrealircd.conf
```

### Backup and Recovery

```bash
# Backup configuration
cp apps/unrealircd/config/unrealircd.conf backup/

# Restore from backup
cp backup/unrealircd.conf apps/unrealircd/config/
```

## Advanced Features

### Server Linking

```c
link hub.irc.atl.chat {
    outgoing {
        hostname "hub.irc.atl.chat";
        port 6900;
        options { tls; };
    };
    password "shared-link-password";
    class servers;
}
```

### Channel Persistence

```c
set {
    channeldb {
        file "channel.db";     // Persistent channel storage
    };
}
```

### Custom Commands

```c
command "CUSTOMCMD" {
    class "opers";           // Operator only
    require_oper yes;
}
```

## Maintenance

### Regular Tasks

```bash
# Check server health
make status

# Monitor logs
make logs-ircd

# Update certificates
make ssl-status

# Restart services
make restart
```

### Performance Monitoring

```bash
# Server statistics
unrealircd stats

# Connection information
unrealircd clients

# Module status
unrealircd modules
```

## Related Documentation

- [SSL.md](SSL.md) - SSL certificate management
- [ATHEME.md](ATHEME.md) - IRC services configuration
- [MODULES.md](MODULES.md) - Module management
- [DOCKER.md](DOCKER.md) - Container setup
- [CONFIG.md](CONFIG.md) - Configuration system
- [UnrealIRCd Documentation](https://www.unrealircd.org/docs/) - Official docs