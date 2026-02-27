# Environment Variable Audit — atl.chat Monorepo

> Generated: 2026-02-26 | Scope: Full 12-factor env var cleanup

---

## Comprehensive Variable Table

### 1. CORE PROJECT & ENVIRONMENT

| Variable | `.env.example` | `.env.dev.example` | Compose files | Config templates | Scripts | Code |
|----------|---------------|-------------------|---------------|-----------------|---------|------|
| `ATL_PROJECT_NAME` | ✅ `atl-chat` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `ATL_BASE_DOMAIN` | ✅ `atl.chat` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `ATL_ENVIRONMENT` | ✅ `dev` | ✅ `dev` | bridge.yaml | ❌ | prepare-config.sh | schema.py (`_ENV_OVERRIDE_KEYS`) |
| `PUID` | ✅ `1000` | ❌ | irc.yaml (build args, env), thelounge.yaml (user) | ❌ | ❌ | ❌ |
| `PGID` | ✅ `1000` | ❌ | irc.yaml (build args, env), thelounge.yaml (user) | ❌ | ❌ | ❌ |
| `TZ` | ✅ `UTC` | ❌ | irc.yaml (env) | ❌ | ❌ | ❌ |

### 2. GLOBAL NETWORKING

| Variable | `.env.example` | `.env.dev.example` | Compose files | Config templates | Scripts | Code |
|----------|---------------|-------------------|---------------|-----------------|---------|------|
| `ATL_GATEWAY_IP` | ✅ `100.64.1.0` | ❌ | irc.yaml (env) | unrealircd.conf.template (`webirc mask`) | ❌ | ❌ |
| `ATL_CHAT_IP` | ✅ `100.64.7.0` | ✅ `127.0.0.1` | irc.yaml (ports), xmpp.yaml (indirectly via port bindings using defaults) | ❌ | ❌ | ❌ |
| `IRC_TLS_PORT` | ✅ `6697` | ❌ | irc.yaml (ports) | bridge config.template.yaml | ❌ | ❌ |
| `IRC_SERVER_PORT` | ✅ `6900` | ❌ | irc.yaml (ports) | ❌ | ❌ | ❌ |
| `IRC_RPC_PORT` | ✅ `8600` | ❌ | irc.yaml (ports) | ❌ | ❌ | ❌ |
| `IRC_WEBSOCKET_PORT` | ✅ `8000` | ❌ | irc.yaml (ports) | ❌ | ❌ | ❌ |
| `XMPP_C2S_PORT` | ✅ `5222` | ❌ | xmpp.yaml (ports, as `PROSODY_C2S_PORT` fallback) | ❌ | ❌ | ❌ |
| `XMPP_S2S_PORT` | ✅ `5269` | ❌ | xmpp.yaml (ports, as `PROSODY_S2S_PORT` fallback) | ❌ | ❌ | ❌ |
| `XMPP_HTTP_PORT` | ✅ `5280` | ❌ | xmpp.yaml (ports, as `PROSODY_HTTP_PORT` fallback) | ❌ | ❌ | ❌ |
| `XMPP_HTTPS_PORT` | ✅ `5281` | ❌ | xmpp.yaml (ports, as `PROSODY_HTTPS_PORT` fallback) | ❌ | ❌ | ❌ |
| `TURN_PORT` | ✅ `3478` | ❌ | ❌ | prosody.cfg.lua (`turn_external_port`) | ❌ | ❌ |
| `TURNS_PORT` | ✅ `5349` | ❌ | ❌ | prosody.cfg.lua (`turn_external_tls_port`) | ❌ | ❌ |

### 3. IRC SERVICE (UnrealIRCd & Atheme)

| Variable | `.env.example` | `.env.dev.example` | Compose files | Config templates | Scripts | Code |
|----------|---------------|-------------------|---------------|-----------------|---------|------|
| `UNREALIRCD_VERSION` | ✅ `6.2.0.1` | ❌ | irc.yaml (build arg) | ❌ | ❌ | ❌ |
| `ATHEME_VERSION` | ✅ `master` | ❌ | irc.yaml (build arg) | ❌ | ❌ | ❌ |
| `IRC_DOMAIN` | ✅ `irc.atl.chat` | ✅ `irc.localhost` | irc.yaml (env) | unrealircd.conf.template (many), atheme.conf.template (uplink) | init.sh, prepare-config.sh | ❌ |
| `IRC_ROOT_DOMAIN` | ✅ `atl.chat` | ❌ | cert-manager.yaml (env) | ❌ | cert-manager/run.sh | ❌ |
| `IRC_NETWORK_NAME` | ✅ `"All Things Linux IRC"` | ❌ | ❌ | unrealircd.conf.template (`me`, `set`) | ❌ | thelounge config.js.template |
| `IRC_CLOAK_PREFIX` | ✅ `atl` | ❌ | ❌ | unrealircd.conf.template (`hiddenhost-prefix`) | prepare-config.sh | ❌ |
| `IRC_CLOAK_KEY_1` | ✅ (hash) | ❌ | ❌ | unrealircd.conf.template (`cloak-keys`) | prepare-config.sh | ❌ |
| `IRC_CLOAK_KEY_2` | ✅ (hash) | ❌ | ❌ | unrealircd.conf.template (`cloak-keys`) | prepare-config.sh | ❌ |
| `IRC_CLOAK_KEY_3` | ✅ (hash) | ❌ | ❌ | unrealircd.conf.template (`cloak-keys`) | prepare-config.sh | ❌ |
| `IRC_ADMIN_NAME` | ✅ `"All Things Linux"` | ❌ | ❌ | unrealircd.conf.template (`admin`) | init.sh, prepare-config.sh | ❌ |
| `IRC_ADMIN_EMAIL` | ✅ `admin@allthingslinux.org` | ❌ | ❌ | unrealircd.conf.template (`admin`, `kline-address`, `gline-address`) | init.sh, prepare-config.sh | ❌ |
| `IRC_STAFF_VHOST` | ✅ `allthingslinux.org` | ❌ | ❌ | unrealircd.conf.template (`oper admin vhost`) | ❌ | ❌ |
| `IRC_OPER_PASSWORD` | ✅ (argon2 hash) | ❌ | ❌ | unrealircd.conf.template (`oper admin password`) | prepare-config.sh | ❌ |
| `IRC_DRPASS` | ✅ `change_me_drpass` | ❌ | ❌ | unrealircd.conf.template (`drpass`) | ❌ | ❌ |
| `ATL_WEBIRC_PASSWORD` | ✅ `change_me_webirc_password` | ❌ | ❌ | unrealircd.conf.template (`webirc password`) | ❌ | ❌ |
| `IRC_STS_DURATION` | ✅ `1m` | ❌ | ❌ | unrealircd.conf.template (`sts-policy duration`) | ❌ | ❌ |
| `IRC_STS_PRELOAD` | ✅ `no` | ❌ | ❌ | unrealircd.conf.template (`sts-policy preload`) | ❌ | ❌ |
| `IRC_SSL_CERT_PATH` | ✅ (path) | ✅ (path) | irc.yaml (env) | ❌ | init.sh, prepare-config.sh | ❌ |
| `IRC_SSL_KEY_PATH` | ✅ (path) | ✅ (path) | irc.yaml (env) | ❌ | init.sh, prepare-config.sh | ❌ |
| `IRC_SERVICES_SERVER` | ✅ `services.atl.chat` | ❌ | ❌ | unrealircd.conf.template (`link`, `ulines`, `set services-server`, `sasl-server`) | prepare-config.sh | ❌ |
| `IRC_SERVICES_PASSWORD` | ✅ `change_me_secure_services_pass` | ❌ | ❌ | unrealircd.conf.template (`link password`), atheme.conf.template (`uplink send/receive_password`) | prepare-config.sh | ❌ |
| `ATHEME_SERVER_NAME` | ✅ `services.atl.chat` | ❌ | ❌ | atheme.conf.template (`serverinfo name`) | init.sh, prepare-config.sh | ❌ |
| `ATHEME_SERVER_DESC` | ✅ `"All Things Linux IRC Services"` | ❌ | ❌ | atheme.conf.template (`serverinfo desc`) | ❌ | ❌ |
| `ATHEME_UPLINK_HOST` | ✅ `127.0.0.1` | ❌ | ❌ | atheme.conf.template (`uplink host`) | prepare-config.sh | ❌ |
| `ATHEME_UPLINK_PORT` | ✅ `6901` | ❌ | ❌ | atheme.conf.template (`uplink port`) | prepare-config.sh | ❌ |
| `ATHEME_UPLINK_SSL_PORT` | ✅ `6900` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `ATHEME_NUMERIC` | ✅ `00A` | ❌ | ❌ | atheme.conf.template (`serverinfo numeric`) | ❌ | ❌ |
| `ATHEME_RECONTIME` | ✅ `10` | ❌ | ❌ | atheme.conf.template (`serverinfo recontime`) | ❌ | ❌ |
| `ATHEME_LOG_LEVEL` | ✅ `all` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `ATHEME_HTTPD_PORT` | ✅ `8081` | ❌ | irc.yaml (ports) | atheme.conf.template (`httpd port`) | init.sh, prepare-config.sh | ❌ |
| `ATHEME_NETNAME` | ✅ `atl.chat` | ❌ | ❌ | atheme.conf.template (`serverinfo netname`) | init.sh | ❌ |
| `ATHEME_ADMIN_NAME` | ✅ `"All Things Linux"` | ❌ | ❌ | atheme.conf.template (`serverinfo adminname`) | init.sh | ❌ |
| `ATHEME_ADMIN_EMAIL` | ✅ `admin@allthingslinux.org` | ❌ | ❌ | atheme.conf.template (`serverinfo adminemail`) | init.sh | ❌ |
| `ATHEME_REGISTER_EMAIL` | ✅ `noreply@allthingslinux.org` | ❌ | ❌ | atheme.conf.template (`serverinfo registeremail`) | ❌ | ❌ |
| `ATHEME_HIDEHOST_SUFFIX` | ✅ `users.atl.chat` | ❌ | ❌ | atheme.conf.template (`serverinfo hidehostsuffix`) | ❌ | ❌ |
| `ATHEME_HELP_CHANNEL` | ✅ `#help` | ❌ | ❌ | atheme.conf.template (`general helpchan`) | ❌ | ❌ |
| `ATHEME_HELP_URL` | ✅ `https://discord.gg/linux` | ❌ | ❌ | atheme.conf.template (`general helpurl`) | ❌ | ❌ |
| `ATHEME_NICKSERV_NICK` | ✅ `NickServ` | ❌ | ❌ | atheme.conf.template | ❌ | ❌ |
| `ATHEME_NICKSERV_USER` | ✅ `NickServ` | ❌ | ❌ | atheme.conf.template | ❌ | ❌ |
| `ATHEME_NICKSERV_HOST` | ✅ `services.atl.chat` | ❌ | ❌ | atheme.conf.template | ❌ | ❌ |
| `ATHEME_NICKSERV_REAL` | ✅ `"Nickname Services"` | ❌ | ❌ | atheme.conf.template | ❌ | ❌ |
| `ATHEME_CHANSERV_NICK` | ✅ `ChanServ` | ❌ | ❌ | atheme.conf.template | ❌ | ❌ |
| `ATHEME_CHANSERV_USER` | ✅ `ChanServ` | ❌ | ❌ | atheme.conf.template | ❌ | ❌ |
| `ATHEME_CHANSERV_HOST` | ✅ `services.atl.chat` | ❌ | ❌ | atheme.conf.template | ❌ | ❌ |
| `ATHEME_CHANSERV_REAL` | ✅ `"Channel Services"` | ❌ | ❌ | atheme.conf.template | ❌ | ❌ |
| `ATHEME_OPERSERV_NICK` | ✅ `OperServ` | ❌ | ❌ | atheme.conf.template | ❌ | ❌ |
| `ATHEME_OPERSERV_USER` | ✅ `OperServ` | ❌ | ❌ | atheme.conf.template | ❌ | ❌ |
| `ATHEME_OPERSERV_HOST` | ✅ `services.atl.chat` | ❌ | ❌ | atheme.conf.template | ❌ | ❌ |
| `ATHEME_OPERSERV_REAL` | ✅ `"Operator Services"` | ❌ | ❌ | atheme.conf.template | ❌ | ❌ |
| `ATHEME_MEMOSERV_NICK` | ✅ `MemoServ` | ❌ | ❌ | atheme.conf.template | ❌ | ❌ |
| `ATHEME_MEMOSERV_USER` | ✅ `MemoServ` | ❌ | ❌ | atheme.conf.template | ❌ | ❌ |
| `ATHEME_MEMOSERV_HOST` | ✅ `services.atl.chat` | ❌ | ❌ | atheme.conf.template | ❌ | ❌ |
| `ATHEME_MEMOSERV_REAL` | ✅ `"Memo Services"` | ❌ | ❌ | atheme.conf.template | ❌ | ❌ |
| `ATHEME_SASLSERV_NICK` | ✅ `SaslServ` | ❌ | ❌ | atheme.conf.template | ❌ | ❌ |
| `ATHEME_SASLSERV_USER` | ✅ `SaslServ` | ❌ | ❌ | atheme.conf.template | ❌ | ❌ |
| `ATHEME_SASLSERV_HOST` | ✅ `services.atl.chat` | ❌ | ❌ | atheme.conf.template | ❌ | ❌ |
| `ATHEME_SASLSERV_REAL` | ✅ `"SASL Authentication Agent"` | ❌ | ❌ | atheme.conf.template | ❌ | ❌ |
| `ATHEME_BOTSERV_NICK` | ✅ `BotServ` | ❌ | ❌ | atheme.conf.template | ❌ | ❌ |
| `ATHEME_BOTSERV_USER` | ✅ `BotServ` | ❌ | ❌ | atheme.conf.template | ❌ | ❌ |
| `ATHEME_BOTSERV_HOST` | ✅ `services.atl.chat` | ❌ | ❌ | atheme.conf.template | ❌ | ❌ |
| `ATHEME_BOTSERV_REAL` | ✅ `"Bot Services"` | ❌ | ❌ | atheme.conf.template | ❌ | ❌ |
| `ATHEME_GROUPSERV_NICK` | ✅ `GroupServ` | ❌ | ❌ | atheme.conf.template | ❌ | ❌ |
| `ATHEME_GROUPSERV_USER` | ✅ `GroupServ` | ❌ | ❌ | atheme.conf.template | ❌ | ❌ |
| `ATHEME_GROUPSERV_HOST` | ✅ `services.atl.chat` | ❌ | ❌ | atheme.conf.template | ❌ | ❌ |
| `ATHEME_GROUPSERV_REAL` | ✅ `"Group Management Services"` | ❌ | ❌ | atheme.conf.template | ❌ | ❌ |
| `ATHEME_HOSTSERV_NICK` | ✅ `HostServ` | ❌ | ❌ | atheme.conf.template | ❌ | ❌ |
| `ATHEME_HOSTSERV_USER` | ✅ `HostServ` | ❌ | ❌ | atheme.conf.template | ❌ | ❌ |
| `ATHEME_HOSTSERV_HOST` | ✅ `services.atl.chat` | ❌ | ❌ | atheme.conf.template | ❌ | ❌ |
| `ATHEME_HOSTSERV_REAL` | ✅ `"Host Management Services"` | ❌ | ❌ | atheme.conf.template | ❌ | ❌ |
| `ATHEME_INFOSERV_NICK` | ✅ `InfoServ` | ❌ | ❌ | atheme.conf.template | ❌ | ❌ |
| `ATHEME_INFOSERV_USER` | ✅ `InfoServ` | ❌ | ❌ | atheme.conf.template | ❌ | ❌ |
| `ATHEME_INFOSERV_HOST` | ✅ `services.atl.chat` | ❌ | ❌ | atheme.conf.template | ❌ | ❌ |
| `ATHEME_INFOSERV_REAL` | ✅ `"Information Service"` | ❌ | ❌ | atheme.conf.template | ❌ | ❌ |
| `ATHEME_HELPSERV_NICK` | ✅ `HelpServ` | ❌ | ❌ | atheme.conf.template | ❌ | ❌ |
| `ATHEME_HELPSERV_USER` | ✅ `HelpServ` | ❌ | ❌ | atheme.conf.template | ❌ | ❌ |
| `ATHEME_HELPSERV_HOST` | ✅ `services.atl.chat` | ❌ | ❌ | atheme.conf.template | ❌ | ❌ |
| `ATHEME_HELPSERV_REAL` | ✅ `"Help Services"` | ❌ | ❌ | atheme.conf.template | ❌ | ❌ |
| `ATHEME_STATSERV_NICK` | ✅ `StatServ` | ❌ | ❌ | atheme.conf.template | ❌ | ❌ |
| `ATHEME_STATSERV_USER` | ✅ `StatServ` | ❌ | ❌ | atheme.conf.template | ❌ | ❌ |
| `ATHEME_STATSERV_HOST` | ✅ `services.atl.chat` | ❌ | ❌ | atheme.conf.template | ❌ | ❌ |
| `ATHEME_STATSERV_REAL` | ✅ `"Statistics Services"` | ❌ | ❌ | atheme.conf.template | ❌ | ❌ |
| `ATHEME_CHANFIX_NICK` | ✅ `ChanFix` | ❌ | ❌ | atheme.conf.template (commented out block) | ❌ | ❌ |
| `ATHEME_CHANFIX_USER` | ✅ `ChanFix` | ❌ | ❌ | atheme.conf.template (commented out block) | ❌ | ❌ |
| `ATHEME_CHANFIX_HOST` | ✅ `services.atl.chat` | ❌ | ❌ | atheme.conf.template (commented out block) | ❌ | ❌ |
| `ATHEME_CHANFIX_REAL` | ✅ `"Channel Fixing Service"` | ❌ | ❌ | atheme.conf.template (commented out block) | ❌ | ❌ |
| `ATHEME_GLOBAL_NICK` | ✅ `Global` | ❌ | ❌ | atheme.conf.template | ❌ | ❌ |
| `ATHEME_GLOBAL_USER` | ✅ `Global` | ❌ | ❌ | atheme.conf.template | ❌ | ❌ |
| `ATHEME_GLOBAL_HOST` | ✅ `services.atl.chat` | ❌ | ❌ | atheme.conf.template | ❌ | ❌ |
| `ATHEME_GLOBAL_REAL` | ✅ `"Network Announcements"` | ❌ | ❌ | atheme.conf.template | ❌ | ❌ |
| `ATHEME_ALIS_NICK` | ✅ `ALIS` | ❌ | ❌ | atheme.conf.template | ❌ | ❌ |
| `ATHEME_ALIS_USER` | ✅ `alis` | ❌ | ❌ | atheme.conf.template | ❌ | ❌ |
| `ATHEME_ALIS_HOST` | ✅ `services.atl.chat` | ❌ | ❌ | atheme.conf.template | ❌ | ❌ |
| `ATHEME_ALIS_REAL` | ✅ `"Channel Directory"` | ❌ | ❌ | atheme.conf.template | ❌ | ❌ |
| `ATHEME_PROXYSCAN_NICK` | ✅ `Proxyscan` | ❌ | ❌ | atheme.conf.template | ❌ | ❌ |
| `ATHEME_PROXYSCAN_USER` | ✅ `dnsbl` | ❌ | ❌ | atheme.conf.template | ❌ | ❌ |
| `ATHEME_PROXYSCAN_HOST` | ✅ `services.atl.chat` | ❌ | ❌ | atheme.conf.template | ❌ | ❌ |
| `ATHEME_PROXYSCAN_REAL` | ✅ `"Proxyscan Service"` | ❌ | ❌ | atheme.conf.template | ❌ | ❌ |
| `ATHEME_GAMESERV_NICK` | ✅ `GameServ` | ❌ | ❌ | atheme.conf.template | ❌ | ❌ |
| `ATHEME_GAMESERV_USER` | ✅ `GameServ` | ❌ | ❌ | atheme.conf.template | ❌ | ❌ |
| `ATHEME_GAMESERV_HOST` | ✅ `services.atl.chat` | ❌ | ❌ | atheme.conf.template | ❌ | ❌ |
| `ATHEME_GAMESERV_REAL` | ✅ `"Game Services"` | ❌ | ❌ | atheme.conf.template | ❌ | ❌ |
| `ATHEME_RPGSERV_NICK` | ✅ `RPGServ` | ❌ | ❌ | atheme.conf.template | ❌ | ❌ |
| `ATHEME_RPGSERV_USER` | ✅ `RPGServ` | ❌ | ❌ | atheme.conf.template | ❌ | ❌ |
| `ATHEME_RPGSERV_HOST` | ✅ `services.atl.chat` | ❌ | ❌ | atheme.conf.template | ❌ | ❌ |
| `ATHEME_RPGSERV_REAL` | ✅ `"RPG Finding Services"` | ❌ | ❌ | atheme.conf.template | ❌ | ❌ |

### 4. WEBPANEL & THE LOUNGE

| Variable | `.env.example` | `.env.dev.example` | Compose files | Config templates | Scripts | Code |
|----------|---------------|-------------------|---------------|-----------------|---------|------|
| `WEBPANEL_PORT` | ✅ `8080` | ❌ | irc.yaml (ports) | ❌ | ❌ | ❌ |
| `WEBPANEL_RPC_USER` | ✅ `adminpanel` | ❌ | ❌ | unrealircd.conf.template (`rpc-user`) | ❌ | ❌ |
| `WEBPANEL_RPC_PASSWORD` | ✅ `change_me_webpanel_password` | ❌ | ❌ | unrealircd.conf.template (`rpc-user password`) | ❌ | ❌ |
| `THELOUNGE_PORT` | ✅ `9000` | ✅ `9000` | thelounge.yaml (ports) | ❌ | ❌ | ❌ |
| `THELOUNGE_DOMAIN` | ✅ `webirc.atl.chat` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `THELOUNGE_WEBIRC_PASSWORD` | ✅ `change_me_thelounge_webirc` | ❌ | ❌ | unrealircd.conf.template (`proxy thelounge password`), config.js.template (`webirc`) | prepare-config.sh | ❌ |
| `THELOUNGE_DELETE_UPLOADS_AFTER_MINUTES` | ✅ `1440` | ❌ | ❌ | config.js.template (`deleteUploadsAfter`) | prepare-config.sh | ❌ |

### 5. XMPP SERVICE (Prosody)

| Variable | `.env.example` | `.env.dev.example` | Compose files | Config templates | Scripts | Code |
|----------|---------------|-------------------|---------------|-----------------|---------|------|
| `XMPP_DOMAIN` | ✅ `atl.chat` | ✅ `xmpp.localhost` | xmpp.yaml (env: `PROSODY_DOMAIN=${XMPP_DOMAIN}`, `XMPP_DOMAIN` for nginx) | ❌ (mapped to PROSODY_DOMAIN) | prepare-config.sh | ❌ |
| `PROSODY_ADMIN_EMAIL` | ✅ `admin@allthingslinux.org` | ❌ | ❌ | prosody.cfg.lua (`contact_info`) | ❌ | ❌ |
| `PROSODY_ENV` | ✅ `development` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `PROSODY_DB_DRIVER` | ✅ `PostgreSQL` | ❌ | ❌ | ❌ | docker-entrypoint.sh (validation) | ❌ |
| `PROSODY_DB_HOST` | ✅ `xmpp-postgres-dev` | ❌ | ❌ | ❌ | docker-entrypoint.sh (pg_isready) | ❌ |
| `PROSODY_DB_PORT` | ✅ `5432` | ❌ | ❌ | ❌ | docker-entrypoint.sh | ❌ |
| `PROSODY_DB_NAME` | ✅ `prosody` | ❌ | ❌ | ❌ | docker-entrypoint.sh | ❌ |
| `PROSODY_DB_USER` | ✅ `prosody` | ❌ | ❌ | ❌ | docker-entrypoint.sh | ❌ |
| `PROSODY_DB_PASSWORD` | ✅ `change_me_secure_db_pass` | ❌ | ❌ | ❌ | docker-entrypoint.sh | ❌ |
| `PROSODY_ALLOW_REGISTRATION` | ✅ `false` | ❌ | ❌ | prosody.cfg.lua | ❌ | ❌ |
| `PROSODY_C2S_REQUIRE_ENCRYPTION` | ✅ `true` | ✅ `false` | ❌ | prosody.cfg.lua | ❌ | ❌ |
| `PROSODY_S2S_REQUIRE_ENCRYPTION` | ✅ `true` | ✅ `false` | ❌ | prosody.cfg.lua | ❌ | ❌ |
| `PROSODY_S2S_SECURE_AUTH` | ✅ `true` | ✅ `false` | ❌ | prosody.cfg.lua | ❌ | ❌ |
| `PROSODY_MAX_CONNECTIONS_PER_IP` | ✅ `10` | ❌ | ❌ | prosody.cfg.lua | ❌ | ❌ |
| `PROSODY_REGISTRATION_THROTTLE_MAX` | ✅ `10` | ❌ | ❌ | prosody.cfg.lua | ❌ | ❌ |
| `PROSODY_REGISTRATION_THROTTLE_PERIOD` | ✅ `60` | ❌ | ❌ | prosody.cfg.lua | ❌ | ❌ |
| `PROSODY_BLOCK_REGISTRATIONS_REQUIRE` | ✅ `^[a-zA-Z0-9_.-]+$` | ❌ | ❌ | prosody.cfg.lua | ❌ | ❌ |
| `PROSODY_TLS_CHANNEL_BINDING` | ✅ `false` | ❌ | ❌ | prosody.cfg.lua | ❌ | ❌ |
| `PROSODY_ALLOW_UNENCRYPTED_PLAIN_AUTH` | ✅ `false` | ✅ `true` | ❌ | prosody.cfg.lua | ❌ | ❌ |
| `PROSODY_HTTP_HOST` | ✅ `localhost` | ❌ | ❌ | prosody.cfg.lua | ❌ | ❌ |
| `PROSODY_HTTP_SCHEME` | ✅ `http` | ❌ | ❌ | prosody.cfg.lua | ❌ | ❌ |
| `PROSODY_SSL_KEY` | ✅ (path) | ✅ (path) | xmpp.yaml (env) | prosody.cfg.lua (multiple) | ❌ | ❌ |
| `PROSODY_SSL_CERT` | ✅ (path) | ✅ (path) | xmpp.yaml (env) | prosody.cfg.lua (multiple) | ❌ | ❌ |
| `PROSODY_LOG_LEVEL` | ✅ `info` | ❌ | ❌ | prosody.cfg.lua | ❌ | ❌ |
| `PROSODY_STATISTICS` | ✅ `internal` | ❌ | ❌ | prosody.cfg.lua | ❌ | ❌ |
| `PROSODY_STATISTICS_INTERVAL` | ✅ `manual` | ❌ | ❌ | prosody.cfg.lua | ❌ | ❌ |
| `PROSODY_OPENMETRICS_IP` | ✅ `127.0.0.1` | ❌ | ❌ | prosody.cfg.lua | ❌ | ❌ |
| `PROSODY_OPENMETRICS_CIDR` | ✅ `127.0.0.1/32` | ❌ | ❌ | prosody.cfg.lua | ❌ | ❌ |
| `PROSODY_ARCHIVE_EXPIRES_AFTER` | ✅ `30d` | ❌ | ❌ | prosody.cfg.lua | ❌ | ❌ |
| `PROSODY_ARCHIVE_POLICY` | ✅ `true` | ❌ | ❌ | prosody.cfg.lua | ❌ | ❌ |
| `PROSODY_ARCHIVE_COMPRESSION` | ✅ `true` | ❌ | ❌ | prosody.cfg.lua | ❌ | ❌ |
| `PROSODY_ARCHIVE_STORE` | ✅ `archive` | ❌ | ❌ | prosody.cfg.lua | ❌ | ❌ |
| `PROSODY_ARCHIVE_MAX_QUERY_RESULTS` | ✅ `250` | ❌ | ❌ | prosody.cfg.lua | ❌ | ❌ |
| `PROSODY_MAM_SMART_ENABLE` | ✅ `true` | ❌ | ❌ | prosody.cfg.lua | ❌ | ❌ |
| `PROSODY_MUC_NOTIFICATIONS` | ✅ `true` | ❌ | ❌ | prosody.cfg.lua | ❌ | ❌ |
| `PROSODY_MUC_OFFLINE_DELIVERY` | ✅ `true` | ❌ | ❌ | prosody.cfg.lua | ❌ | ❌ |
| `PROSODY_RESTRICT_ROOM_CREATION` | ✅ `false` | ❌ | ❌ | prosody.cfg.lua | ❌ | ❌ |
| `PROSODY_MUC_DEFAULT_PUBLIC` | ✅ `true` | ❌ | ❌ | prosody.cfg.lua | ❌ | ❌ |
| `PROSODY_MUC_DEFAULT_PERSISTENT` | ✅ `true` | ❌ | ❌ | prosody.cfg.lua | ❌ | ❌ |
| `PROSODY_MUC_DEFAULT_PUBLIC_JIDS` | ✅ `true` | ❌ | ❌ | prosody.cfg.lua | ❌ | ❌ |
| `PROSODY_MUC_LOCKING` | ✅ `false` | ❌ | ❌ | prosody.cfg.lua | ❌ | ❌ |
| `PROSODY_MUC_LOG_BY_DEFAULT` | ✅ `true` | ❌ | ❌ | prosody.cfg.lua | ❌ | ❌ |
| `PROSODY_MUC_LOG_EXPIRES_AFTER` | ✅ `1y` | ❌ | ❌ | prosody.cfg.lua | ❌ | ❌ |
| `PROSODY_MUC_LOG_PRESENCES` | ✅ `false` | ❌ | ❌ | prosody.cfg.lua | ❌ | ❌ |
| `PROSODY_MUC_LOG_ALL_ROOMS` | ✅ `false` | ❌ | ❌ | prosody.cfg.lua | ❌ | ❌ |
| `PROSODY_MUC_LOG_CLEANUP_INTERVAL` | ✅ `86400` | ❌ | ❌ | prosody.cfg.lua | ❌ | ❌ |
| `PROSODY_MUC_MAX_ARCHIVE_QUERY_RESULTS` | ✅ `100` | ❌ | ❌ | prosody.cfg.lua | ❌ | ❌ |
| `PROSODY_MUC_LOG_STORE` | ✅ `muc_log` | ❌ | ❌ | prosody.cfg.lua | ❌ | ❌ |
| `PROSODY_MUC_LOG_COMPRESSION` | ✅ `true` | ❌ | ❌ | prosody.cfg.lua | ❌ | ❌ |
| `PROSODY_MUC_MAM_SMART_ENABLE` | ✅ `false` | ❌ | ❌ | prosody.cfg.lua | ❌ | ❌ |
| `PROSODY_C2S_RATE` | ✅ `10kb/s` | ❌ | ❌ | prosody.cfg.lua | ❌ | ❌ |
| `PROSODY_C2S_BURST` | ✅ `25kb` | ❌ | ❌ | prosody.cfg.lua | ❌ | ❌ |
| `PROSODY_C2S_STANZA_SIZE` | ✅ `262144` | ❌ | ❌ | prosody.cfg.lua | ❌ | ❌ |
| `PROSODY_S2S_RATE` | ✅ `30kb/s` | ❌ | ❌ | prosody.cfg.lua | ❌ | ❌ |
| `PROSODY_S2S_BURST` | ✅ `100kb` | ❌ | ❌ | prosody.cfg.lua | ❌ | ❌ |
| `PROSODY_S2S_STANZA_SIZE` | ✅ `524288` | ❌ | ❌ | prosody.cfg.lua | ❌ | ❌ |
| `PROSODY_HTTP_UPLOAD_RATE` | ✅ `2mb/s` | ❌ | ❌ | prosody.cfg.lua | ❌ | ❌ |
| `PROSODY_HTTP_UPLOAD_BURST` | ✅ `10mb` | ❌ | ❌ | prosody.cfg.lua | ❌ | ❌ |
| `PROSODY_PUSH_IMPORTANT_BODY` | ✅ `"New Message!"` | ❌ | ❌ | prosody.cfg.lua | ❌ | ❌ |
| `PROSODY_PUSH_MAX_ERRORS` | ✅ `16` | ❌ | ❌ | prosody.cfg.lua | ❌ | ❌ |
| `PROSODY_PUSH_MAX_DEVICES` | ✅ `5` | ❌ | ❌ | prosody.cfg.lua | ❌ | ❌ |
| `PROSODY_PUSH_MAX_HIBERNATION_TIMEOUT` | ✅ `259200` | ❌ | ❌ | prosody.cfg.lua | ❌ | ❌ |
| `PROSODY_PUSH_NOTIFICATION_WITH_BODY` | ✅ `false` | ❌ | ❌ | prosody.cfg.lua | ❌ | ❌ |
| `PROSODY_PUSH_NOTIFICATION_WITH_SENDER` | ✅ `false` | ❌ | ❌ | prosody.cfg.lua | ❌ | ❌ |
| `PROSODY_ACCOUNT_INACTIVE_PERIOD` | ✅ `31536000` | ❌ | ❌ | prosody.cfg.lua | ❌ | ❌ |
| `PROSODY_ACCOUNT_GRACE_PERIOD` | ✅ `2592000` | ❌ | ❌ | prosody.cfg.lua | ❌ | ❌ |
| `PROSODY_ACCOUNT_DELETION_CONFIRMATION` | ✅ `true` | ❌ | ❌ | ❌ (commented out in lua) | ❌ | ❌ |
| `PROSODY_SERVER_NAME` | ✅ `localhost` | ❌ | ❌ | prosody.cfg.lua | ❌ | ❌ |
| `PROSODY_SERVER_WEBSITE` | ✅ `http://localhost` | ❌ | ❌ | prosody.cfg.lua | ❌ | ❌ |
| `PROSODY_SERVER_DESCRIPTION` | ✅ `"XMPP Service"` | ❌ | ❌ | prosody.cfg.lua | ❌ | ❌ |
| `LUA_GC_STEP_SIZE` | ✅ `13` | ❌ | ❌ | prosody.cfg.lua | ❌ | ❌ |
| `LUA_GC_PAUSE` | ✅ `110` | ❌ | ❌ | prosody.cfg.lua | ❌ | ❌ |
| `LUA_GC_SPEED` | ✅ `200` | ❌ | ❌ | prosody.cfg.lua | ❌ | ❌ |
| `LUA_GC_THRESHOLD` | ✅ `120` | ❌ | ❌ | prosody.cfg.lua | ❌ | ❌ |
| `PROSODY_UPLOAD_EXTERNAL_URL` | ✅ `http://localhost:5280/upload/` | ✅ `https://xmpp.localhost:5281/` | xmpp.yaml (env) | prosody.cfg.lua | ❌ | ❌ |
| `PROSODY_PROXY_ADDRESS` | ✅ `localhost` | ✅ `xmpp.localhost` | xmpp.yaml (env) | prosody.cfg.lua | ❌ | ❌ |
| `PROSODY_FEED_URL` | ✅ `https://allthingslinux.org/feed` | ❌ | ❌ | prosody.cfg.lua | ❌ | ❌ |

### 6. DATABASE (PostgreSQL)

| Variable | `.env.example` | `.env.dev.example` | Compose files | Config templates | Scripts | Code |
|----------|---------------|-------------------|---------------|-----------------|---------|------|
| `POSTGRES_USER` | ✅ `prosody` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `POSTGRES_DB` | ✅ `prosody` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `POSTGRES_PASSWORD` | ✅ `change_me_secure_db_pass` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `POSTGRES_SHARED_BUFFERS` | ✅ `32MB` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `POSTGRES_EFFECTIVE_CACHE_SIZE` | ✅ `128MB` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `POSTGRES_WORK_MEM` | ✅ `1MB` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `POSTGRES_MAINTENANCE_WORK_MEM` | ✅ `16MB` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `POSTGRES_CHECKPOINT_COMPLETION_TARGET` | ✅ `0.9` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `POSTGRES_WAL_BUFFERS` | ✅ `4MB` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `POSTGRES_DEFAULT_STATISTICS_TARGET` | ✅ `50` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `POSTGRES_RANDOM_PAGE_COST` | ✅ `1.1` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `POSTGRES_EFFECTIVE_IO_CONCURRENCY` | ✅ `100` | ❌ | ❌ | ❌ | ❌ | ❌ |

### 7. ADMINER

| Variable | `.env.example` | `.env.dev.example` | Compose files | Config templates | Scripts | Code |
|----------|---------------|-------------------|---------------|-----------------|---------|------|
| `ADMINER_PORT` | ✅ `8080` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `ADMINER_AUTO_LOGIN` | ✅ `false` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `ADMINER_DEFAULT_DRIVER` | ✅ `pgsql` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `ADMINER_DEFAULT_SERVER` | ✅ `xmpp-postgres` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `ADMINER_DEFAULT_DB` | ✅ `prosody` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `ADMINER_DEFAULT_USERNAME` | ✅ `prosody` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `ADMINER_DEFAULT_PASSWORD` | ✅ `change_me_secure_db_pass` | ❌ | ❌ | ❌ | ❌ | ❌ |

### 8. NGINX REVERSE PROXY

| Variable | `.env.example` | `.env.dev.example` | Compose files | Config templates | Scripts | Code |
|----------|---------------|-------------------|---------------|-----------------|---------|------|
| `NGINX_HTTP_PORT` | ✅ `80` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `NGINX_HTTPS_PORT` | ✅ `443` | ❌ | ❌ | ❌ | ❌ | ❌ |

### 9. EXTERNAL INTEGRATIONS

| Variable | `.env.example` | `.env.dev.example` | Compose files | Config templates | Scripts | Code |
|----------|---------------|-------------------|---------------|-----------------|---------|------|
| `ATL_SENTRY_DSN` | ✅ (empty) | ❌ | ❌ | ❌ | ❌ | ❌ |
| `ATL_INTERNAL_SECRET_IRC` | ✅ (empty) | ❌ | ❌ | ❌ | ❌ | ❌ |
| `ATL_INTERNAL_SECRET_XMPP` | ✅ (empty) | ❌ | ❌ | ❌ | ❌ | ❌ |
| `LETSENCRYPT_EMAIL` | ✅ `admin@allthingslinux.org` | ❌ | cert-manager.yaml (env) | ❌ | cert-manager/run.sh | ❌ |

### 10. BRIDGE SERVICE

| Variable | `.env.example` | `.env.dev.example` | Compose files | Config templates | Scripts | Code |
|----------|---------------|-------------------|---------------|-----------------|---------|------|
| `BRIDGE_DISCORD_TOKEN` | ✅ `change_me_discord_bot_token` | ❌ | bridge.yaml (env) | ❌ | ❌ | `__main__.py`, `discord/adapter.py` |
| `BRIDGE_DISCORD_CHANNEL_ID` | ✅ `REPLACE_WITH_DISCORD_CHANNEL_ID` | ❌ | ❌ | config.template.yaml | prepare-config.sh | ❌ |
| `BRIDGE_PORTAL_BASE_URL` | ✅ `https://portal.atl.tools` | ✅ (empty) | bridge.yaml (env) | ❌ | ❌ | `__main__.py` |
| `BRIDGE_PORTAL_TOKEN` | ✅ `change_me_bridge_portal_token` | ❌ | bridge.yaml (env) | ❌ | ❌ | `__main__.py` |
| `BRIDGE_XMPP_COMPONENT_JID` | ✅ `bridge.atl.chat` | ✅ `bridge.xmpp.localhost` | bridge.yaml (env) | ❌ | prepare-config.sh | `xmpp/adapter.py` |
| `BRIDGE_XMPP_COMPONENT_SECRET` | ✅ `change_me_xmpp_component_secret` | ❌ | bridge.yaml (env) | prosody.cfg.lua | ❌ | `xmpp/adapter.py` |
| `BRIDGE_XMPP_COMPONENT_SERVER` | ✅ `atl-xmpp-server` | ✅ `atl-xmpp-server` | bridge.yaml (env) | ❌ | ❌ | `xmpp/adapter.py` |
| `BRIDGE_XMPP_COMPONENT_PORT` | ✅ `5347` | ✅ `5347` | bridge.yaml (env) | ❌ | ❌ | `xmpp/adapter.py` |
| `BRIDGE_IRC_NICK` | ✅ `bridge` | ❌ | bridge.yaml (env) | ❌ | ❌ | `irc/adapter.py` |
| `BRIDGE_IRC_OPER_PASSWORD` | ✅ `change_me_bridge_oper` | ❌ | bridge.yaml (env) | unrealircd.conf.template (`oper bridge`) | prepare-config.sh | `irc/client.py` |
| `IRC_BRIDGE_SERVER` | ✅ `atl-irc-server` | ✅ `atl-irc-server` | ❌ | config.template.yaml | prepare-config.sh | ❌ |
| `BRIDGE_IRC_TLS_VERIFY` | ❌ | ✅ `false` | bridge.yaml (env) | ❌ | prepare-config.sh | schema.py (`_ENV_OVERRIDE_KEYS`) |
| `BRIDGE_RELAYMSG_CLEAN_NICKS` | ❌ | ✅ `true` | bridge.yaml (env) | ❌ | ❌ | schema.py (`_ENV_OVERRIDE_KEYS`) |
| `LOG_LEVEL` | ❌ (commented) | ❌ (commented) | bridge.yaml (env) | ❌ | ❌ | `__main__.py` |

### 11. PORTAL INTEGRATION

| Variable | `.env.example` | `.env.dev.example` | Compose files | Config templates | Scripts | Code |
|----------|---------------|-------------------|---------------|-----------------|---------|------|
| `IRC_ATHEME_JSONRPC_URL` | ✅ `http://atl-irc-server:8081/jsonrpc` | ✅ (same) | ❌ | ❌ | ❌ | ❌ |
| `IRC_UNREAL_JSONRPC_URL` | ✅ `https://irc.atl.chat:8600/api` | ✅ `https://irc.localhost:8600/api` | ❌ | ❌ | ❌ | ❌ |
| `IRC_UNREAL_RPC_USER` | ✅ `${WEBPANEL_RPC_USER}` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `IRC_UNREAL_RPC_PASSWORD` | ✅ `${WEBPANEL_RPC_PASSWORD}` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `PROSODY_REST_URL` | ✅ `http://atl-xmpp-server:5280` | ✅ (same) | ❌ | ❌ | ❌ | ❌ |
| `PROSODY_REST_USERNAME` | ✅ `admin@atl.chat` | ✅ `admin@xmpp.localhost` | ❌ | ❌ | ❌ | ❌ |
| `PROSODY_REST_PASSWORD` | ✅ `change_me_prosody_rest_password` | ✅ (same) | ❌ | ❌ | ❌ | ❌ |
| `IRC_SERVER` | ✅ `irc.atl.chat` | ✅ `irc.localhost` | ❌ | ❌ | ❌ | ❌ |
| `IRC_PORT` | ✅ `6697` | ✅ `6697` | ❌ | ❌ | ❌ | ❌ |

### 12. WEB FRONTEND (Next.js)

| Variable | `.env.example` (root) | `.env.dev.example` | `apps/web/.env.example` | Compose files | Code |
|----------|----------------------|-------------------|------------------------|---------------|------|
| `NEXT_PUBLIC_IRC_WS_URL` | ✅ `wss://irc.atl.chat/ws` | ✅ `wss://irc.localhost/ws` | ✅ `wss://irc.atl.chat/ws` | ❌ | justfile (hardcoded override) |
| `NEXT_PUBLIC_XMPP_BOSH_URL` | ✅ `https://xmpp.atl.chat/http-bind` | ✅ `https://xmpp.localhost/http-bind` | ✅ `https://xmpp.atl.chat/http-bind` | ❌ | justfile (hardcoded override) |
| `NEXT_PUBLIC_ATL_BASE_DOMAIN` | ❌ | ❌ | ✅ `atl.chat` | ❌ | ❌ |
| `NEXT_PUBLIC_ATL_ENVIRONMENT` | ❌ | ❌ | ✅ `development` | ❌ | ❌ |
| `NEXT_PUBLIC_SENTRY_DSN` | ❌ | ❌ | ✅ (empty) | ❌ | ❌ |

---

## Categorized Findings

### Category A: ORPHANED — Defined in `.env.example` but never consumed

| Variable | Notes |
|----------|-------|
| `ATL_PROJECT_NAME` | Defined as `atl-chat`. Not referenced in any compose, config template, script, or code. Docker Compose `name: atl-chat` is hardcoded in compose.yaml. |
| `ATL_BASE_DOMAIN` | Defined as `atl.chat`. Not referenced anywhere. Individual domains (`IRC_DOMAIN`, `XMPP_DOMAIN`) are used instead. |
| `PROSODY_ENV` | Defined as `development`. Not referenced in any compose file, Lua config, script, or code. `ATL_ENVIRONMENT` is the actual env discriminator. |
| `ATHEME_UPLINK_SSL_PORT` | Defined as `6900`. Never consumed in any template or compose file. The atheme.conf.template uses `ATHEME_UPLINK_PORT` (6901, plaintext). |
| `ATHEME_LOG_LEVEL` | Defined as `all`. Not referenced in atheme.conf.template (log level is hardcoded: `logfile "logs/atheme.log" { debug; };`). |
| `POSTGRES_USER` | Defined as `prosody`. No PostgreSQL service exists in compose (removed; dev uses SQLite). Not consumed by any running service. |
| `POSTGRES_DB` | Same as above. |
| `POSTGRES_PASSWORD` | Same as above. |
| `POSTGRES_SHARED_BUFFERS` | No PostgreSQL compose service exists. |
| `POSTGRES_EFFECTIVE_CACHE_SIZE` | No PostgreSQL compose service exists. |
| `POSTGRES_WORK_MEM` | No PostgreSQL compose service exists. |
| `POSTGRES_MAINTENANCE_WORK_MEM` | No PostgreSQL compose service exists. |
| `POSTGRES_CHECKPOINT_COMPLETION_TARGET` | No PostgreSQL compose service exists. |
| `POSTGRES_WAL_BUFFERS` | No PostgreSQL compose service exists. |
| `POSTGRES_DEFAULT_STATISTICS_TARGET` | No PostgreSQL compose service exists. |
| `POSTGRES_RANDOM_PAGE_COST` | No PostgreSQL compose service exists. |
| `POSTGRES_EFFECTIVE_IO_CONCURRENCY` | No PostgreSQL compose service exists. |
| `ADMINER_PORT` | No Adminer service in compose files. |
| `ADMINER_AUTO_LOGIN` | No Adminer service in compose files. |
| `ADMINER_DEFAULT_DRIVER` | No Adminer service in compose files. |
| `ADMINER_DEFAULT_SERVER` | No Adminer service in compose files. |
| `ADMINER_DEFAULT_DB` | No Adminer service in compose files. |
| `ADMINER_DEFAULT_USERNAME` | No Adminer service in compose files. |
| `ADMINER_DEFAULT_PASSWORD` | No Adminer service in compose files. |
| `NGINX_HTTP_PORT` | No nginx reverse proxy service in compose files (only xmpp-nginx exists, which uses `PROSODY_HTTPS_PORT`). |
| `NGINX_HTTPS_PORT` | Same as above. |
| `ATL_SENTRY_DSN` | Defined (empty) but not referenced in any compose, config, script, or code in this monorepo. |
| `ATL_INTERNAL_SECRET_IRC` | Defined (empty) but not referenced anywhere. Intended for future Portal integration. |
| `ATL_INTERNAL_SECRET_XMPP` | Defined (empty) but not referenced anywhere. Intended for future Portal integration. |
| `THELOUNGE_DOMAIN` | Defined as `webirc.atl.chat`. Not referenced in any compose file, config template, script, or code. |
| `ATHEME_CHANFIX_NICK/USER/HOST/REAL` | Defined in `.env.example` but only consumed in a **commented-out** block in atheme.conf.template. The ChanFix module is disabled. |
| `IRC_ATHEME_JSONRPC_URL` | Defined in `.env.example` and `.env.dev.example`. Not consumed by any service in this monorepo — intended for an external Portal service. |
| `IRC_UNREAL_JSONRPC_URL` | Same — intended for external Portal. |
| `IRC_UNREAL_RPC_USER` | Same — intended for external Portal. Uses `${WEBPANEL_RPC_USER}` interpolation in `.env.example` which is unusual. |
| `IRC_UNREAL_RPC_PASSWORD` | Same — intended for external Portal. |
| `PROSODY_REST_URL` | Same — intended for external Portal. |
| `PROSODY_REST_USERNAME` | Same — intended for external Portal. |
| `PROSODY_REST_PASSWORD` | Same — intended for external Portal. |
| `IRC_SERVER` | Same — intended for external Portal. |
| `IRC_PORT` | Same — intended for external Portal. |
| `PROSODY_ACCOUNT_DELETION_CONFIRMATION` | Defined as `true`. The Lua code block that consumes it is **commented out** in prosody.cfg.lua. |

**Total: 37 orphaned variables** (though ~11 Portal vars are intentionally pre-defined for external consumers)

### Category B: UNDEFINED — Consumed in config/compose but NOT defined in `.env.example`

| Variable | Where consumed | Notes |
|----------|---------------|-------|
| `PROSODY_DOMAIN` | prosody.cfg.lua, docker-entrypoint.sh, config.template.yaml, init.sh, prepare-config.sh | **Critical.** Not in `.env.example`. Derived in prepare-config.sh as `${PROSODY_DOMAIN:-${XMPP_DOMAIN:-xmpp.localhost}}`. Set in `.env.dev.example` as `xmpp.localhost`. Compose sets it from `XMPP_DOMAIN`. This is intentional (derived var) but confusing. |
| `PROSODY_HTTPS_VIA_PROXY` | xmpp.yaml (env), prosody.cfg.lua | Not in `.env.example`. Compose sets default `false`. Controls whether nginx handles HTTPS. |
| `PROSODY_HTTP_EXTERNAL_URL` | xmpp.yaml (env), prosody.cfg.lua | Not in `.env.example`. Set in `.env.dev.example`. Important for Converse.js dev access. |
| `PROSODY_C2S_DIRECT_TLS_PORT` | xmpp.yaml (ports, with default `5223`) | Not in `.env.example`. Port 5223 (direct TLS). |
| `PROSODY_S2S_DIRECT_TLS_PORT` | xmpp.yaml (ports, with default `5270`) | Not in `.env.example`. Port 5270 (direct s2s TLS). |
| `PROSODY_PROXY65_PORT` | xmpp.yaml (ports, with default `5000`) | Not in `.env.example`. SOCKS5 proxy port. |
| `PROSODY_C2S_PORT` | xmpp.yaml (ports, with default `5222`) | Not in `.env.example` as `PROSODY_C2S_PORT`. `XMPP_C2S_PORT` exists but compose uses `PROSODY_C2S_PORT`. **Name mismatch.** |
| `PROSODY_S2S_PORT` | xmpp.yaml (ports, with default `5269`) | Same issue. `XMPP_S2S_PORT` defined, compose uses `PROSODY_S2S_PORT`. |
| `PROSODY_HTTP_PORT` | xmpp.yaml (ports, with default `5280`) | Same. `XMPP_HTTP_PORT` defined, compose uses `PROSODY_HTTP_PORT`. |
| `PROSODY_HTTPS_PORT` | xmpp.yaml (ports, with default `5281`) | Same. `XMPP_HTTPS_PORT` defined, compose uses `PROSODY_HTTPS_PORT`. |
| `PROSODY_STORAGE` | docker-entrypoint.sh | Not in `.env.example`. Set in `.env.dev.example` as `sqlite`. Controls Prosody storage backend. |
| `LOG_MAX_SIZE` | xmpp.yaml (logging) | Not in `.env.example`. Defaults to `50m`. |
| `LOG_MAX_FILES` | xmpp.yaml (logging) | Not in `.env.example`. Defaults to `5`. |
| `DOZZLE_PORT` | compose.yaml | Not in `.env.example`. Defaults to `8082`. Dev-only (Dozzle log viewer). |
| `CLOUDFLARE_DNS_API_TOKEN` | cert-manager.yaml (env), cert-manager/run.sh | Not in `.env.example`. Required for Let's Encrypt cert issuance. |
| `SSL_DOMAIN` | cert-manager.yaml (env), cert-manager/run.sh | Not in `.env.example`. Optional override for cert domain. |
| `IRC_LOG_PATH` | unrealircd.conf.template (log destination), prepare-config.sh | Not in `.env.example`. Defaults to `/home/unrealircd/unrealircd/logs` in prepare-config.sh. |
| `IRC_TLS_VERIFY` | config.template.yaml (`irc_tls_verify`) | Not in `.env.example`. Derived in prepare-config.sh from `BRIDGE_IRC_TLS_VERIFY` / `ATL_ENVIRONMENT`. |
| `IRC_LOUNGE_REJECT_UNAUTHORIZED` | config.js.template (`rejectUnauthorized`) | Not in `.env.example`. Derived in prepare-config.sh from `ATL_ENVIRONMENT`. |
| `TURN_SECRET` | prosody.cfg.lua (`turn_external_secret`) | Not in `.env.example`. Defaults to `devsecret`. Required for production TURN server auth. |
| `TURN_EXTERNAL_HOST` | prosody.cfg.lua (`turn_external_host`) | Not in `.env.example`. Defaults to `turn.atl.network`. |
| `PROSODY_ADMIN_JID` | prosody.cfg.lua, docker-entrypoint.sh | Not in `.env.example`. Derived from `PROSODY_DOMAIN` in entrypoint. |
| `PROSODY_SUPPORT_CONTACT` | prosody.cfg.lua | Not in `.env.example`. Defaults to `support@{domain}`. |
| `PROSODY_SUPPORT_CONTACT_NICK` | prosody.cfg.lua | Not in `.env.example`. Defaults to `"Support"`. |
| `XMPP_AVATAR_BASE_URL` | bridge.yaml (env) | Not in `.env.example`. Set in `.env.dev.example`. Bridge needs internal URL to HEAD-check avatars. |
| `XMPP_UPLOAD_FETCH_URL` | bridge.yaml (env) | Not in `.env.example`. Set in `.env.dev.example`. Bridge rewrites XMPP upload URLs. |
| `BRIDGE_IRC_REDACT_ENABLED` | schema.py (`_ENV_OVERRIDE_KEYS`) | Not in `.env.example`. Env override for IRC REDACT feature toggle. |
| `BRIDGE_DEV_IRC_PUPPETS` | `__main__.py` | Not in `.env.example`. Mentioned (commented) in `.env.dev.example`. Enables IRC puppets without Portal. |
| `BRIDGE_DEV_IRC_NICK_MAP` | `identity/dev.py` | Not in `.env.example`. Mentioned (commented) in `.env.dev.example`. Maps Discord IDs to IRC nicks for dev. |
| `BRIDGE_PORTAL_URL` | `__main__.py` (legacy alias) | Not in `.env.example`. Legacy alias for `BRIDGE_PORTAL_BASE_URL`. |
| `BRIDGE_PORTAL_API_TOKEN` | `__main__.py` (legacy alias) | Not in `.env.example`. Legacy alias for `BRIDGE_PORTAL_TOKEN`. |
| `XMPP_COMPONENT_SECRET` | prosody.cfg.lua (fallback) | Not in `.env.example`. Legacy alias for `BRIDGE_XMPP_COMPONENT_SECRET`. |
| `IRC_PUPPET_IDLE_TIMEOUT_HOURS` | `irc/adapter.py` | Not in `.env.example`. Env override; defaults to `24`. Config YAML property `irc_puppet_idle_timeout_hours` is the primary. |
| `CERT_DIR` | xmpp-nginx docker-entrypoint.sh, prosody-https.conf.template | Not in `.env.example`. Hardcoded as env in xmpp.yaml nginx: `CERT_DIR=/etc/nginx/certs`. |

### Category C: INCONSISTENT — Same variable referenced differently

| Issue | Details |
|-------|---------|
| **XMPP port naming mismatch** | `.env.example` defines `XMPP_C2S_PORT`, `XMPP_S2S_PORT`, `XMPP_HTTP_PORT`, `XMPP_HTTPS_PORT`. But `xmpp.yaml` uses `PROSODY_C2S_PORT`, `PROSODY_S2S_PORT`, `PROSODY_HTTP_PORT`, `PROSODY_HTTPS_PORT` with fallback defaults. The `XMPP_*_PORT` vars are defined but **never consumed** by compose — the `PROSODY_*_PORT` names are what actually work. |
| **XMPP_DOMAIN vs PROSODY_DOMAIN** | `.env.example` defines `XMPP_DOMAIN`. Compose passes it as `PROSODY_DOMAIN=${XMPP_DOMAIN}`. Scripts derive `PROSODY_DOMAIN` from `XMPP_DOMAIN`. Prosody code only reads `PROSODY_DOMAIN`. Two names for one value; `.env.dev.example` defines **both** separately (`XMPP_DOMAIN=xmpp.localhost` and `PROSODY_DOMAIN=xmpp.localhost`). |
| **BRIDGE_PORTAL_URL vs BRIDGE_PORTAL_BASE_URL** | Code checks both `BRIDGE_PORTAL_BASE_URL` and `BRIDGE_PORTAL_URL` (legacy). Only `BRIDGE_PORTAL_BASE_URL` is in `.env.example`. |
| **BRIDGE_PORTAL_TOKEN vs BRIDGE_PORTAL_API_TOKEN** | Code checks both `BRIDGE_PORTAL_TOKEN` and `BRIDGE_PORTAL_API_TOKEN` (legacy). Only `BRIDGE_PORTAL_TOKEN` is in `.env.example`. |
| **BRIDGE_XMPP_COMPONENT_SECRET vs XMPP_COMPONENT_SECRET** | prosody.cfg.lua checks both `BRIDGE_XMPP_COMPONENT_SECRET` and `XMPP_COMPONENT_SECRET` (legacy fallback). Only the `BRIDGE_` prefixed version is in `.env.example`. |
| **IRC_UNREAL_RPC_USER/PASSWORD uses var interpolation in .env.example** | `IRC_UNREAL_RPC_USER=${WEBPANEL_RPC_USER}` — this relies on shell expansion when `.env` is sourced, but Docker Compose does NOT expand `${VAR}` references inside `.env` files. This means these vars will literally be set to the string `${WEBPANEL_RPC_USER}` when loaded by Compose. |

### Category D: HARDCODED — Values that should be env vars but are hardcoded

| Location | Hardcoded value | Should be |
|----------|----------------|-----------|
| `unrealircd.conf.template` | `me { sid "001"; }` | Consider `IRC_SERVER_SID` env var for multi-server setups |
| `unrealircd.conf.template` | `help-channel "#support"` | Could use `IRC_HELP_CHANNEL` |
| `unrealircd.conf.template` | `oper-auto-join "#mod-chat"` | Could use `IRC_OPER_CHANNEL` |
| `unrealircd.conf.template` | `maxchannelsperuser 10` | Could use `IRC_MAX_CHANNELS_PER_USER` |
| `unrealircd.conf.template` | `maxperip 5` (allow block) | Could use `IRC_MAX_PER_IP` |
| `config.js.template` | `host: "atl-irc-server"` | Could use `IRC_BRIDGE_SERVER` or a `THELOUNGE_IRC_HOST` var |
| `config.js.template` | `port: 6697` | Could use `IRC_TLS_PORT` |
| `config.js.template` | `join: "#help"` | Could use `THELOUNGE_DEFAULT_CHANNEL` |
| `prosody.cfg.lua` | `default_storage = "sql"` + SQLite3 config | Hardcoded to SQLite; the `PROSODY_DB_*` vars in `.env.example` suggest PostgreSQL should be configurable via env. The entrypoint switches based on `PROSODY_STORAGE` but the Lua config itself doesn't read it. |
| `compose.yaml` | `name: atl-chat` | Could use `ATL_PROJECT_NAME` |
| `xmpp.yaml` | `image: allthingslinux/prosody:latest` | Could use a versioned tag env var |
| Various | Docker hostnames like `atl-irc-server`, `atl-xmpp-server` | Hardcoded in multiple config templates; should be consistent env vars if they ever need to change |

### Category E: DEAD — Defined and maybe partially referenced but serve no actual purpose

| Variable | Reason |
|----------|--------|
| `PROSODY_ENV` | Defined as `development`. Nothing reads it. `ATL_ENVIRONMENT` is the actual environment discriminator used by bridge and scripts. |
| `ATHEME_LOG_LEVEL` | Defined as `all`. Atheme config hardcodes `logfile "logs/atheme.log" { debug; };` — doesn't read this env var. |
| `ATHEME_UPLINK_SSL_PORT` | Defined as `6900`. Atheme connects via plaintext port 6901 (`ATHEME_UPLINK_PORT`); the SSL variant is never used since Atheme connects via localhost/Docker network. |
| `ATHEME_CHANFIX_*` (4 vars) | ChanFix module is commented out in atheme.conf.template. These vars are substituted into a dead code block. |
| `PROSODY_ACCOUNT_DELETION_CONFIRMATION` | The Lua code block using it is commented out. |
| All `POSTGRES_*` vars (12 vars) | No PostgreSQL service exists in any compose file. Dev uses SQLite (`PROSODY_STORAGE=sqlite`). The `PROSODY_DB_*` vars exist for when Postgres is enabled, but the `POSTGRES_*` vars (standard Docker image vars) have no compose service to consume them. |
| All `ADMINER_*` vars (7 vars) | No Adminer service in compose files. |
| `NGINX_HTTP_PORT`, `NGINX_HTTPS_PORT` | No main nginx reverse proxy in compose. Only xmpp-nginx exists (different service). |
| `XMPP_C2S_PORT` | Name defined in `.env.example`, but compose uses `PROSODY_C2S_PORT` instead. |
| `XMPP_S2S_PORT` | Same mismatch. |
| `XMPP_HTTP_PORT` | Same mismatch. |
| `XMPP_HTTPS_PORT` | Same mismatch. |

### Category F: DUPLICATE — Same logical setting under multiple variable names

| Logical Setting | Variable Names | Notes |
|----------------|----------------|-------|
| XMPP domain | `XMPP_DOMAIN`, `PROSODY_DOMAIN` | `XMPP_DOMAIN` in `.env.example`, compose maps to `PROSODY_DOMAIN`. Both defined separately in `.env.dev.example`. |
| XMPP C2S port | `XMPP_C2S_PORT`, `PROSODY_C2S_PORT` | `.env.example` defines `XMPP_C2S_PORT`; compose uses `PROSODY_C2S_PORT`. |
| XMPP S2S port | `XMPP_S2S_PORT`, `PROSODY_S2S_PORT` | Same pattern. |
| XMPP HTTP port | `XMPP_HTTP_PORT`, `PROSODY_HTTP_PORT` | Same pattern. |
| XMPP HTTPS port | `XMPP_HTTPS_PORT`, `PROSODY_HTTPS_PORT` | Same pattern. |
| Portal API URL | `BRIDGE_PORTAL_BASE_URL`, `BRIDGE_PORTAL_URL` | Code accepts both (legacy compat). |
| Portal API token | `BRIDGE_PORTAL_TOKEN`, `BRIDGE_PORTAL_API_TOKEN` | Code accepts both (legacy compat). |
| XMPP component secret | `BRIDGE_XMPP_COMPONENT_SECRET`, `XMPP_COMPONENT_SECRET` | Prosody Lua accepts both (legacy fallback). |
| RPC credentials | `WEBPANEL_RPC_USER` / `IRC_UNREAL_RPC_USER` | Same value, two names. |
| RPC credentials | `WEBPANEL_RPC_PASSWORD` / `IRC_UNREAL_RPC_PASSWORD` | Same value, two names. |
| IRC TLS port | `IRC_TLS_PORT` / `IRC_PORT` | Both `6697`. `IRC_TLS_PORT` used by compose ports; `IRC_PORT` used by Portal section. |
| DB password | `PROSODY_DB_PASSWORD` / `POSTGRES_PASSWORD` / `ADMINER_DEFAULT_PASSWORD` | All default to `change_me_secure_db_pass`. |
| DB user | `PROSODY_DB_USER` / `POSTGRES_USER` / `ADMINER_DEFAULT_USERNAME` | All `prosody`. |
| DB name | `PROSODY_DB_NAME` / `POSTGRES_DB` / `ADMINER_DEFAULT_DB` | All `prosody`. |

---

## Summary Statistics

| Category | Count | Severity |
|----------|-------|----------|
| **A: Orphaned** | 37 vars | Medium — clutters .env.example, confuses operators |
| **B: Undefined** | 33 vars | High — some are critical (CLOUDFLARE_DNS_API_TOKEN, TURN_SECRET, PROSODY_DOMAIN) |
| **C: Inconsistent** | 6 issues | High — port naming mismatch causes vars to be silently ignored |
| **D: Hardcoded** | 12 items | Low-Medium — reduces configurability |
| **E: Dead** | ~30 vars | Medium — waste of .env.example real estate |
| **F: Duplicate** | 14 pairs | Medium — confusing, error-prone |

## Recommended Actions (Priority Order)

1. **Fix port naming mismatch (C):** Rename `XMPP_C2S_PORT` → `PROSODY_C2S_PORT` (etc.) in `.env.example`, OR update `xmpp.yaml` to use `XMPP_*` names. Currently the defined vars are **silently ignored**.

2. **Add critical undefined vars to `.env.example` (B):** `CLOUDFLARE_DNS_API_TOKEN`, `TURN_SECRET`, `TURN_EXTERNAL_HOST`, `PROSODY_HTTPS_VIA_PROXY`, `PROSODY_HTTP_EXTERNAL_URL`, `PROSODY_STORAGE`, `DOZZLE_PORT`, `LOG_MAX_SIZE`, `LOG_MAX_FILES`, `XMPP_AVATAR_BASE_URL`, `XMPP_UPLOAD_FETCH_URL`, `IRC_LOG_PATH`, `BRIDGE_IRC_TLS_VERIFY`, `BRIDGE_RELAYMSG_CLEAN_NICKS`.

3. **Remove dead PostgreSQL/Adminer/Nginx sections (A+E):** 21 vars for services with no compose definition. Move to a `compose.postgres.yaml` fragment or remove entirely.

4. **Fix `.env` variable interpolation (C):** `IRC_UNREAL_RPC_USER=${WEBPANEL_RPC_USER}` won't expand in Docker Compose `.env` loading. Either hardcode the values or remove the indirection.

5. **Consolidate XMPP_DOMAIN/PROSODY_DOMAIN (F):** Pick one canonical name. Recommendation: use `XMPP_DOMAIN` in `.env.example` and let compose/scripts derive `PROSODY_DOMAIN` internally.

6. **Remove legacy alias support (F):** `BRIDGE_PORTAL_URL`, `BRIDGE_PORTAL_API_TOKEN`, `XMPP_COMPONENT_SECRET` — if no live deployment uses these, remove the fallbacks.

7. **Remove dead ChanFix vars (E):** 4 vars for a commented-out module.

8. **Document intentional Portal vars (A):** Add a clear comment that `IRC_ATHEME_JSONRPC_URL`, `IRC_SERVER`, `IRC_PORT`, `PROSODY_REST_*`, etc. are consumed by the external Portal service, not this monorepo.
