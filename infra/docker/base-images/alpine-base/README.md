# Alpine Base Image

Base Alpine Linux image with common dependencies for IRC services.

## Usage

```dockerfile
FROM ghcr.io/allthingslinux/alpine-base:latest
# or build locally
FROM atl/alpine-base:latest
```

## Includes

- Alpine 3.23
- curl, wget
- ca-certificates
- openssl
- bash
- tini (init system)
- su-exec (user switching)

## Used By

- UnrealIRCd
- Atheme
