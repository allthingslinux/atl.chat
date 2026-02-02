# IRC Integration TODO

## Atheme JSON-RPC: Enable for Portal Provisioning

When enabling Atheme's JSON-RPC API for programmatic NickServ registration (Portal IRC integration), the following changes are required.

### atl.chat Changes

| Change | Details |
|--------|---------|
| **Enable modules** | Uncomment `misc/httpd` and `transport/jsonrpc` in [atheme.conf.template](src/backend/atheme/conf/atheme.conf.template) (lines 289-291) |
| **Avoid port conflict** | Change `httpd` port from 8080 to 8081 (WebPanel uses 8080) in the `httpd {}` block |
| **Add env var** | Add `ATHEME_HTTPD_PORT=8081` to [env.example](env.example) and use in template |
| **Expose port** | Add `'${ATHEME_HTTPD_PORT:-8081}:8081'` to the unrealircd service ports in [compose.yaml](compose.yaml) |
| **Bind address** | Consider `host = "127.0.0.1"` for internal-only access; `0.0.0.0` only if intentionally exposed and secured |
| **Provisioning account** | Not needed for REGISTER—call with `authcookie='.'`, `account=''` for unauthenticated. See JSON-RPC API section below. |

### Atheme Template Edits

```diff
-#loadmodule "misc/httpd";				/* HTTP Server */
-#loadmodule "misc/login_throttling";	/* Password-based login throttling */
-#loadmodule "transport/xmlrpc";			/* XMLRPC handler for the httpd */
+loadmodule "misc/httpd";				/* HTTP Server */
+loadmodule "misc/login_throttling";	/* Password-based login throttling */
+loadmodule "transport/jsonrpc";			/* JSON-RPC handler for the httpd */
```

```diff
 httpd {
 	host = "0.0.0.0";
 	#host = "::";
 	www_root = "/var/www";
-	port = 8080;
+	port = ${ATHEME_HTTPD_PORT:-8081};
 };
```

### Port Summary

| Service | Port | Notes |
|---------|------|-------|
| IRC TLS | 6697 | Client connections |
| Server linking | 6900 | s2s TLS |
| Atheme uplink | 6901 | Plaintext services link |
| UnrealIRCd JSON-RPC | 8600 | Admin API |
| WebSocket IRC | 8000 | Web clients |
| WebPanel | 8080 | Web UI |
| **Atheme JSON-RPC** | **8081** | For Portal provisioning (to add) |

### Security Notes

- JSON-RPC should be reachable only from trusted IPs or internal network (e.g. Portal server, Docker network)
- REGISTER runs unauthenticated—restrict access by network/firewall
- Avoid exposing JSON-RPC publicly without TLS and proper auth

### JSON-RPC API (from Atheme source: `portal/examples/atheme`)

**Endpoint:** `http://host:port/jsonrpc` (default path `/jsonrpc`).

**Methods:**

- `atheme.login(account, password, sourceip?)` → authcookie (or fault)
- `atheme.logout(authcookie, account)` → success message
- `atheme.command(authcookie, account, sourceip, service, command, ...params)` → command result

**NickServ REGISTER (unauthenticated):**

When called without an IRC user (`si->su == NULL`), NickServ REGISTER accepts **3 parameters**: nick, password, email.

Request (JSON-RPC 2.0):

```json
{ "jsonrpc": "2.0", "method": "atheme.command", "params": [ ".", "", "127.0.0.1", "NickServ", "REGISTER", "nick", "password", "user@example.com" ], "id": 1 }
```

- Use `'.'` and `''` for authcookie and account to run unauthenticated (no prior login).
- `sourceip` is logged; use Portal server IP or a sentinel like `127.0.0.1`.
- Params: `[ '.', '', sourceip, 'NickServ', 'REGISTER', nick, password, email ]`.

**Fault codes:** 1=needmoreparams, 3=nosuch_source, 5=authfail, 6=noprivs/frozen, 8=alreadyexists, etc. See `doc/JSONRPC`.

### Related

- [Portal IRC Integration Plan](https://github.com/allthingslinux/portal) – Portal-side implementation
- [Portal examples/atheme](https://github.com/allthingslinux/portal/tree/main/examples/atheme) – Local Atheme source; `doc/JSONRPC`, `modules/transport/jsonrpc/main.c`, `modules/nickserv/register.c`
