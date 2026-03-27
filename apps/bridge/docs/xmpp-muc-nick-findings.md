# XMPP MUC nick / bridge — reference review findings

This file records outcomes from reviewing in-repo `references/`, `misc/bridge/references/`, `.cursor/plans/`, and `.kiro/specs/` (investigation notes; not the Cursor plan in `~/.cursor/plans/`).

## Implementation (this repo)

- **`xmpp_jid_or_plain_to_muc_nick`** — Portal bare JID → local part → `sanitize_nick` (max 23 per Prosody).
- **`puppet_muc_nick_from_base`** — optional `BRIDGE_XMPP_PUPPET_NICK_SUFFIX` for occupant collision with a human in the same room.
- **`puppet_muc_xep0172_display_nick`** — when a suffix is set, MUC join presence includes XEP-0172 (`pnick`) with the unsuffixed base so UIs can show `kaizen` while the occupant resource is `kaizen_d` (client support varies).
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

XMPP MUC client: relay lines whose **body** says “from discord” vs “from hexchat” all show under the **same occupant `kaizen`** — one nick column, stable puppet.

## “Multiple kaizens” — what was actually going on

**In one XMPP MUC, you cannot have two different people both using the exact occupant nick `kaizen` at the same time.** XEP-0045 requires nick uniqueness per room; the server rejects or rewrites the second join. So “multiple kaizens” was never *two MUC occupants both named `kaizen`*.

What people **see** that *feels* like “lots of kaizens”:

1. **Many messages, one occupant** — The timeline repeats the **same** sender label (`kaizen`) on every line because **one** bridge puppet (one Discord user → one resolved MUC nick) sent **many** messages. That is one `kaizen`, not several.

2. **Same nick, different bridge legs** — IRC traffic and Discord traffic for **the same user** still use **one** Discord `author_id` and thus **one** resolved nick (`kaizen`). The bridge does not create a second occupant for “HexChat” vs “Discord”; it only changes the **message body** (your tests: “from hexchat” / “from discord”). So you still have **one** MUC `kaizen`, not two.

3. **Other apps (e.g. Discord) are a different namespace** — If you also had rows like `kaizen` (webhook), `kaizen_` (native), or `admin`, those are **Discord** display layers, not extra XMPP occupants. Comparing Discord and XMPP side-by-side can look like “many kaizens” without violating MUC rules on the XMPP side.

4. **Close variants are different nicks** — `kaizen` vs `kaizen_` (trailing underscore) are **two different** occupant strings if both were in the same MUC — that is how two humans (or human + bot) avoid collision without both being literally `kaizen`.

**Bottom line:** Before any JID local-part work, **dev fallback** already produced a **single** display-based nick per Discord user. “Multiple kaizens” in chat was **repeated lines from one puppet**, or **the same string in different apps**, not duplicate MUC nicks for the same string.

---

*Update this file when additional reference review completes.*
