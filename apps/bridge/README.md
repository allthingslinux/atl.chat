# ATL Bridge

Custom Discord–IRC–XMPP multi-presence bridge.

Source: https://github.com/allthingslinux/bridge

## Setup

1. Copy `config.example.yaml` to `config.yaml` and fill in your channel mappings.
2. Set the required env vars in `.env` (see `.env.example` for the full list).
3. Ensure Prosody has the `bridge.atl.chat` component configured (already done in `prosody.cfg.lua`).

## Required env vars

| Variable | Description |
|---|---|
| `DISCORD_TOKEN` | Discord bot token |
| `XMPP_COMPONENT_SECRET` | Must match Prosody's `component_secret` |
| `PORTAL_BASE_URL` | Portal API URL (optional — identity linking disabled if unset) |
| `PORTAL_TOKEN` | Portal service token |

## Containerfile

The bridge source lives at `~/dev/allthingslinux/bridge`. Copy or symlink the
`Containerfile` and `src/` here, or point the compose build context at the
source repo directly.
