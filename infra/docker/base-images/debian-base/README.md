# Debian Base Image

Base Debian Linux image with common dependencies for XMPP services.

## Usage

```dockerfile
FROM ghcr.io/allthingslinux/debian-base:latest
# or build locally
FROM atl/debian-base:latest
```

## Includes

- Debian Bookworm Slim
- curl, wget
- ca-certificates
- gnupg
- dumb-init (init system)
- gosu (user switching)

## Used By

- Prosody XMPP Server
