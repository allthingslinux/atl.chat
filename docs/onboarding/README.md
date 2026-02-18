# Onboarding Guide

Get your local atl.chat development environment set up.

## Prerequisites

- Docker and Docker Compose
- [just](https://github.com/casey/just) command runner
- [lefthook](https://github.com/evilmartians/lefthook) (optional, for git hooks)

## Quick Start

```bash
# Clone and enter the repo
cd atl.chat

# One-time setup: data dirs, config, dev certs
just init

# Start the stack
just dev
```

## Next Steps

- [Architecture Overview](../architecture/README.md)
- [IRC Setup](../services/irc/README.md)
- [XMPP Setup](../services/xmpp/README.md)
