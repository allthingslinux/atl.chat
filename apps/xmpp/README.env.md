# XMPP Environment Variables

## Quick Start

The XMPP service uses the **root `.env.example`** as the source of truth for all environment variables.

```bash
# From the repository root
cp .env.example .env

# Edit with your values
nano .env
```

## Key Variables for XMPP

All XMPP-related variables are already documented in the root `.env.example` file (lines 182-286).

### Required for Production

```bash
# Database (from root .env.example)
POSTGRES_USER=prosody
POSTGRES_PASSWORD=your-secure-password
POSTGRES_DB=prosody

# TURN Server (add to root .env if missing)
TURN_SECRET=your-turn-secret
TURN_REALM=xmpp.atl.chat
TURN_DOMAIN=xmpp.atl.chat

# SSL Certificates
LETSENCRYPT_EMAIL=admin@atl.chat
```

### Development Mode

For development with `--profile dev`, Adminer auto-login is enabled by default:

```bash
# Optional: Override Adminer defaults
ADMINER_AUTO_LOGIN=true              # Auto-login in dev (default: true)
ADMINER_DEFAULT_SERVER=atl-xmpp-db   # Database host (default)
ADMINER_DEFAULT_DB=prosody           # Database name (default)
ADMINER_DEFAULT_USERNAME=prosody     # Database user (default)
ADMINER_DEFAULT_PASSWORD=<from POSTGRES_PASSWORD>
```

## Usage

```bash
# Production (uses root .env)
docker compose up -d

# Development with dev tools (uses root .env)
docker compose --profile dev up -d

# Certificate issuance (uses root .env)
docker compose --profile cert-issue up atl-xmpp-certbot
```

## Notes

- ✅ **Single source of truth**: Root `.env.example` contains all XMPP variables
- ✅ **No XMPP-specific .env needed**: The compose.yaml reads from root `.env`
- ✅ **Smart defaults**: Most variables have sensible defaults for development
- ✅ **Environment-aware**: Same `.env` works for both prod and dev profiles
