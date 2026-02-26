# Atheme IRC Services Configuration Audit Report

**Date:** 2026-02-26
**Local config:** `apps/atheme/config/atheme.conf.template`
**Upstream reference:** Atheme `master` branch — `dist/atheme.conf.example`
**Upstream modules:** `modules/` directory tree

---

## A. `serverinfo` Block

### 🟢 OK — Server name, desc, numeric properly templated

```conf
name = "${ATHEME_SERVER_NAME}";     # .env.example: services.atl.chat ✅
desc = "${ATHEME_SERVER_DESC}";     # .env.example: "All Things Linux IRC Services" ✅
numeric = "${ATHEME_NUMERIC}";      # .env.example: 00A (matches upstream default) ✅
recontime = ${ATHEME_RECONTIME};    # .env.example: 10 (matches upstream default) ✅
netname = "${ATHEME_NETNAME}";      # .env.example: atl.chat ✅
```

All values are properly templated via `${VAR}` for substitution by `prepare-config.sh`. Defaults in `.env.example` are reasonable.

### 🟢 OK — `casemapping = ascii`

Correct for UnrealIRCd. Upstream docs explicitly state: *"Bahamut, Unreal, and other 'DALnet'-style IRCds will use ASCII case mapping."*

### 🟢 OK — `hidehostsuffix`, `adminname`, `adminemail`, `registeremail`

All properly templated. Default values are network-specific and sensible.

### 🟡 WARNING — `loglevel = { debug; }` is excessively verbose

```conf
# Local:
loglevel = { debug; };

# Upstream default:
loglevel = { admin; error; info; network; wallops; };
```

**Issue:** `debug` is a meta-keyword that enables ALL log categories, including `rawdata` (raw IRC protocol data, which can include passwords for some operations) and `commands` (every single command used). This is appropriate for development but **not** for production.

**Fix:** For production, use:

```conf
loglevel = { admin; error; info; network; wallops; };
```

Or at most add `commands` and `register` for auditing:

```conf
loglevel = { admin; error; info; network; wallops; commands; register; set; denycmd; };
```

### 🟢 OK — `maxcertfp`, `maxlogins`, `maxusers`, `mdlimit`, `emaillimit`, `emailtime`

All match upstream defaults exactly.

### 🟢 OK — `auth = none`

Matches upstream default. Email verification is disabled. This is fine for networks that don't require email confirmation for registration.

### 💡 SUGGESTION — Consider enabling `auth = email` for production

If spam registration is a concern, enabling email verification provides an additional layer of protection. The local config has `waitreg_time = 30` in the NickServ block which helps, but email verification is stronger.

### 🟢 OK — `mta = "/usr/sbin/sendmail"`

Matches upstream. Note: in the Docker container, sendmail may not be installed. This only matters if `auth = email` is enabled or email-based password recovery is used.

---

## B. `uplink` Block

### 🟢 OK — Uplink host and password properly templated

```conf
uplink "${IRC_DOMAIN}" {
    host = "${ATHEME_UPLINK_HOST}";     # .env.example: 127.0.0.1
    port = ${ATHEME_UPLINK_PORT};       # .env.example: 6901
    send_password = "${IRC_SERVICES_PASSWORD}";
    receive_password = "${IRC_SERVICES_PASSWORD}";
};
```

- Both `send_password` and `receive_password` use the same `${IRC_SERVICES_PASSWORD}` — this is correct and matches how UnrealIRCd is typically configured for services links.
- Default password `change_me_secure_services_pass` in `.env.example` is clearly marked as needing change.

### 🟢 OK — No TLS on uplink (by design)

The uplink uses port 6901 (non-TLS). This is correct because:

1. **Atheme does not support TLS for uplinks** — the upstream docs explicitly state: *"Atheme does not currently link over TLS. To link Atheme over TLS, please connect Atheme to a local IRCd."*
2. The Docker Compose configuration uses `network_mode: service:atl-irc-server`, so Atheme shares the network namespace with UnrealIRCd — the connection is truly `127.0.0.1` and never traverses a network boundary.

### 💡 SUGGESTION — Document `ATHEME_UPLINK_SSL_PORT` purpose

`.env.example` defines `ATHEME_UPLINK_SSL_PORT=6900` but it's never used in the Atheme config template. Consider either:

- Removing it from `.env.example` to avoid confusion, or
- Adding a comment explaining it's reserved for future TLS support

---

## C. `loadmodule` Statements

### 🟢 OK — Protocol and backend modules

```conf
loadmodule "protocol/unreal4";   # ✅ Correct for UnrealIRCd 4+/6.x
loadmodule "backend/opensex";    # ✅ Recommended by upstream
```

### 🟢 OK — Crypto module (pbkdf2v2 with SCRAM-SHA-256)

```conf
loadmodule "crypto/pbkdf2v2";
```

Loaded first before other crypto modules. SCRAM-SHA-256 configured in `crypto{}` block. This is the recommended setup for SASL SCRAM support.

### 🟡 WARNING — Missing `crypto/pbkdf2` verify-only module

```conf
# Upstream loads BOTH:
loadmodule "crypto/pbkdf2v2";
loadmodule "crypto/pbkdf2";     # Verify-only, for Atheme <= 7.2 compat

# Local only loads:
loadmodule "crypto/pbkdf2v2";
```

**Issue:** If you ever migrated from Atheme 7.2 or need to verify passwords created with the old pbkdf2 v1 module, those passwords would fail verification without this module.

**Fix:** Add after pbkdf2v2:

```conf
loadmodule "crypto/pbkdf2";     /* Verify-only for Atheme <= 7.2 compat */
```

**Severity note:** Only a warning because this is a new deployment that likely has no legacy password hashes. If you're certain no migration from older Atheme will ever occur, this can be safely skipped.

### 🟡 WARNING — Duplicate `saslserv/scram` reference

```conf
# Line 174 (ENABLED):
loadmodule "saslserv/scram";

# Line 258 (COMMENTED OUT):
#loadmodule "saslserv/scram";
```

**Issue:** Confusing — the module IS loaded at line 174, but line 258 has it commented out, making it look like it's disabled. The first load wins, so SCRAM-SHA is functional, but this creates confusion during config review.

**Fix:** Remove the duplicate commented-out line at 258, or add a clear note:

```conf
/* saslserv/scram already loaded above in the SASL section */
```

### 🟢 OK — NickServ modules (comprehensive)

The local config loads significantly more NickServ modules than the upstream defaults, including several that upstream has commented out:

| Module | Local | Upstream | Notes |
|--------|-------|----------|-------|
| `nickserv/access` | ✅ Loaded | ❌ Commented | Access lists — useful feature |
| `nickserv/cert` | ✅ Loaded | ❌ Commented | CertFP management — recommended for security |
| `nickserv/enforce` | ✅ Loaded | ❌ Commented | Nickname enforcement — good for ownership |
| `nickserv/info_lastquit` | ✅ Loaded | ❌ Commented | Nice info feature |
| `nickserv/listlogins` | ✅ Loaded | ❌ Commented | Session management |
| `nickserv/listownmail` | ✅ Loaded | ❌ Commented | Email management |
| `nickserv/set_privmsg` | ✅ Loaded | ❌ Commented | User preference |
| `nickserv/set_private` | ✅ Loaded | ❌ Commented | Privacy feature |
| `nickserv/waitreg` | ✅ Loaded | ❌ Commented | Anti-spam delay |

All additional modules are reasonable choices. The `nickserv/enforce` + `nickserv/waitreg` combination provides good anti-spam protection.

### 🟢 OK — ChanServ modules (comprehensive)

Similar to NickServ, more modules enabled than upstream defaults. Notable additions:

| Module | Local | Upstream | Notes |
|--------|-------|----------|-------|
| `chanserv/quiet` | ✅ Loaded | ❌ Commented | +q support for UnrealIRCd |
| `chanserv/set_private` | ✅ Loaded | ❌ Commented | Channel privacy |
| `chanserv/xop` | ✅ Loaded | ❌ Commented | VOP/HOP/AOP/SOP emulation |

All appropriate choices.

### 🟢 OK — OperServ modules (comprehensive, modern approach)

The local config uses individual `operserv/set_*` modules instead of the deprecated unified `operserv/set` module. This is the **preferred** approach for v7.3.

Additional modules loaded compared to upstream defaults:

- `operserv/clearchan` (upstream commented)
- `operserv/clones` (upstream commented)
- `operserv/genhash` (upstream commented)
- `operserv/greplog` (upstream commented)
- `operserv/soper` (upstream commented)

All good additions for a production network.

### 💡 SUGGESTION — Missing `operserv/set_enforceprefix`

The upstream modules directory includes `operserv/set_enforceprefix.c` which allows temporarily changing the enforcement prefix via OperServ SET. All other `operserv/set_*` modules are loaded, but this one is missing.

**Fix:**

```conf
loadmodule "operserv/set_enforceprefix"; /* SET ENFORCEPREFIX command */
```

### 🟢 OK — MemoServ modules (complete)

All upstream MemoServ modules loaded, plus `memoserv/main` (explicit core initialization).

### 🟢 OK — GroupServ modules (complete)

All upstream GroupServ modules loaded plus `groupserv/invite` (commented out upstream, enabled locally).

### 🟢 OK — SASL modules

```conf
loadmodule "saslserv/authcookie";  # For IRIS/web integration
loadmodule "saslserv/plain";       # Basic SASL
loadmodule "saslserv/scram";       # SCRAM-SHA (loaded at line 174)
```

Matches upstream (with scram enabled, which upstream has commented). Good security posture.

### 🟢 OK — HostServ, HelpServ, StatServ, ALIS, ProxyScan

All fully loaded with comprehensive module sets. These are all commented out in upstream defaults, so the local config is more feature-rich.

### 🟢 OK — Misc modules (httpd, login_throttling, jsonrpc)

```conf
loadmodule "misc/httpd";               # Required for WebPanel/JSON-RPC
loadmodule "misc/login_throttling";    # Password brute-force protection
loadmodule "transport/jsonrpc";        # JSON-RPC for WebPanel/portal
```

All three correctly loaded. Upstream has these commented out; they're required for the atl.chat infrastructure (WebPanel and portal integration).

### 🟢 OK — ProxyScan/DNSBL

```conf
loadmodule "proxyscan/main";
loadmodule "proxyscan/dnsbl";
```

Enabled (upstream has these commented out). Provides DNSBL checking for connecting users. Good security measure.

### 🔴 CRITICAL — `chanfix/main` NOT loaded but `chanfix{}` block exists

```conf
# Line 247 (COMMENTED OUT):
#loadmodule "chanfix/main";

# Lines 451-461 (ACTIVE CONFIG BLOCK):
chanfix {
    nick = "${ATHEME_CHANFIX_NICK}";
    ...
    autofix;
};
```

**Issue:** The `chanfix/main` module is not loaded, but a full `chanfix{}` configuration block is present with `autofix;` enabled. This orphaned configuration block will either:

- Be silently ignored (wasted config)
- Cause a warning/error at startup

**Fix:** Either:

1. Uncomment `loadmodule "chanfix/main";` to enable ChanFix, or
2. Comment out/remove the `chanfix{}` configuration block

### 💡 SUGGESTION — Consider enabling exttarget modules

```conf
#loadmodule "exttarget/oper";
#loadmodule "exttarget/registered";
#loadmodule "exttarget/channel";
#loadmodule "exttarget/chanacs";
#loadmodule "exttarget/server";
```

These are all commented out (matching upstream). Extended targets like `$oper`, `$registered`, and `$channel` are very useful for channel access management on production networks.

**Recommended minimum:**

```conf
loadmodule "exttarget/oper";        /* $oper match type */
loadmodule "exttarget/registered";  /* $registered match type */
loadmodule "exttarget/channel";     /* $channel match type */
```

### 💡 SUGGESTION — BotServ, GameServ, RPGServ intentionally disabled

All three services are commented out in the local config, which matches upstream defaults. Their configuration blocks are still present (templated). This is a clean approach — they can be enabled later by uncommenting the loadmodule lines.

---

## D. `operclass` Blocks

### 🟢 OK — Operclass definitions match upstream exactly

```
operclass "user" { };    # ✅ Matches upstream
operclass "ircop" { };   # ✅ Matches upstream (all same privs)
operclass "sra" { };     # ✅ Matches upstream (extends ircop, needoper)
```

All privilege sets are identical to upstream. The `sra` class correctly:

- Extends `ircop`
- Requires `needoper` (must be opered on IRC)
- Has `massakill` and `akill-anymask` commented out (safe default)

---

## E. `operator` Blocks

### 🔴 CRITICAL — Upstream example operator "jilles" left in config

```conf
operator "jilles" {
    operclass = "sra";
    #password = "$1$3gJMO9by$0G60YE6GqmuHVH3AnFPor1";
};
```

**Issue:** This is a copy-paste from the upstream example config. "jilles" is Jilles Tjoelker, one of the original Atheme developers. This operator block:

1. Grants SRA (Super Root Admin) privileges to anyone with a NickServ account named "jilles"
2. Has no password requirement (the password line is commented out)
3. Is not templated via environment variables

**Risk:** If someone registers the nickname "jilles" on your network and opers up, they would gain full SRA privileges over Atheme services.

**Fix:** Replace with a properly templated operator block, or better yet, use `operserv/soper` (which is already loaded) for runtime oper management and remove the static block entirely:

```conf
/* Operator blocks should be managed via SOPER or include from a separate file */
/* Use OperServ SOPER ADD <account> <operclass> to grant privileges at runtime */
```

Or if a static block is needed:

```conf
operator "${ATHEME_SRA_ACCOUNT}" {
    operclass = "sra";
};
```

---

## F. Service Bot `nickname` Blocks

### 🟢 OK — All service bots properly templated

All 17 service bot blocks use `${ATHEME_*}` template variables:

| Service | Nick Var | Defaults |
|---------|----------|----------|
| NickServ | `${ATHEME_NICKSERV_NICK}` | NickServ |
| ChanServ | `${ATHEME_CHANSERV_NICK}` | ChanServ |
| OperServ | `${ATHEME_OPERSERV_NICK}` | OperServ |
| MemoServ | `${ATHEME_MEMOSERV_NICK}` | MemoServ |
| SaslServ | `${ATHEME_SASLSERV_NICK}` | SaslServ |
| GroupServ | `${ATHEME_GROUPSERV_NICK}` | GroupServ |
| HostServ | `${ATHEME_HOSTSERV_NICK}` | HostServ |
| HelpServ | `${ATHEME_HELPSERV_NICK}` | HelpServ |
| InfoServ | `${ATHEME_INFOSERV_NICK}` | InfoServ |
| Global | `${ATHEME_GLOBAL_NICK}` | Global |
| ChanFix | `${ATHEME_CHANFIX_NICK}` | ChanFix |
| StatServ | `${ATHEME_STATSERV_NICK}` | StatServ |
| ALIS | `${ATHEME_ALIS_NICK}` | ALIS |
| Proxyscan | `${ATHEME_PROXYSCAN_NICK}` | Proxyscan |
| GameServ | `${ATHEME_GAMESERV_NICK}` | GameServ |
| RPGServ | `${ATHEME_RPGSERV_NICK}` | RPGServ |
| BotServ | `${ATHEME_BOTSERV_NICK}` | BotServ |

All default values in `.env.example` match upstream conventions.

### 💡 SUGGESTION — Service bot host values

All service bots use `services.atl.chat` as their host, which is the network's services hostname. This is consistent and correct. However, the bot hosts are all set via individual env vars (e.g., `${ATHEME_NICKSERV_HOST}`) rather than a single shared variable. Consider if a single `ATHEME_SERVICES_HOST` would reduce `.env` complexity.

---

## G. `nickserv` Settings

### 🟢 OK — Core settings reasonable

```conf
maxnicks = 5;           # ✅ Matches upstream
expire = 30;            # ✅ Matches upstream (30 days)
enforce_expire = 14;    # Upstream commented, good value
enforce_delay = 30;     # Upstream commented, reasonable (30 seconds)
enforce_prefix = "Guest"; # Upstream commented, standard prefix
```

### 🟢 OK — `waitreg_time = 30`

Upstream default is 0 (disabled). Setting to 30 seconds provides anti-spam protection by requiring users to be connected for 30 seconds before registering. Good security measure.

### 🟢 OK — `spam` enabled

Tells users about NickServ/ChanServ on connect. Matches upstream.

### 🟢 OK — Aliases and shorthelp

```conf
aliases {
    "ID" = "IDENTIFY";
    "MYACCESS" = "LISTCHANS";
};
shorthelp = "REGISTER IDENTIFY LOGOUT GROUP DROP GHOST ACCESS CERT SET";
```

Standard aliases. Shorthelp is customized to show the most useful commands.

### 🟢 OK — `show_custom_metadata`, `listownmail_canon`, `bad_password_message`

All match upstream defaults.

---

## H. `chanserv` Settings

### 🟢 OK — Core settings reasonable

```conf
maxchans = 5;             # ✅ Matches upstream
fantasy;                  # ✅ Matches upstream
trigger = "!";            # ✅ Matches upstream
expire = 30;              # ✅ Matches upstream
maxchanacs = 0;           # ✅ Matches upstream (unlimited)
maxfounders = 4;          # ✅ Matches upstream
```

### 🟢 OK — `changets` enabled

```conf
changets;
```

This is commented out in upstream but is a security improvement for UnrealIRCd — it changes channel TS on re-creation to prevent takeovers. Upstream notes it's supported for UnrealIRCd (via the protocol module list).

### 🟢 OK — Templates with additions

```conf
templates {
    vop = "+AV";              # ✅ Matches upstream
    hop = "+AHehitrv";        # ✅ Matches upstream
    aop = "+AOehiortv";       # ✅ Matches upstream
    sop = "+AOaefhiorstv";    # ✅ Matches upstream
    founder = "+AFORaefhioqrstv"; # ✅ Matches upstream
    member = "+Ai";           # ➕ Added (upstream has as comment example)
    op = "+AOiortv";          # ➕ Added (upstream has as comment example)
};
deftemplates = "MEMBER=+Ai OP=+AOiortv";
```

Good — enables the member/op templates that upstream only has as examples, and sets them as defaults for new channels.

### 🟢 OK — `antiflood_enforce_method = quiet`

Matches upstream default. Uses quiet mode for flood enforcement rather than kickban or akill.

---

## I. `general` Block Settings

### 🟢 OK — Most settings match upstream

| Setting | Local | Upstream | Match |
|---------|-------|----------|-------|
| `join_chans` | ✅ | ✅ | ✅ |
| `leave_chans` | ✅ | ✅ | ✅ |
| `uflags = { hidemail; }` | ✅ | ✅ | ✅ |
| `cflags = { guard; verbose; }` | ✅ | ✅ | ✅ |
| `flood_msgs = 7` | ✅ | ✅ | ✅ |
| `flood_time = 10` | ✅ | ✅ | ✅ |
| `ratelimit_uses = 5` | ✅ | ✅ | ✅ |
| `ratelimit_period = 60` | ✅ | ✅ | ✅ |
| `kline_time = 7` | ✅ | ✅ | ✅ |
| `clone_time = 0` | ✅ | ✅ | ✅ |
| `commit_interval = 5` | ✅ | ✅ | ✅ |
| `default_clone_allowed = 5` | ✅ | ✅ | ✅ |
| `default_clone_warn = 4` | ✅ | ✅ | ✅ |
| `clone_identified_increase_limit` | ✅ | ✅ | ✅ |
| `uplink_sendq_limit = 1048576` | ✅ | ✅ | ✅ |
| `language = "en"` | ✅ | ✅ | ✅ |
| `immune_level = immune` | ✅ | ✅ | ✅ |
| `show_entity_id` | ✅ | ✅ | ✅ |
| `load_database_mdeps` | ✅ | ✅ | ✅ |
| `match_masks_through_vhost` | ✅ | ✅ | ✅ |

### 🟢 OK — `helpchan` and `helpurl` templated

```conf
helpchan = "${ATHEME_HELP_CHANNEL}";  # .env: #help
helpurl = "${ATHEME_HELP_URL}";       # .env: https://discord.gg/linux
```

Both are uncommented and templated (upstream has them commented out).

---

## J. `saslserv` Settings

### 🟢 OK — Minimal, correct configuration

```conf
saslserv {
    nick = "${ATHEME_SASLSERV_NICK}";
    user = "${ATHEME_SASLSERV_USER}";
    host = "${ATHEME_SASLSERV_HOST}";
    real = "${ATHEME_SASLSERV_REAL}";
    #hide_server_names;
};
```

SaslServ doesn't need aliases or access blocks (upstream docs confirm this). The loaded SASL mechanisms (PLAIN, SCRAM, AUTHCOOKIE) are configured via loadmodule statements.

### 💡 SUGGESTION — Consider restricting `scram_mechanisms`

The `crypto{}` block configures `pbkdf2v2_digest = "SCRAM-SHA-256"` but doesn't set `scram_mechanisms` in the crypto block. This means all SCRAM mechanisms (SHA-1, SHA-256, SHA-512) are advertised to clients, but only SCRAM-SHA-256 digests are stored. The other mechanisms will fail for users.

**Fix:** Add to `crypto{}` block:

```conf
scram_mechanisms = "SCRAM-SHA-256";
```

---

## K. Logging Configuration

### 🟡 WARNING — Single debug-level logfile, no separation

```conf
# Local:
logfile "logs/atheme.log" { debug; };

# Upstream examples (all commented but suggested):
#logfile "var/account.log" { register; set; };
#logfile "var/commands.log" { commands; };
#logfile "var/audit.log" { denycmd; };
```

**Issue:** Everything goes to a single file at debug level. This makes log analysis difficult and the file will grow very quickly. Combined with `serverinfo::loglevel = { debug; }`, this logs raw protocol data, every command, and all debug messages.

**Fix for production:** Split logs by purpose:

```conf
logfile "logs/atheme.log" { error; info; admin; network; };
logfile "logs/commands.log" { commands; };
logfile "logs/audit.log" { register; set; denycmd; request; };
```

### 💡 SUGGESTION — Consider IRC channel logging

```conf
#logfile "#services" { debug; };
#logfile "!snotices" { debug; };
```

Both are commented out. For operations, logging important events to an IRC channel (e.g., `#services`) is valuable for real-time monitoring:

```conf
logfile "#services" { admin; denycmd; error; info; register; request; };
```

---

## L. `memoserv` Settings

### 🟢 OK — Settings reasonable

```conf
maxmemos = 50;   # Upstream: 30
```

More generous than upstream (50 vs 30 memos). This is fine — provides more inbox capacity.

### 🟢 OK — Aliases well-configured

```conf
aliases {
    "MAIL" = "SEND";
    "MSG" = "SEND";
    "DEL" = "DELETE";
    "RM" = "DELETE";
};
```

Upstream has no aliases for MemoServ. These are user-friendly additions.

---

## M. `operserv` Settings

### 🟢 OK — Properly configured

```conf
operserv {
    nick = "${ATHEME_OPERSERV_NICK}";
    ...
    aliases {
        "AKILL" = "AKILL";
        "GLINE" = "AKILL";
        "KLINE" = "AKILL";
    };
    modinspect_use_colors;   # Upstream has commented out — nice feature
};
```

- Standard GLINE/KLINE→AKILL aliases for operators familiar with other IRC daemons
- `modinspect_use_colors` enabled (cosmetic improvement over upstream)
- All essential OperServ modules loaded (see Section C)

---

## N. Security Settings

### 🟢 OK — Password hashing (PBKDF2v2 with SCRAM-SHA-256)

```conf
loadmodule "crypto/pbkdf2v2";
crypto {
    pbkdf2v2_digest = "SCRAM-SHA-256";
    pbkdf2v2_rounds = 64000;
    pbkdf2v2_saltlen = 32;
};
```

- Digest: SCRAM-SHA-256 (recommended)
- Rounds: 64,000 (matches upstream default, within Cyrus SASL compat range of 10,000–65,536)
- Salt length: 32 bytes (matches upstream default)
- Loaded before any other crypto modules ✅

### 🟢 OK — Login throttling

```conf
loadmodule "misc/login_throttling";
throttle {
    #address_burst = 5;
    #address_replenish = 1;
    #address_account_burst = 2;
    #address_account_replenish = 2;
};
```

Module loaded. Throttle block uses defaults (all values commented, so Atheme uses built-in defaults). This is fine and matches upstream.

### 🟢 OK — Flood protection

```conf
flood_msgs = 7;
flood_time = 10;
```

Matches upstream. 7 messages in 10 seconds triggers flood protection.

### 🟢 OK — Rate limiting

```conf
ratelimit_uses = 5;
ratelimit_period = 60;
```

Matches upstream. 5 rate-limited command uses per 60 seconds.

### 🟢 OK — DNSBL/Proxyscan

```conf
loadmodule "proxyscan/main";
loadmodule "proxyscan/dnsbl";
proxyscan {
    blacklists {
        "dnsbl.dronebl.org";
        "rbl.efnetrbl.org";
        "tor.efnet.org";
        "dnsbl.tornevall.org";   # ➕ Additional (not in upstream)
        "bl.spamcop.net";        # ➕ Additional (not in upstream)
    };
    dnsbl_action = kline;
};
```

More comprehensive DNSBL list than upstream (5 vs 3 providers). `kline` action is the standard response.

### 🟢 OK — Docker entrypoint security

```bash
if [ "$(id -u)" = "0" ]; then
    echo "ERROR: Atheme should not run as root for security reasons"
    exit 1
fi
```

The entrypoint correctly refuses to run as root. The Containerfile switches to the `atheme` user (UID 1000).

### 🟢 OK — Containerfile build security

```dockerfile
./configure \
    --prefix=/usr/local/atheme \
    --enable-contrib \
    --with-modulesdir=/usr/local/atheme/modules \
    --with-libidn \      # ✅ Required for SCRAM-SHA support
    --enable-large-net \  # ✅ Good for scalability
    --disable-linker-defs
```

- `--with-libidn` is required for SCRAM-SHA support (matches the comment in the config template)
- `--enable-contrib` builds contrib modules
- `--enable-large-net` optimizes for larger networks

---

## O. HTTPd / JSON-RPC Configuration

### 🟢 OK — HTTPd properly configured

```conf
httpd {
    host = "0.0.0.0";
    www_root = "/var/www";
    port = ${ATHEME_HTTPD_PORT};  # .env: 8081
};
```

- Listening on all interfaces (`0.0.0.0`) is correct since it's inside a Docker container
- Port templated via env var
- `www_root` is standard

### 🟢 OK — JSON-RPC transport loaded

```conf
loadmodule "transport/jsonrpc";
```

Required for WebPanel and portal integration. The compose file maps port 8081 through the UnrealIRCd container (since Atheme shares its network namespace).

### 💡 SUGGESTION — Consider adding transport/xmlrpc for broader compatibility

```conf
#loadmodule "transport/xmlrpc";
```

XMLRPC is commented out (matching upstream). If only JSON-RPC is needed for the WebPanel/portal, this is fine. JSON-RPC is the more modern choice.

---

## P. Missing Blocks/Settings

### 🔴 CRITICAL — `chanfix{}` block without `chanfix/main` module (see C above)

The `chanfix{}` configuration block with `autofix;` is present but the module isn't loaded.

### 🟡 WARNING — No `include` directive for operator management

Upstream suggests:

```conf
include "etc/sras.conf";
```

All operator definitions are inline in the main config. For a Docker deployment with templated configs, consider either:

- Templating operator blocks via env vars, or
- Using `operserv/soper` exclusively for runtime oper management (module is already loaded)

### 💡 SUGGESTION — Missing `nickserv/multimark` module

Upstream modules directory contains `nickserv/multimark.c` which is not referenced in either config. This module allows operators to add multiple marks to accounts, which is useful for tracking problematic users.

### 💡 SUGGESTION — Missing `chanserv/set` (core SET router)

The upstream modules include `chanserv/set.c` and `chanserv/set_core.c`. While individual `set_*` modules are loaded, the main `chanserv/set` router and `nickserv/set` router may be auto-loaded as dependencies. Verify these are functioning correctly.

### 💡 SUGGESTION — `statserv/pwhashes` module available but not loaded

The upstream modules include `statserv/pwhashes.c` which provides statistics on password hash types in use. Useful for monitoring crypto migration progress.

---

## Summary

| Severity | Count | Key Items |
|----------|-------|-----------|
| 🔴 CRITICAL | 2 | "jilles" operator block; orphaned `chanfix{}` block |
| 🟡 WARNING | 4 | Debug loglevel; missing pbkdf2 v1 compat; duplicate scram ref; single log file |
| 🟢 OK | 35+ | Vast majority of configuration matches or exceeds upstream |
| 💡 SUGGESTION | 8+ | scram_mechanisms, exttarget, enforceprefix, log separation, etc. |

### Priority Fixes

1. **🔴 Remove or replace `operator "jilles"` block** — immediate security concern
2. **🔴 Fix `chanfix` module/block mismatch** — either enable the module or remove the block
3. **🟡 Reduce loglevel for production** — `debug` is too verbose and may log sensitive data
4. **🟡 Clean up duplicate `saslserv/scram` reference** — reduces confusion
5. **🟡 Add `crypto/pbkdf2` for migration safety** — protects against future Atheme version upgrades
6. **🟡 Split log files by category** — improves operational visibility

### What's Done Well

- Comprehensive module selection (more features than upstream defaults)
- Proper environment variable templating throughout
- Strong crypto configuration (PBKDF2v2 with SCRAM-SHA-256)
- Good security modules (login throttling, DNSBL, flood protection)
- Correct protocol selection for UnrealIRCd
- Well-structured Docker setup with non-root execution
- JSON-RPC properly configured for WebPanel/portal integration
- Network-appropriate settings (casemapping, changets, etc.)
