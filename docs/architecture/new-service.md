# New Service Integration Guide

Adding a new service to the atl.chat monorepo.

## 1. App Structure

```
apps/my-service/
├── services/          # Container builds
│   └── mysvc/
│       ├── Containerfile
│       └── config/
├── scripts/           # Init, health checks
└── tests/
```

## 2. Compose Fragment

Add `infra/compose/my-service.yaml`:

```yaml
name: atl-my-service
include:
  - networks.yaml
services:
  atl-my-service:
    build:
      context: ../../apps/my-service/services/mysvc
      dockerfile: Containerfile
    networks:
      - atl-chat
```

## 3. Root Compose

Add to `compose.yaml`:

```yaml
include:
  - infra/compose/my-service.yaml
```

## 4. Init

Update `scripts/init.sh` (or create `apps/my-service/scripts/init.sh`) for data dirs and config.
