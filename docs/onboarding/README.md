# Onboarding Guide

Get your local atl.chat development environment set up.

## Prerequisites

- Docker and Docker Compose
- [just](https://github.com/casey/just) command runner
- [pre-commit](https://pre-commit.com/) (optional, for git hooks)

## Quick Start

```bash
# Clone and enter the repo
cd atl.chat

# One-time setup: data dirs, config, dev certs
just init

# Start the stack
just dev
```

## Git Hooks (optional)

```bash
uv run pre-commit install
uv run pre-commit install --hook-type commit-msg
uv run pre-commit install --hook-type prepare-commit-msg
```

## Next Steps

- [Architecture Overview](../architecture/README.md)
- [IRC Setup](../services/irc/README.md)
- [XMPP Setup](../services/xmpp/README.md)
