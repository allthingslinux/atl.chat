# XMPP MUC nick / bridge — reference review findings

This file records outcomes from reviewing in-repo `references/`, `misc/bridge/references/`, `.cursor/plans/`, and `.kiro/specs/` (investigation notes; not the Cursor plan in `~/.cursor/plans/`).

## Implementation (this repo)

- **`xmpp_jid_or_plain_to_muc_nick`** — Portal bare JID → local part → `sanitize_nick` (max 23 per Prosody).
- **`puppet_muc_nick_from_base`** — optional `BRIDGE_XMPP_PUPPET_NICK_SUFFIX` for occupant collision with a human in the same room.
- **`XMPPAdapter`** — applies both for identity and dev fallback.
- **Tests** — `xep_0045` mock (`join_muc_wait`) defaults in `_make_plugin_registry` for outbound/retraction unit tests.

See [`AGENTS.md`](../AGENTS.md) section “XMPP MUC puppet nick”.

## `references/` (monorepo `atl.chat/references`)

Vendor/spec mirrors: Prosody (`muc_max_nick_length`), slixmpp, UnrealIRCd, xeps, fluux-messenger, clients. Use for **server limits** and **client expectations**, not third-party bridge algorithms.

## `misc/bridge/references/`

Prior art for MUC naming: single-nick bridges (black-hole, matterbridge, discord-xmpp-bridge); per-user sanitization (jabagram, slidge/slidcord); biboumi (IRC↔MUC gateway). atl.chat’s **JID local part + sanitize + optional suffix** targets component multi-presence + echo matching.

## `.cursor/plans/` (repo)

Plans such as `custom_discord_irc_xmpp_bridge_0068eac0`, `bridge_implementation_stages_b21ce01f`, `irc_puppets_and_reference_insights_2e3bda2d` — historical intent and audits; reconcile with `apps/bridge` when changing behavior.

## `.kiro/specs/`

Kiro feature specs (e.g. bridge optimization): align tests and requirements when touching performance or docs.

## User evidence

XMPP MUC client: multiple relay sources in message body under the **same occupant `kaizen`** — stable puppet nick across bridge legs.

---

*Update this file when additional reference review completes.*
