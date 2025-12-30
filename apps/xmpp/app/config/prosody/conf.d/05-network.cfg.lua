-- ===============================================
-- NETWORKING CONFIGURATION
-- ===============================================
-- This file centralizes all network- and port-related settings.
--
-- References:
-- - Port & network configuration docs:
--   https://prosody.im/doc/ports
-- - HTTP server docs:
--   https://prosody.im/doc/http
-- - Config basics and advanced directives:
--   https://prosody.im/doc/configure
--
-- IMPORTANT:
-- - Network options must be set in the GLOBAL section (i.e., not under
--   a VirtualHost/Component) per Prosody's design.
-- - Services can be individually overridden via <service>_ports and
--   <service>_interfaces (e.g., c2s_ports, s2s_interfaces, etc.).
-- - Private services (e.g., components, console) default to loopback.
-- ===============================================
-- Default service ports (override as needed)
-- ===============================================
-- Client-to-server (XMPP over TCP, STARTTLS-capable)
c2s_ports = { 5222 }

-- Client-to-server over direct TLS (XMPP over TLS)
-- Available since Prosody 0.12+
c2s_direct_tls_ports = { 5223 }

-- Server-to-server (federation)
s2s_ports = { 5269 }

-- Server-to-server over direct TLS
-- Available since Prosody 0.12+
s2s_direct_tls_ports = { 5270 }

-- External components (XEP-0114) — private by default
component_ports = { 5347 }

-- HTTP/HTTPS listener (mod_http)
-- Note: 5280 is private by default in Prosody 0.12+
http_ports = { 5280 }
https_ports = { 5281 }

-- ===============================================
-- Interfaces
-- ===============================================
-- By default Prosody listens on all interfaces. To restrict:
--   interfaces = { "127.0.0.1", "::1" }
-- The special "*" means all IPv4; "::" means all IPv6.

interfaces = { "127.0.0.1" } -- Restrict to loopback (default)
-- Expose XMPP services publicly; override per-service so HTTP can remain loopback
c2s_interfaces = { "*" }
c2s_direct_tls_interfaces = { "*" }
s2s_interfaces = { "*" }
s2s_direct_tls_interfaces = { "*" }
local_interfaces = { "127.0.0.1" } -- Private services bind here by default

-- If you need to hint external/public addresses (behind NAT)
external_addresses = {}

-- ===============================================
-- IPv6
-- ===============================================
-- Enable IPv6 if your deployment supports it.
use_ipv6 = false

-- ===============================================
-- Backend & performance tuning
-- ===============================================
-- Available backends: "epoll" (default), "event" (libevent), "select" (legacy)
-- The setting name for libevent backend is "event" for compatibility.
network_backend = "event"

-- Common advanced network settings. See docs for full list.
-- https://prosody.im/doc/ports#advanced
network_settings = {
    read_timeout = 840 -- seconds; align with reverse proxy timeouts (~900s)
    -- send_timeout = 300,
    -- max_send_buffer_size = 1048576,
    -- tcp_backlog = 32,
}

-- ===============================================
-- Proxy65 (XEP-0065) port/interface overrides
-- ===============================================
-- Global port/interface options must be set here (not under Component)
-- Docs: https://prosody.im/doc/modules/mod_proxy65
proxy65_ports = { 5000 }
proxy65_interfaces = { "*" }

-- ===============================================
-- HTTP SERVICES
-- ===============================================
-- HTTP server-level options and module configuration
-- Docs: https://prosody.im/doc/http

-- External URL advertised to clients and components
local __http_host = Lua.os.getenv("PROSODY_HTTP_HOST") or
    Lua.os.getenv("PROSODY_DOMAIN") or "localhost"
local __http_scheme = Lua.os.getenv("PROSODY_HTTP_SCHEME") or "http"
http_default_host = __http_host
http_external_url = __http_scheme .. "://" .. __http_host .. "/"

-- Port/interface defaults per Prosody 0.12 docs:
-- http_ports = { 5280 } (already set above)
-- https_ports = { 5281 } (already set above)
-- http binds to loopback by default; https binds publicly for reverse proxy
http_interfaces = { "*" }
https_interfaces = { "*" }

-- Static file serving root (Prosody's web root; reverse proxy in front)
http_files_dir = "/usr/share/prosody/www"

-- Trusted reverse proxies for X-Forwarded-* handling
trusted_proxies = { "127.0.0.1", "172.18.0.0/16", "10.0.0.0/8" }

-- Enable CORS for BOSH and WebSocket endpoints
http_cors_override = {
    bosh = { enabled = true },
    websocket = { enabled = true },
    file_share = { enabled = true }
}

-- Additional security headers for HTTP responses
http_headers = {
    ["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload",
    ["X-Frame-Options"] = "DENY",
    ["X-Content-Type-Options"] = "nosniff",
    ["X-XSS-Protection"] = "1; mode=block",
    ["Referrer-Policy"] = "strict-origin-when-cross-origin",
    -- Allow Converse.js CDN and XMPP endpoints for mod_conversejs
    ["Content-Security-Policy"] =
    "default-src 'self'; script-src 'self' https://cdn.conversejs.org 'unsafe-inline'; style-src 'self' https://cdn.conversejs.org 'unsafe-inline'; img-src 'self' data: https://cdn.conversejs.org; connect-src 'self' https: wss:; frame-ancestors 'none'"
}

-- HTTP File Upload (XEP-0363)
http_file_share_size_limit = 100 * 1024 * 1024         -- 100MB per file
http_file_share_daily_quota = 1024 * 1024 * 1024       -- 1GB daily quota per user
http_file_share_expire_after = 30 * 24 * 3600          -- 30 days expiration
http_file_share_path = "/var/lib/prosody/http_file_share"
http_file_share_global_quota = 10 * 1024 * 1024 * 1024 -- 10GB global quota

-- BOSH/WebSocket tuning
bosh_max_inactivity = 60
bosh_max_polling = 5
bosh_max_requests = 2
bosh_max_wait = 120
bosh_session_timeout = 300
bosh_hold_timeout = 60
bosh_window = 5
websocket_frame_buffer_limit = 2 * 1024 * 1024
websocket_frame_fragment_limit = 8
websocket_max_frame_size = 1024 * 1024

-- Path mappings served by mod_http
http_paths = {
    file_share = "/upload",
    files = "/",
    pastebin = "/paste",
    bosh = "/http-bind",
    websocket = "/xmpp-websocket",
    conversejs = "/conversejs",
    status = "/status"
}

-- HTTP Status API (mod_http_status) for monitoring
-- Allow access from any IP for monitoring (accessible from anywhere)
-- http_status_allow_ips = { "*" }

-- Alternative: Allow access from specific IPs (more secure)
-- http_status_allow_ips = { "127.0.0.1"; "::1"; "172.18.0.0/16"; "76.215.15.63" }

-- Allow access from any IP using CIDR notation (0.0.0.0/0 covers all IPv4)
http_status_allow_cidr = "0.0.0.0/0"

-- ===============================================
-- TURN/STUN EXTERNAL SERVICES (XEP-0215)
-- ===============================================
-- External TURN/STUN server configuration for audio/video calls
-- These services are provided by the COTURN container

-- TURN external configuration (XEP-0215)
-- A secret shared with the TURN server, used to dynamically generate credentials
turn_external_secret = Lua.os.getenv("TURN_SECRET") or "devsecret"

-- DNS hostname of the TURN (and STUN) server
-- Use dedicated TURN subdomain for clean separation
turn_external_host = Lua.os.getenv("TURN_DOMAIN") or
    Lua.os.getenv("PROSODY_DOMAIN") or "localhost"

-- Port number used by TURN (and STUN) server
turn_external_port = Lua.tonumber(Lua.os.getenv("TURN_PORT")) or 3478

-- How long the generated credentials are valid (default: 1 day)
turn_external_ttl = 86400

-- Whether to announce TURN (and STUN) over TCP, in addition to UDP
-- Note: Most clients prefer UDP, but TCP can help with restrictive firewalls
turn_external_tcp = true

-- Optional: Port offering TURN over TLS (if using TURNS)
-- Enable TLS support for secure TURN connections
turn_external_tls_port = Lua.tonumber(Lua.os.getenv("TURNS_PORT")) or 5349
