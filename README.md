# atl.chat Monorepo

This repository contains the full `atl.chat` ecosystem, managed as a monorepo.

## Workspace Structure

- **`apps/web`**: The main `atl.chat` Next.js application.
- **`apps/xmpp`**: XMPP server configuration (Prosody) and modules.
- **`apps/irc`**: IRC server configuration (UnrealIRCd) and web panel.

## Getting Started

### Prerequisites
- Node.js & npm
- Docker & Docker Compose (for XMPP/IRC apps)

### Development

To start all applications in parallel (if supported):
```bash
npx turbo dev
```

To work on a specific application:
```bash
# Web App
npm run dev -w apps/web

# XMPP (via Docker)
npm run dev -w apps/xmpp

# IRC (via Docker)
npm run dev -w apps/irc
```

## Build

To build all apps:
```bash
npx turbo build
```
