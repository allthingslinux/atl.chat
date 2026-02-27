# UnrealIRCd Configuration Audit Report

**Date:** 2026-02-26
**Auditor:** Cloud Agent (automated cross-reference)
**Local config:** `apps/unrealircd/config/unrealircd.conf.template` (UnrealIRCd 6.2.0.1)
**Reference:** UnrealIRCd 6.1.10 `modules.default.conf` and 6.x `example.conf` from repo docs

---

## A. Loaded Modules

### Comparison: Local vs `modules.default.conf` (6.1.10)

All **229** upstream default modules are present in the local config. The local config loads **13 additional** modules beyond the defaults:

| Extra Module | Purpose | Verdict |
|---|---|---|
| `cloak_sha256` | SHA-256 cloaking (required, upstream example loads it separately) | 🟢 Correct |
| `webserver` | HTTP server for RPC/WebSocket | 🟢 Required for WebSocket + RPC |
| `websocket` | WebSocket protocol support | 🟢 Required for web clients |
| `antirandom` | Block random-looking user/nick/ident | 🟢 Good security hardening |
| `antimixedutf8` | Block mixed-script spam | 🟢 Good anti-spam measure |
| `ircops` | `/IRCOPS` command to list online opers | 🟢 Useful for community |
| `staff` | `/STAFF` command | 🟢 Useful for community |
| `nocodes` | Strip mIRC color codes from certain channels | 🟢 Nice to have |
| `maxperip` | Per-IP connection limiting | 🟢 Good security hardening |
| `utf8functions` | UTF-8 nick/channel support | 🟢 Modern best practice |
| `third/showwebirc` | Show WebIRC info in WHOIS | 🟢 Good for transparency |
| `third/metadata` | IRCv3 draft/metadata | 🟢 Modern feature |
| `third/react` | IRCv3 draft/react (reactions) | 🟢 Modern feature |
| `third/redact` | IRCv3 draft/message-redaction | 🟢 Modern feature |
| `third/relaymsg-atl` | Stateless bridging (atl.chat fork) | 🟢 Required for bridge |

### Findings

- 🟢 **OK** — All upstream default modules are loaded. No important modules are missing.
- 🟢 **OK** — Extra modules are all justified and well-documented with `@if module-loaded()` guards where appropriate.
- 💡 **SUGGESTION** — The local `modules.default.conf` reference is version 6.1.10 while the server runs 6.2.0.1. Consider checking the 6.2.0.1 `modules.default.conf` for any newly added modules. Specifically, the `maxperip` module was added as a standalone module in newer versions (it's loaded locally but not in the 6.1.10 reference, which is correct behavior).

---

## B. TLS/SSL Configuration

**Config lines:** `set { tls { ... } }` (lines 465–513)

### Findings

- 🟢 **OK** — **TLS Protocols**: `"TLSv1.2,+TLSv1.3"` — correctly enforces TLS 1.2+ only. No SSLv3, TLS 1.0, or TLS 1.1.

- 🟢 **OK** — **TLS 1.2 Ciphers**: Strong ECDHE-only cipher suite with Forward Secrecy. All ciphers use AEAD (GCM or ChaCha20-Poly1305). No weak ciphers (RC4, DES, 3DES, CBC).

  ```
  ECDHE-ECDSA-CHACHA20-POLY1305:ECDHE-RSA-CHACHA20-POLY1305:ECDHE-ECDSA-AES256-GCM-SHA384:
  ECDHE-RSA-AES256-GCM-SHA384:ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256
  ```

- 🟢 **OK** — **TLS 1.3 Cipher Suites**: Complete list including all standard TLS 1.3 suites plus CCM variants.

- 🟢 **OK** — **ECDH Groups**: Includes `X25519MLKEM768` (post-quantum hybrid), `X25519`, and standard NIST curves. Both the new `groups` directive and legacy `ecdh-curves` are set for compatibility.

- 🟢 **OK** — **STS Policy**: Enabled with configurable duration/preload via environment variables. The phased rollout plan in the comments (1m → 1d → 30d → 180d) is an excellent approach.

- 🟢 **OK** — **Certificate Expiry Notification**: `certificate-expiry-notification yes;` — good operational practice.

- 🟢 **OK** — **Trusted CA File**: Explicit CA bundle path set for certificate validation.

- 💡 **SUGGESTION** — **TLS 1.3 CCM Ciphers**: The `TLS_AES_128_CCM_8_SHA256` and `TLS_AES_128_CCM_SHA256` suites are rarely used by IRC clients and add no real benefit. Consider removing them for a cleaner config, though they cause no harm.

- 💡 **SUGGESTION** — **`no-client-certificate`**: This is set, which is standard for public IRC servers. If you ever want to support certificate-based authentication (certfp), this would need to be reconsidered at the per-listen level.

---

## C. `set` Block Analysis

### Network Configuration (lines 735–758)

- 🟢 **OK** — `network-name`, `default-server`, `services-server`, `stats-server`, `sasl-server` — all correctly templated with `${IRC_SERVICES_SERVER}` and `${IRC_DOMAIN}`.
- 🟢 **OK** — `help-channel "#support"` — reasonable choice.
- 🟢 **OK** — `cloak-keys` — properly sourced from environment variables.
- 🟢 **OK** — `hiddenhost-prefix` — configurable via `${IRC_CLOAK_PREFIX}`.
- 🟢 **OK** — `cloak-method ip` — good choice for privacy.

### Server Configuration (lines 842–965)

- 🟢 **OK** — `kline-address` — set to `${IRC_ADMIN_EMAIL}`.
- 🟢 **OK** — `modes-on-connect "+ixw"` — matches upstream example. `+i` (invisible), `+x` (cloaked host), `+w` (wallops).
- 🟢 **OK** — `modes-on-oper "+xws"` — good. Ensures opers get cloaking + wallops + server notices.
- 🟢 **OK** — `modes-on-join "+nt"` — standard default (no external messages + topic lock).
- 🟢 **OK** — `restrict-usermodes "x"` — prevents users from removing cloaking. Excellent security practice.
- 🟢 **OK** — `maxchannelsperuser 10` — matches upstream.
- 🟢 **OK** — `anti-spam-quit-message-time 10s` — matches upstream.
- 🟢 **OK** — `oper-auto-join "#mod-chat"` — appropriate for team use.
- 🟢 **OK** — `hide-ulines` and `show-connect-info` — correct.

### Missing from upstream example

- 🟡 **WARNING** — **Missing `set::spamfilter` block**: The upstream example.conf includes:

  ```
  spamfilter {
      ban-time 1d;
      ban-reason "Spam/Advertising";
      virus-help-channel "#help";
  }
  ```

  The local config has no `set::spamfilter` sub-block. While the included `spamfilter.conf` file provides rules, the global defaults (ban-time, ban-reason, virus-help-channel) are not explicitly set. UnrealIRCd will use built-in defaults, but it's best practice to set these explicitly.

  **Fix:** Add inside a `set { }` block:

  ```
  spamfilter {
      ban-time 1d;
      ban-reason "Spam/Advertising";
      virus-help-channel "#help";
  }
  ```

- 🟡 **WARNING** — **Missing `set::connthrottle` block**: The upstream example.conf has a comprehensive `connthrottle` configuration:

  ```
  connthrottle {
      except { reputation-score 24; identified yes; }
      new-users { local-throttle 20:60; global-throttle 30:60; }
      disabled-when { reputation-gathering 1w; start-delay 3m; }
  }
  ```

  The local config loads the `connthrottle` module but has no configuration for it. The module will use built-in defaults, which may not be optimal.

  **Fix:** Add a `set { connthrottle { ... } }` block mirroring or customizing the upstream defaults.

- 🟡 **WARNING** — **Missing `set::oper-only-stats`**: The upstream example restricts stats commands to opers:

  ```
  oper-only-stats "okfGsMRUEelLCXzdD";
  ```

  The local config doesn't set this, meaning all stats are visible to everyone. While modern UnrealIRCd 6 has better defaults than older versions, consider restricting sensitive stats.

  **Fix:** Add `oper-only-stats "okfGsMRUEelLCXzdD";` inside a `set` block.

- 💡 **SUGGESTION** — **Missing `set::whois-details` for certfp**: While whois-details are configured for `webirc` and `websocket`, consider adding certfp visibility control.

- 💡 **SUGGESTION** — **`set::allowed-nickchars`**: The `charsys` module is loaded but no `set::allowed-nickchars` is configured. If you want to allow UTF-8 nicknames (which `utf8functions` module supports), you should explicitly set this. Example:

  ```
  set { allowed-nickchars { latin-utf8; }; }
  ```

---

## D. `allow` Blocks

**Config lines:** 558–562

```
allow {
    mask *@*;
    class clients;
    maxperip 5;
}
```

### Findings

- 🟢 **OK** — Single allow block, open to all — appropriate for a public IRC server.
- 🟢 **OK** — `maxperip 5` — matches upstream old example.conf (5). The modern example uses 3, which is more restrictive.
- 💡 **SUGGESTION** — Consider lowering `maxperip` to 3 (matching modern upstream defaults) to reduce abuse surface. Users needing more connections can be handled with specific allow blocks.

---

## E. `listen` Blocks

**Config lines:** 288–456

| Port | Options | Purpose | Verdict |
|---|---|---|---|
| Unix socket (`rpc.socket`) | `rpc` | RPC for webpanel | 🟢 OK |
| Unix socket (`services.sock`) | (none) | Atheme services link | 🟢 OK |
| 6697 | `tls` | Standard IRC TLS port | 🟢 OK |
| 6900 | `tls; serversonly` | Server linking (TLS) | 🟢 OK |
| 6901 | `serversonly` | Server linking (plaintext, for Docker) | 🟢 OK (see note) |
| 8600 | `rpc; tls` | RPC API with TLS | 🟢 OK |
| 8000 | `websocket { type text; }` | WebSocket for web clients | 🟢 OK (see note) |

### Findings

- 🟢 **OK** — No plaintext client port (6667) is open. Good security practice.
- 🟢 **OK** — Port 8000 WebSocket without TLS is justified because TLS is terminated at the reverse proxy (NPM).
- 🟢 **OK** — Port 8600 RPC has its own TLS configuration with explicit cert/key paths.
- 🟢 **OK** — Port 6901 plaintext for servers is justified for Docker-internal Atheme communication. The `plaintext-policy { server allow; }` is correct for this use case.

- 💡 **SUGGESTION** — Port 8000 (WebSocket): Consider binding to a specific internal IP rather than `*` if the WebSocket should only be accessible from the reverse proxy, not directly from the internet.

- 💡 **SUGGESTION** — Port 6901 plaintext server port: Since Atheme connects via Unix socket (`services.sock`), this port may be unnecessary. If it's not used, removing it reduces the attack surface.

---

## F. `link` Blocks

**Config lines:** 542–550

```
link ${IRC_SERVICES_SERVER} {
    incoming {
        mask *;
        password "${IRC_SERVICES_PASSWORD}";
    }
    password "${IRC_SERVICES_PASSWORD}";
    class servers;
}
```

### Findings

- 🟡 **WARNING** — **`incoming { mask * }`**: The mask accepts connections from any IP. While this is somewhat mitigated by the password requirement and Docker network isolation, it would be more secure to restrict the mask to the Docker network range.

  **Fix:**

  ```
  incoming {
      mask 172.16.0.0/12;
      password "${IRC_SERVICES_PASSWORD}";
  }
  ```

- 🟡 **WARNING** — **No TLS for services link**: The link block doesn't specify `options { tls; }`. Since Atheme connects via Unix socket (port 6901 or `services.sock`), this is acceptable for the current Docker setup. However, if services ever connect over the network, TLS should be required.

- 🟢 **OK** — Password is properly templated from environment variable.
- 🟢 **OK** — The services password (`IRC_SERVICES_PASSWORD`) in `.env.example` has a placeholder that forces users to change it.

---

## G. `log` Blocks

**Config lines:** 293–310, 808–839

### Findings

- 🟢 **OK** — **Memory log**: For RPC (1000 lines, 7 days) — matches upstream best practice.
- 🟢 **OK** — **Text log**: `ircd.log` with 100M maxsize — matches upstream example.
- 🟢 **OK** — **JSON log**: `ircd.json.log` with 250M maxsize — matches upstream example and provides machine-readable audit trail.
- 🟢 **OK** — **Source filters**: Identical exclusions across all log blocks (`!debug`, `!join.*`, `!part.*`, `!kick.*`) — consistent and appropriate.
- 🟢 **OK** — Log path templated via `${IRC_LOG_PATH}`.

---

## H. `except ban` Blocks

**Config line:** 729–732

```
except ban {
    mask *@172.16.0.0/12;
    type { blacklist; connect-flood; maxperip; handshake-data-flood; }
}
```

### Findings

- 🟢 **OK** — Covers the entire Docker bridge subnet range (172.16.0.0/12).
- 🟢 **OK** — Exemption types are appropriate: `blacklist` (don't DNSBL internal IPs), `connect-flood` (allow many container connections), `maxperip` (multiple containers share subnet), `handshake-data-flood` (services may send bursts).

- 💡 **SUGGESTION** — The upstream example also exempts IRCCloud (`*.irccloud.com`). If your network expects IRCCloud users, consider adding a similar exception:

  ```
  except ban {
      mask *.irccloud.com;
      type { maxperip; connect-flood; }
  }
  ```

- 💡 **SUGGESTION** — Consider adding `type all;` exception for a specific oper IP to ensure opers can always connect even during accidental self-bans.

---

## I. `blacklist` (DNSBL) Blocks

**Config lines:** 692–723

| DNSBL | Reply Codes | Action | Ban Time |
|---|---|---|---|
| `dnsbl.dronebl.org` | 3,5-16 | gline | 24h |
| `rbl.efnetrbl.org` | 1,4,5 | gline | 24h |
| `dnsbl.tornevall.org` | 1-16 | gline | 24h |

### Findings

- 🟢 **OK** — DroneBL and EFnetRBL are the two most commonly recommended DNSBLs for IRC. Both match the upstream example exactly.

- 🟡 **WARNING** — **Tornevall DNSBL** (`dnsbl.tornevall.org`): This DNSBL has had reliability issues historically and some networks have stopped using it. It's not in the upstream UnrealIRCd example. The extremely broad reply code range (1-16 = everything) could lead to false positives.

  **Fix:** Consider removing the `tornevall` blacklist or at minimum narrowing the reply codes to specific abuse categories. If you want a third DNSBL, consider `dnsbl.sectoor.de` or `dnsbl.ahbl.org` instead, though availability varies.

- 🟢 **OK** — Ban time of 24h is reasonable for all blacklists.
- 🟢 **OK** — Reason messages include lookup URLs for users to check their IP.
- 🟢 **OK** — Action `gline` is appropriate (network-wide ban).

---

## J. `oper` Blocks

**Config lines:** 761–787

### Admin Oper

```
oper admin {
    class opers;
    mask *@*;
    password "${IRC_OPER_PASSWORD}";
    operclass netadmin-with-override;
    swhois "is the Network Administrator";
    vhost "${IRC_STAFF_VHOST}";
    require-modes "";
}
```

### Findings

- 🟢 **OK** — Password sourced from `${IRC_OPER_PASSWORD}`. The `.env.example` shows an `$argon2id$...` hash, meaning the password is properly hashed (not plaintext).
- 🟢 **OK** — `operclass netadmin-with-override` — appropriate for the primary admin.
- 🟢 **OK** — `swhois` and `vhost` are set for identification.

- 🔴 **CRITICAL** — **`mask *@*`**: The admin oper block accepts connections from ANY host. This means anyone who knows (or brute-forces) the oper password can become netadmin from anywhere. Best practice is to restrict this to known IPs or at minimum require TLS certificate fingerprint authentication.

  **Fix (at minimum):**

  ```
  oper admin {
      ...
      mask *@172.16.0.0/12;  /* Docker network only, or specific IPs */
      /* Or better: use certificate fingerprint */
      /* password "$argon2id..."; */
      /* require-modes "z"; */  /* Require TLS connection */
  }
  ```

- 🟡 **WARNING** — **`require-modes ""`**: This is explicitly set to empty, meaning no user modes are required to OPER up. Consider requiring `require-modes "z"` to force TLS for oper authentication:

  ```
  require-modes "z";
  ```

### Bridge Oper

```
oper bridge {
    class opers;
    mask *@*bridge*;
    password "${BRIDGE_IRC_OPER_PASSWORD}";
    operclass bridge-oper;
}
```

- 🟢 **OK** — Restricted mask (`*@*bridge*`) limits this oper to bridge hostnames.
- 🟢 **OK** — `bridge-oper` operclass has minimal permissions (just channel override + relaymsg).
- 🟢 **OK** — Password sourced from environment variable.

---

## K. `set::anti-flood` / `set::connthrottle`

### Anti-Flood (lines 896–964)

- 🟢 **OK** — **Channel anti-flood profiles**: Five profiles (very-strict through very-relaxed) with default "normal" — excellent granularity.
- 🟢 **OK** — **Handshake data flood**: 4k limit with 10m zline — reasonable protection.
- 🟢 **OK** — **Target flood protection**: Comprehensive rate limits for channel/private messages, notices, and tagmsg.
- 🟢 **OK** — **Known vs unknown user differentiation**: Proper two-tier system with stricter limits for unknown users.

- 🟡 **WARNING** — **`connect-flood 20:10`**: This allows 20 connections per 10 seconds per IP, which is described as "relaxed for testing." For production, this should be tightened significantly. The upstream default is typically 3:60 (3 per 60 seconds).

  **Fix for production:**

  ```
  connect-flood 3:60;
  ```

### ConnThrottle

- 🟡 **WARNING** — **Missing `set::connthrottle` configuration**: The `connthrottle` module is loaded but not configured. This module needs explicit configuration to be effective. Without it, the module uses built-in defaults which may not be optimal for this network.

  **Fix:** Add:

  ```
  set {
      connthrottle {
          except {
              reputation-score 24;
              identified yes;
          }
          new-users {
              local-throttle 20:60;
              global-throttle 30:60;
          }
          disabled-when {
              reputation-gathering 1w;
              start-delay 3m;
          }
      }
  }
  ```

---

## L. `drpass` Block

### Finding

- 🔴 **CRITICAL** — **Missing `drpass` block**: The local configuration has NO `drpass` block. The `/DIE` and `/RESTART` commands have no password protection. Any IRC operator with sufficient privileges could accidentally or maliciously shut down or restart the server without authentication.

  The upstream example.conf includes:

  ```
  drpass {
      restart "restart";
      die "die";
  }
  ```

  **Fix:** Add a `drpass` block with strong, hashed passwords:

  ```
  drpass {
      restart "${IRC_DRPASS_RESTART}";
      die "${IRC_DRPASS_DIE}";
  }
  ```

  And add corresponding environment variables to `.env.example` with argon2id-hashed values.

---

## M. `set::plaintext-policy` / `set::outdated-tls-policy`

**Config lines:** 515–538

### Plaintext Policy

```
plaintext-policy {
    server allow;
    user allow;
    oper deny;
    user-message "...";
    oper-message "...";
}
```

### Findings

- 🟢 **OK** — `server allow` — correct for Docker-internal Atheme link on plaintext Unix socket.
- 🟢 **OK** — `oper deny` — opers must use TLS. Good security practice.
- 🟢 **OK** — `user allow` with STS redirect — correct phased approach. Users with STS-capable clients get auto-redirected to TLS.
- 🟢 **OK** — Custom user-message and oper-message provide clear guidance.
- 💡 **SUGGESTION** — For production, eventually move `user` to `warn` or `deny` once STS has been in place long enough (Phase 4 in the config comments).

### Outdated TLS Policy

```
outdated-tls-policy {
    user warn;
    oper deny;
    server deny;
}
```

- 🟢 **OK** — Users get warned about outdated TLS (not kicked).
- 🟢 **OK** — Opers and servers are denied with outdated TLS. Excellent security practice.
- 🟢 **OK** — Custom messages provide actionable guidance.

---

## N. WebSocket Configuration

**Config lines:** 443–456

```
listen {
    ip *;
    port 8000;
    options {
        websocket { type text; }
    }
}
```

### Findings

- 🟢 **OK** — WebSocket listener on port 8000, type `text` — correct for IRC over WebSocket.
- 🟢 **OK** — TLS is correctly disabled here because it's terminated at the reverse proxy (NPM). This is documented in the comments.
- 🟢 **OK** — Both `websocket_common` and `websocket` modules are loaded.
- 🟢 **OK** — The `webserver` module is loaded for HTTP functionality.

- 💡 **SUGGESTION** — Consider adding `websocket { type text; origin "https://your-domain.com"; }` to restrict WebSocket connections to your web application's origin, preventing unauthorized cross-origin connections.

---

## O. Spamfilter and Badwords

### Spamfilter (`spamfilter.conf`)

- 🟡 **WARNING** — **Outdated rules**: The file itself states: "Since 2005 these rules are no longer maintained. The main purpose nowadays is to serve as an example." All the rules target malware/trojans from the early 2000s (sub7, mIRC exploits, fagot worm, etc.). None of these are relevant modern threats.

  **Fix:** Either:
  1. Write new, modern spamfilter rules targeting current IRC spam patterns (crypto scams, phishing links, mass-highlight floods, invite spam), or
  2. Remove/empty the file and rely on dynamic spamfilters via `/SPAMFILTER` command, or
  3. Keep as-is but acknowledge the rules provide no real protection against modern threats.

### Badwords (`badwords.conf`)

- 🟡 **WARNING** — **Potentially problematic word list**: The badwords file is the default from UnrealIRCd circa 2000 (by Carsten V. Munk). It contains several slurs including `faggot` and `fag`. For a modern Linux community:
  - The word list is very basic (only 20 entries)
  - Some entries may create false positives (e.g., "fag" matching in legitimate words, `*fuck*` wildcard matching "Buckfastleigh" etc.)
  - The list doesn't cover modern harassment patterns
  - Consider whether a word filter is the right approach vs. moderation tooling

  **Fix:** Review and update the badwords list to match your community standards, or disable channel/user mode +G if you prefer moderation-based approaches.

---

## P. Third-Party Modules

### Installed Modules

| Module | Config | Status |
|---|---|---|
| `third/showwebirc` | No config needed | 🟢 OK — works out of the box |
| `third/metadata` | `metadata { max-user-metadata 10; max-channel-metadata 10; max-subscriptions 10; }` | 🟢 OK — reasonable limits |
| `third/react` | No config needed | 🟢 OK — works out of the box |
| `third/redact` | No config needed | 🟢 OK — works out of the box |
| `third/relaymsg-atl` | `relaymsg { hostmask "bridge@${IRC_DOMAIN}"; require-separator no; }` | 🟢 OK — custom fork, properly configured |

### Findings

- 🟢 **OK** — All third-party modules in `third-party-modules.list` are loaded in the config.
- 🟢 **OK** — `relaymsg` is properly configured with `require-separator no` for clean bridge nicks.
- 🟢 **OK** — `metadata` limits are reasonable (10 per user/channel/subscriptions).

### Commented-Out Modules in `third-party-modules.list`

The file lists these as potential additions:

- `third/commandsno` — SNOMASK-based command logging
- `third/clones` — Clone detection
- `third/repeatprot` — Repeat message protection
- `third/block_masshighlight` — Block mass highlighting in channels

- 💡 **SUGGESTION** — **`third/block_masshighlight`** is highly recommended for any community IRC server. Mass-highlighting (mentioning many nicks at once) is a common harassment/spam tactic. Consider enabling this module.

- 💡 **SUGGESTION** — **`third/repeatprot`** would complement the existing anti-flood settings by catching repeated messages that slip through rate limits.

---

## Additional Findings

### WEBIRC Block (line 370–373)

```
webirc {
    mask ${ATL_GATEWAY_IP}/32;
    password "change_me_webirc_password";
}
```

- 🔴 **CRITICAL** — **Hardcoded placeholder password**: The WEBIRC password is `"change_me_webirc_password"` which is NOT an environment variable. Unlike other passwords in the config (which use `${VAR}` syntax), this one is a literal string. If the config template is processed without changing this, the WEBIRC password will be the placeholder text.

  **Fix:** Change to use an environment variable:

  ```
  password "${ATL_WEBIRC_PASSWORD}";
  ```

  And add `ATL_WEBIRC_PASSWORD` to `.env.example`.

### RPC User (line 790–794)

```
rpc-user "${WEBPANEL_RPC_USER}" {
    match { ip *; }
    rpc-class full;
    password "${WEBPANEL_RPC_PASSWORD}";
}
```

- 🟡 **WARNING** — **`match { ip *; }`**: The RPC user can connect from any IP. While the RPC port (8600) requires TLS, restricting to known IPs would be more secure:

  ```
  match { ip 172.16.0.0/12; }
  ```

### Proxy/WEBIRC Block for The Lounge (lines 376–380)

```
proxy thelounge {
    type webirc;
    match { ip 172.16.0.0/12; }
    password "${THELOUNGE_WEBIRC_PASSWORD}";
}
```

- 🟢 **OK** — Properly restricted to Docker network range.
- 🟢 **OK** — Password sourced from environment variable.

### Auto Vhost (lines 797–803)

```
vhost {
    auto-login yes;
    mask { identified yes; }
    vhost ${IRC_DOMAIN};
}
```

- 🟢 **OK** — Gives all identified users a clean vhost matching the IRC domain. Good for privacy.

### Ban Nick Blocks (lines 591–689)

- 🟢 **OK** — Comprehensive list covering services names, system names, and generic names.
- 🟡 **WARNING** — **Overly broad patterns**: `*IRC*` will block any nick containing "IRC" (e.g., "CircleOfLife", "QuIRCky"). Similarly, `*admin*` blocks "administrator" type nicks but also catches legitimate nicks like "badminton". `*server*` would catch "observer". Consider making these patterns more specific.

  **Fix example:**

  ```
  ban nick { mask "IRC"; reason "Reserved for network"; }
  ban nick { mask "IRC-*"; reason "Reserved for network"; }
  ```

### Missing `aliases` Include

- 💡 **SUGGESTION** — The upstream example includes `aliases/anope.conf` for service aliases (/NickServ, /ChanServ, etc.). The local config doesn't include any aliases file. Since Atheme is used (which is compatible with Anope aliases), consider adding:

  ```
  include "aliases/anope.conf";
  ```

  This provides `/NS`, `/CS`, `/OS`, `/MS` shortcut commands.

---

## Summary

### By Severity

| Severity | Count | Items |
|---|---|---|
| 🔴 CRITICAL | 3 | Missing `drpass` block; admin oper `mask *@*`; hardcoded WEBIRC password |
| 🟡 WARNING | 8 | Missing connthrottle config; missing spamfilter set block; missing oper-only-stats; relaxed connect-flood; tornevall DNSBL; link mask too open; RPC user match too open; overly broad ban nick patterns |
| 🟢 OK | 35+ | Most configuration is solid and well-documented |
| 💡 SUGGESTION | 12 | Various optional improvements |

### Priority Fixes

1. **Add `drpass` block** with hashed passwords for `/DIE` and `/RESTART`
2. **Fix WEBIRC password** to use environment variable instead of hardcoded placeholder
3. **Restrict admin oper mask** from `*@*` to specific IPs or Docker network
4. **Add `set::connthrottle`** configuration block
5. **Tighten `connect-flood`** from `20:10` to production values
6. **Add `set::spamfilter`** defaults block
7. **Restrict link block mask** to Docker network range
8. **Add `set::oper-only-stats`** to hide sensitive stats from regular users

### Overall Assessment

The configuration is **well above average** for a Docker-deployed IRC server. The TLS configuration is excellent (including post-quantum cryptography support), the anti-flood settings are comprehensive with proper known/unknown user differentiation, and the module selection is thorough. The use of environment variable templating for sensitive values is good practice. The main areas for improvement are the three critical findings (drpass, oper mask, WEBIRC password) and adding the missing `connthrottle` configuration.
