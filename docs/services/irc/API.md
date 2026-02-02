# API Reference

This guide covers the programmatic interfaces available for IRC.atl.chat, focusing on the actual JSON-RPC API provided by UnrealIRCd.

## Overview

### Available APIs

IRC.atl.chat provides:

1. **JSON-RPC API** - UnrealIRCd's built-in administration API (port 8600)
2. **WebSocket IRC** - Standard IRC protocol over WebSocket (port 8000)

### API Endpoints

```
JSON-RPC API:    atl-irc-server:8600    (internal)
WebSocket IRC:   atl-irc-server:8000    (external)
```

## JSON-RPC API

### Connection Setup

The JSON-RPC API is built into UnrealIRCd and provides server administration capabilities.

#### Basic Connection
```bash
# Test RPC connectivity
curl -X POST http://localhost:8600/api \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "server.info",
    "params": {},
    "id": 1
  }'
```

#### Authentication
The RPC API uses basic authentication configured in UnrealIRCd:

```c
// In unrealircd.conf
rpc-user adminpanel {
    match { ip 127.*; }
    rpc-class full;
    password "your_rpc_password";
}
```

### Available Methods

UnrealIRCd's JSON-RPC API provides these core methods:

#### Server Information
- `server.info` - Get server information
- `server.stats` - Get server statistics
- `server.command` - Execute server commands

#### User Management
- `user.list` - List online users
- `user.get` - Get user details
- `user.action` - Perform user actions (kill, ban, etc.)

#### Channel Management
- `channel.list` - List channels
- `channel.get` - Get channel details
- `channel.action` - Perform channel actions

#### Ban Management
- `ban.list` - List active bans
- `ban.add` - Add new ban
- `ban.remove` - Remove ban

### Example Usage

#### Get Server Information
```bash
curl -X POST http://localhost:8600/api \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "server.info",
    "params": {},
    "id": 1
  }'
```

#### List Online Users
```bash
curl -X POST http://localhost:8600/api \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "user.list",
    "params": {"limit": 50},
    "id": 2
  }'
```

#### Execute Server Command
```bash
curl -X POST http://localhost:8600/api \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "server.command",
    "params": {
      "command": "REHASH"
    },
    "id": 3
  }'
```

## WebSocket IRC

### Connection Setup

WebSocket IRC provides standard IRC protocol over WebSocket connections.

#### JavaScript Connection
```javascript
const ws = new WebSocket('ws://localhost:8000');

ws.onopen = function() {
    // Send IRC registration
    ws.send('NICK mynick\r\n');
    ws.send('USER mynick 0 * :Real Name\r\n');
};

ws.onmessage = function(event) {
    console.log('Received:', event.data);
    // Handle IRC messages
};
```

#### Python Connection
```python
import websocket

def on_message(ws, message):
    print(f"Received: {message}")

def on_open(ws):
    ws.send('NICK mynick\r\n')
    ws.send('USER mynick 0 * :Real Name\r\n')

ws = websocket.WebSocketApp('ws://localhost:8000',
                          on_message=on_message,
                          on_open=on_open)
ws.run_forever()
```

### IRC Protocol

WebSocket connections use standard IRC protocol:

#### Registration
```
NICK mynick
USER mynick 0 * :Real Name
```

#### Channel Operations
```
JOIN #channel
PRIVMSG #channel :Hello world!
PART #channel
```

#### Ping/Pong
```
PING :server
PONG :server
```

## Configuration

### RPC Configuration

Configure the JSON-RPC API in `unrealircd.conf`:

```c
// Enable RPC modules
include "rpc.modules.default.conf";

// Listen on RPC port
listen {
    ip *;
    port 8600;
    options { rpc; }
}

// RPC user configuration
rpc-user adminpanel {
    match { ip 127.*; }
    rpc-class full;
    password "secure_password";
}
```

### WebSocket Configuration

WebSocket IRC is enabled by default in UnrealIRCd 6.x:

```c
// WebSocket listener
listen {
    ip *;
    port 8000;
    options { websocket; }
}
```

## Troubleshooting

### RPC Connection Issues

**Cannot connect to RPC API:**

1. **Check if RPC is enabled:**
   ```bash
   grep -A5 "listen.*rpc" src/backend/unrealircd/conf/unrealircd.conf
   ```

2. **Verify RPC user configuration:**
   ```bash
   grep -A5 "rpc-user" src/backend/unrealircd/conf/unrealircd.conf
   ```

3. **Test connectivity:**
   ```bash
   curl -v http://localhost:8600/api
   ```

### WebSocket Issues

**WebSocket connection fails:**

1. **Check WebSocket listener:**
   ```bash
   grep -A5 "websocket" src/backend/unrealircd/conf/unrealircd.conf
   ```

2. **Test WebSocket connection:**
   ```bash
   curl -i -N -H "Connection: Upgrade" \
        -H "Upgrade: websocket" \
        -H "Sec-WebSocket-Version: 13" \
        -H "Sec-WebSocket-Key: x3JJHMbDL1EzLkh9GBhXDw==" \
        http://localhost:8000/
   ```

## Security Considerations

### RPC Security

- **Authentication**: Always use strong RPC passwords
- **Access Control**: Limit RPC access to trusted IPs
- **HTTPS**: Use HTTPS for RPC connections in production

### WebSocket Security

- **TLS**: Use WSS (WebSocket Secure) in production
- **Origin Validation**: Validate WebSocket origins
- **Rate Limiting**: Implement connection rate limiting

## Related Documentation

- [UNREALIRCD.md](UNREALIRCD.md) - IRC server configuration
- [WEBPANEL.md](WEBPANEL.md) - Web administration interface
- [CONFIG.md](CONFIG.md) - Configuration management
- [TROUBLESHOOTING.md](TROUBLESHOOTING.md) - Common issues and solutions