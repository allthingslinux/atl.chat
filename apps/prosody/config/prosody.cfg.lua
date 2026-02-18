-- Plugin paths for community and custom modules
plugin_paths = {
    "/usr/local/lib/prosody/prosody-modules-enabled",
    "/var/lib/prosody/custom_plugins"
}

plugin_server = "https://modules.prosody.im/rocks/"

-- Ensure installer writes to image-owned path (not the /var/lib volume)
installer_plugin_path = "/usr/local/lib/prosody/prosody-modules-enabled"

modules_enabled = {
    -- ===============================================
    -- CORE PROTOCOL MODULES (Required)
    -- ===============================================
    "roster",     -- Allow users to have a roster/contact list (RFC 6121)
    "legacyauth", -- Legacy authentication. Only used by some old clients and bots.
    "saslauth",   -- SASL authentication for clients and servers (RFC 4422)
    "tls",        -- TLS encryption support for c2s/s2s connections (RFC 6120)
    "dialback",   -- Server-to-server authentication via dialback (XEP-0220)
    "disco",      -- Service discovery for features and items (XEP-0030)
    "presence",   -- Presence information and subscriptions (RFC 6121)
    "message",    -- Message routing and delivery (RFC 6120)
    "iq",         -- Info/Query request-response semantics (RFC 6120)
    "s2s_status", -- https://modules.prosody.im/mod_s2s_status.html
    "s2s_bidi",   -- XEP-0288: Bidirectional Server-to-Server Connections
    "limits",     -- ===============================================
    -- DISCOVERY & CAPABILITIES
    -- ===============================================
    "version",      -- Server version information (XEP-0092)
    "uptime",       -- Server uptime reporting (XEP-0012)
    "time",         -- Entity time reporting (XEP-0202)
    "ping",         -- XMPP ping for connectivity testing (XEP-0199)
    "lastactivity", -- Last activity timestamps (XEP-0012)
    -- ===============================================
    -- MESSAGING & ARCHIVING
    -- ===============================================
    "mam",     -- Message Archive Management for message history (XEP-0313)
    "carbons", -- Message carbons for multi-device sync (XEP-0280)
    "offline", -- Store messages for offline users (XEP-0160)
    "smacks",  -- Stream Management for connection resumption (XEP-0198)
    -- ===============================================
    -- CLIENT STATE & OPTIMIZATION
    -- ===============================================
    "csi",
    -- "csi_simple", -- Client State Indication for mobile optimization (XEP-0352)
    "csi_battery_saver", -- Enhanced CSI with battery saving features
    -- ===============================================
    -- USER PROFILES & PERSONAL DATA
    -- ===============================================
    "vcard4",
    "vcard_legacy", -- Legacy vCard support for older clients (XEP-0054)
    "private",      -- Private XML storage for client data (XEP-0049)
    "pep",          -- Personal Eventing Protocol for presence extensions (XEP-0163)
    "bookmarks",    -- Bookmark storage and synchronization (XEP-0402, XEP-0411)
    -- ===============================================
    -- PUSH NOTIFICATIONS
    -- ===============================================
    "cloud_notify",            -- Push notifications for mobile devices (XEP-0357)
    "cloud_notify_extensions", -- Enhanced push notification features
    -- ===============================================
    -- SECURITY & PRIVACY
    -- ===============================================
    "blocklist",       -- User blocking functionality (XEP-0191)
    "anti_spam",       -- Spam prevention and detection
    "spam_reporting",  -- Spam reporting mechanisms (XEP-0377)
    "admin_blocklist", -- Administrative blocking controls
    -- ===============================================
    -- REGISTRATION & USER MANAGEMENT
    -- ===============================================
    "register",           -- In-band user registration (XEP-0077)
    -- "invites", -- User invitation system
    "welcome",            -- Welcome messages for new users
    "watchregistrations", -- Administrative alerts for new registrations
    "mimicking",          -- Prevent address spoofing
    "flags",              -- Module to view and manage flags on user accounts via shell/API.
    -- ===============================================
    -- ADMINISTRATIVE INTERFACES
    -- ===============================================
    "admin_adhoc",       -- Administrative commands via XMPP (XEP-0050)
    "admin_shell",       -- Administrative shell interface
    "announce",          -- Server-wide announcements
    "motd",              -- Message of the day for users2
    "compliance_latest", -- Compliance tester
    -- ===============================================
    -- WEB SERVICES & HTTP
    -- ===============================================
    "http",          -- HTTP server functionality
    "bosh",          -- BOSH (HTTP binding) for web clients (XEP-0124, XEP-0206)
    "websocket",     -- WebSocket connections for web clients (RFC 7395)
    "http_files",    -- Static file serving over HTTP
    "conversejs",    -- Converse.js web client at /conversejs (auto-config from VirtualHost)
    "http_status",   -- HTTP status API for monitoring (XEP-0156)
    -- "proxy65", -- Disabled here; provided via dedicated Component `proxy.atl.chat`
    "turn_external", -- External TURN server support (XEP-0215)
    -- ===============================================
    -- SYSTEM & PLATFORM
    -- ===============================================
    "groups", -- Shared roster groups support
    -- ===============================================
    -- COMPLIANCE & CONTACT INFORMATION
    -- ===============================================
    "server_contact_info", -- Contact information advertisement (XEP-0157)
    "server_info",         -- Server information (XEP-0157)
    -- ===============================================
    -- MONITORING & METRICS
    -- ===============================================
    "http_openmetrics", -- Prometheus-compatible metrics endpoint
    "measure_modules"  -- Module status as OpenMetrics (gauge 0=ok, 1=info, 2=warn, 3=error)

    -- Note: MUC (multi-user chat) is loaded as a component in 30-vhosts-components.cfg.lua
    -- Note: HTTP file sharing is handled by dedicated upload component
}

-- Modules that are auto-loaded but can be explicitly disabled
modules_disabled = {
    -- "offline",  -- Uncomment to disable offline message storage
    -- "c2s",      -- Uncomment to disable client-to-server connections
    -- "s2s",      -- Uncomment to disable server-to-server connections
}

-- ===============================================
-- CORE SERVER SETTINGS
-- ===============================================

-- Process management
pidfile = "/var/run/prosody/prosody.pid"
user = "prosody"
group = "prosody"

admins = { Lua.os.getenv("PROSODY_ADMIN_JID") or "admin@localhost" }

-- ===============================================
-- DATA STORAGE
-- ===============================================

default_storage = "sql"

-- SQLite configuration
sql = {
	driver = "SQLite3",
	database = "data/prosody.sqlite",
}

-- Storage backend assignments
storage = {
	-- User data
	accounts = "sql",
	roster = "sql",
	vcard = "sql",
	private = "sql",
	blocklist = "sql",

	-- Message archives
	archive = "sql",
	muc_log = "sql",
	offline = "sql",

	-- PubSub and PEP
	pubsub_nodes = "sql",
	pubsub_data = "sql",
	pep = "sql",

	-- File sharing
	http_file_share = "sql",

	-- Activity tracking
	account_activity = "sql",

	-- Memory-only (ephemeral)
	caps = "memory", -- Entity capabilities cache
	carbons = "memory", -- Message carbons state
}

-- ===============================================
-- MESSAGE ARCHIVING (MAM)
-- ===============================================

-- Archive retention and policy
archive_expires_after = Lua.os.getenv("PROSODY_ARCHIVE_EXPIRES_AFTER") or "1y" -- Keep messages for 1 year
default_archive_policy = Lua.os.getenv("PROSODY_ARCHIVE_POLICY") ~= "false"    -- Archive all conversations by default
archive_compression = Lua.os.getenv("PROSODY_ARCHIVE_COMPRESSION") ~= "false"  -- Compress archived messages
archive_store = Lua.os.getenv("PROSODY_ARCHIVE_STORE") or "archive"            -- Storage backend for archives

-- Query limits
max_archive_query_results = Lua.tonumber(Lua.os.getenv("PROSODY_ARCHIVE_MAX_QUERY_RESULTS")) or
	250 -- Limit results per query
mam_smart_enable = Lua.os.getenv("PROSODY_MAM_SMART_ENABLE") ==
	"true" -- Disable smart archiving

-- Namespaces to exclude from archiving
-- dont_archive_namespaces = {
-- 	"http://jabber.org/protocol/chatstates", -- Chat state notifications
-- 	"urn:xmpp:jingle-message:0", -- Jingle messages
-- }

-- ===============================================
-- MOBILE CLIENT OPTIMIZATIONS
-- ===============================================

-- Client detection patterns
-- mobile_client_patterns = {
-- 	"Conversations",
-- 	"ChatSecure",
-- 	"Monal",
-- 	"Siskin",
-- 	"Xabber",
-- 	"Blabber",
-- }

-- Client State Indication (XEP-0352)
-- csi_config = {
-- 	enabled = true,
-- 	default_state = "active",
-- 	queue_presence = true, -- Queue presence updates when inactive
-- 	queue_chatstates = true, -- Queue chat state notifications
-- 	queue_pep = false, -- Don't queue PEP events
-- 	delivery_delay = 30, -- Delay before batching (seconds)
-- 	max_delay = 300, -- Maximum delay (5 minutes)
-- 	batch_stanzas = true, -- Batch multiple stanzas
-- 	max_batch_size = 10, -- Maximum stanzas per batch
-- 	batch_timeout = 60, -- Batch timeout (seconds)
-- }

-- Stream Management (XEP-0198)
-- smacks_config = {
-- 	-- Session resumption timeouts
-- 	resumption_timeout = 300, -- 5 minutes
-- 	max_resumption_timeout = 3600, -- 1 hour maximum
-- 	hibernation_timeout = 60, -- 1 minute
-- 	max_hibernation_timeout = 300, -- 5 minutes maximum
--
-- 	-- Queue management
-- 	max_unacked_stanzas = 500, -- Maximum unacknowledged stanzas
-- 	max_queue_size = 1000, -- Maximum queue size
--
-- 	-- Acknowledgment settings
-- 	ack_frequency = 5, -- Request ack every 5 stanzas
-- 	ack_timeout = 60, -- Timeout for ack requests
--
-- 	-- Mobile-specific settings
-- 	mobile_resumption_timeout = 900, -- 15 minutes for mobile
-- 	mobile_hibernation_timeout = 300, -- 5 minutes for mobile
-- 	mobile_ack_frequency = 10, -- Less frequent acks for mobile
-- }

-- Lua garbage collection
lua_gc_step_size = Lua.tonumber(Lua.os.getenv("LUA_GC_STEP_SIZE")) or 13 -- GC step size
lua_gc_pause = Lua.tonumber(Lua.os.getenv("LUA_GC_PAUSE")) or 110        -- GC pause percentage

-- Enhanced garbage collection
gc = {
	speed = Lua.tonumber(Lua.os.getenv("LUA_GC_SPEED")) or 200,      -- Collection speed
	threshold = Lua.tonumber(Lua.os.getenv("LUA_GC_THRESHOLD")) or 120, -- Memory threshold percentage
}

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
local __domain = Lua.os.getenv("PROSODY_DOMAIN") or "xmpp.localhost"
-- Route requests for unknown hosts (e.g. localhost) to main VirtualHost so / and /status work
http_default_host = __domain
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
turn_external_host = Lua.os.getenv("TURN_EXTERNAL_HOST") or "turn.atl.network"

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

-- ===============================================
-- LOGGING
-- ===============================================

log = {
	{ levels = { min = Lua.os.getenv("PROSODY_LOG_LEVEL") or "info" }, to = "console" },
	-- { levels = { min = "info" }, to = "file", filename = "/var/log/prosody/prosody.log" },
	-- { levels = { min = "warn" }, to = "file", filename = "/var/log/prosody/prosody.err" },
	-- { levels = { "warn", "error" }, to = "file", filename = "/var/log/prosody/security.log" },
}

statistics = Lua.os.getenv("PROSODY_STATISTICS") or "internal"
statistics_interval = Lua.os.getenv("PROSODY_STATISTICS_INTERVAL") or "manual"

-- By default restrict to loopback; allow-list is expanded via CIDR below
openmetrics_allow_ips = {
	Lua.os.getenv("PROSODY_OPENMETRICS_IP") or "127.0.0.1",
}

-- Fixed CIDR allow-list for internal scraping
openmetrics_allow_cidr = Lua.os.getenv("PROSODY_OPENMETRICS_CIDR") or "172.16.0.0/12"

-- ===============================================
-- SECURITY (limits, registration, firewall)
-- ===============================================

limits = {
	c2s = {
		rate = Lua.os.getenv("PROSODY_C2S_RATE") or "10kb/s",
		burst = Lua.os.getenv("PROSODY_C2S_BURST") or "25kb",
		stanza_size = Lua.tonumber(Lua.os.getenv("PROSODY_C2S_STANZA_SIZE")) or (1024 * 256)
	},
	s2s = {
		rate = Lua.os.getenv("PROSODY_S2S_RATE") or "30kb/s",
		burst = Lua.os.getenv("PROSODY_S2S_BURST") or "100kb",
		stanza_size = Lua.tonumber(Lua.os.getenv("PROSODY_S2S_STANZA_SIZE")) or (1024 * 512)
	},
	http_upload = {
		rate = Lua.os.getenv("PROSODY_HTTP_UPLOAD_RATE") or "2mb/s",
		burst = Lua.os.getenv("PROSODY_HTTP_UPLOAD_BURST") or "10mb"
	},
}

max_connections_per_ip = Lua.tonumber(Lua.os.getenv("PROSODY_MAX_CONNECTIONS_PER_IP")) or 5
registration_throttle_max = Lua.tonumber(Lua.os.getenv("PROSODY_REGISTRATION_THROTTLE_MAX")) or 3
registration_throttle_period = Lua.tonumber(Lua.os.getenv("PROSODY_REGISTRATION_THROTTLE_PERIOD")) or 3600

-- ===============================================
-- TLS/SSL SECURITY
-- ===============================================
-- Global TLS configuration. See:
-- https://prosody.im/doc/certificates
-- https://prosody.im/doc/security
-- ssl = {
-- protocol = "tlsv1_2+",
-- ciphers = "ECDHE+AESGCM:ECDHE+CHACHA20:DHE+AESGCM:DHE+CHACHA20:!aNULL:!MD5:!DSS",
-- curve = "secp384r1",
-- options = { "cipher_server_preference", "single_dh_use", "single_ecdh_use" },
-- }

-- Let's Encrypt certificate location (mounted into the container)
certificates = "certs"

-- Require encryption and secure s2s auth
c2s_require_encryption = Lua.os.getenv("PROSODY_C2S_REQUIRE_ENCRYPTION") ~= "false"
s2s_require_encryption = Lua.os.getenv("PROSODY_S2S_REQUIRE_ENCRYPTION") ~= "false"
s2s_secure_auth = Lua.os.getenv("PROSODY_S2S_SECURE_AUTH") ~= "false"
allow_unencrypted_plain_auth = Lua.os.getenv("PROSODY_ALLOW_UNENCRYPTED_PLAIN_AUTH") == "true"

-- Channel binding strengthens SASL against MITM
tls_channel_binding = Lua.os.getenv("PROSODY_TLS_CHANNEL_BINDING") ~= "false"

-- Recommended privacy defaults for push notifications
-- See https://modules.prosody.im/mod_cloud_notify.html
push_notification_with_body = Lua.os.getenv("PROSODY_PUSH_NOTIFICATION_WITH_BODY") == "true"
push_notification_with_sender = Lua.os.getenv("PROSODY_PUSH_NOTIFICATION_WITH_SENDER") == "true"

-- ===============================================
-- AUTHENTICATION & ACCOUNT POLICY
-- ===============================================
-- Hashed password storage and preferred SASL mechanisms
authentication = "internal_hashed"
sasl_mechanisms = {
	"SCRAM-SHA-256",
	"SCRAM-SHA-1",
	"DIGEST-MD5",
}

-- Account lifecycle and registration hygiene
user_account_management = {
	grace_period = Lua.tonumber(Lua.os.getenv("PROSODY_ACCOUNT_GRACE_PERIOD")) or (7 * 24 * 3600),
	deletion_confirmation = Lua.os.getenv("PROSODY_ACCOUNT_DELETION_CONFIRMATION") ~= "false",
}

-- Disallow common/abusive usernames during registration
block_registrations_users = {
	"administrator",
	"admin",
	"root",
	"postmaster",
	"xmpp",
	"jabber",
	"contact",
	"mail",
	"abuse",
	"support",
	"security",
}
block_registrations_require = Lua.os.getenv("PROSODY_BLOCK_REGISTRATIONS_REQUIRE") or "^[a-zA-Z0-9_.-]+$"

-- Inline firewall rules for mod_firewall
-- firewall_rules = [=[
-- %ZONE spam: log=debug
-- RATE: 10 (burst 15) on full-jid
-- TO: spam
-- DROP.

-- %LENGTH > 262144
-- BOUNCE: policy-violation (Stanza too large)
-- ]=]

-- ===============================================
-- PUSH NOTIFICATIONS CONFIGURATION
-- ===============================================
-- Configuration for mod_cloud_notify and mod_cloud_notify_extensions
-- XEP-0357: Push Notifications for mobile devices
-- https://modules.prosody.im/mod_cloud_notify.html

-- ===============================================
-- CLOUD NOTIFY CORE MODULE (XEP-0357)
-- ===============================================

-- Body text for important messages when real body cannot be sent
-- Used when messages are encrypted or have no body
push_notification_important_body = Lua.os.getenv("PROSODY_PUSH_IMPORTANT_BODY") or "New Message!"

-- Maximum persistent push errors before disabling notifications for a device
-- Default: 16, Production: 16-32 depending on tolerance
push_max_errors = Lua.tonumber(Lua.os.getenv("PROSODY_PUSH_MAX_ERRORS")) or 16

-- Maximum number of devices per user
-- Default: 5, Production: 5-10 depending on user needs
push_max_devices = Lua.tonumber(Lua.os.getenv("PROSODY_PUSH_MAX_DEVICES")) or 5

-- Extend smacks timeout if no push was triggered yet
-- Default: 259200 (72 hours), Production: 259200-604800 (3-7 days)
push_max_hibernation_timeout = Lua.tonumber(Lua.os.getenv("PROSODY_PUSH_MAX_HIBERNATION_TIMEOUT")) or 259200

-- Privacy settings (configured in 21-security.cfg.lua)
-- push_notification_with_body = false      -- Don't send message body to push gateway
-- push_notification_with_sender = false    -- Don't send sender info to push gateway

-- ===============================================
-- CLOUD NOTIFY EXTENSIONS (iOS CLIENT SUPPORT)
-- ===============================================
-- Enhanced push notification features for Siskin, Snikket iOS, and other clients
-- that require additional extensions beyond XEP-0357

-- Enable iOS-specific push notification features
-- This module provides enhanced support for:
-- - Siskin (iOS XMPP client)
-- - Snikket (iOS XMPP client)
-- - Other iOS clients with extended push requirements

-- ===============================================
-- INTEGRATION WITH OTHER MODULES
-- ===============================================

-- This module works with:
-- - mod_smacks: Stream Management for connection resumption
-- - mod_mam: Message Archive Management for offline messages
-- - mod_carbons: Message Carbons for multi-device sync
-- - mod_csi: Client State Indication for mobile optimization

-- ===============================================
-- BUSINESS RULES AND MESSAGE HANDLING
-- ===============================================
-- The module automatically handles:
-- - Offline messages stored by mod_offline
-- - Messages stored by mod_mam (Message Archive Management)
-- - Messages waiting in the smacks queue
-- - Hibernated sessions via mod_smacks
-- - Delayed acknowledgements via mod_smacks

-- ===============================================
-- MONITORING AND DEBUGGING
-- ===============================================
-- To monitor push notification activity:
-- - Check Prosody logs for "cloud_notify" entries
-- - Monitor for push errors and device registration
-- - Use prosodyctl shell to inspect push registrations

-- ===============================================
-- CLIENT COMPATIBILITY
-- ===============================================
-- Supported clients include:
-- - Conversations (Android)
-- - Monal (iOS)
-- - Siskin (iOS) - requires mod_cloud_notify_extensions
-- - Snikket (iOS) - requires mod_cloud_notify_extensions
-- - ChatSecure (iOS)
-- - Xabber (Android)
-- - Blabber (Android)

-- Note: Some iOS clients require mod_cloud_notify_extensions for full functionality
-- as they use extensions not currently defined in XEP-0357

-- ===============================================
-- VIRTUAL HOSTS + COMPONENTS
-- ===============================================
-- Domain and registration settings
local domain = Lua.os.getenv("PROSODY_DOMAIN") or "atl.chat"
allow_registration = Lua.os.getenv("PROSODY_ALLOW_REGISTRATION") ~= "false"

-- Single VirtualHost
VirtualHost(domain)
ssl = {
    key = Lua.os.getenv("PROSODY_SSL_KEY") or
        ("certs/live/" .. domain .. "/privkey.pem"),
    certificate = Lua.os.getenv("PROSODY_SSL_CERT") or
        ("certs/live/" .. domain .. "/fullchain.pem")
}

Component("muc." .. domain) "muc"

ssl = {
    key = Lua.os.getenv("PROSODY_SSL_KEY") or
        ("certs/live/" .. domain .. "/privkey.pem"),
    certificate = Lua.os.getenv("PROSODY_SSL_CERT") or
        ("certs/live/" .. domain .. "/fullchain.pem")
}
name = "muc." .. domain

-- MUC-specific modules
modules_enabled = {
    -- "muc", -- Not needed here; this is a dedicated MUC component
    "muc_mam", -- Message Archive Management for MUC events
    -- "vcard_muc", -- Conflicts with built-in muc_vcard on Prosody 13
    "muc_notifications", -- Push notifications for MUC events
    "muc_offline_delivery", -- Offline delivery for MUC events
    "muc_thread_polyfill" -- Infer thread from XEP-0461 reply when client lacks thread UI
    -- "muc_local_only",
    -- "pastebin",
}

-- MUC push notification configuration
-- Ensure MUC messages trigger push notifications for offline users
muc_notifications = Lua.os.getenv("PROSODY_MUC_NOTIFICATIONS") ~= "false"
muc_offline_delivery = Lua.os.getenv("PROSODY_MUC_OFFLINE_DELIVERY") ~= "false"

restrict_room_creation = Lua.os.getenv("PROSODY_RESTRICT_ROOM_CREATION") ==
                             "true"
muc_room_default_public = Lua.os.getenv("PROSODY_MUC_DEFAULT_PUBLIC") ~= "false"
muc_room_default_persistent = Lua.os.getenv("PROSODY_MUC_DEFAULT_PERSISTENT") ~=
                                  "false"
muc_room_locking = Lua.os.getenv("PROSODY_MUC_LOCKING") == "true"
muc_room_default_public_jids =
    Lua.os.getenv("PROSODY_MUC_DEFAULT_PUBLIC_JIDS") ~= "false"
-- vcard_to_pep = true

-- General MUC configuration
-- max_history_messages = 50
-- muc_room_lock_timeout = 300
-- muc_tombstones = true
-- muc_room_cache_size = 1000
-- muc_room_default_public = true
-- muc_room_default_members_only = false
-- muc_room_default_moderated = false
-- muc_room_default_persistent = true
-- muc_room_default_language = "en"
-- muc_room_default_change_subject = true

-- MUC Message Archive Management (MAM)
muc_log_by_default = Lua.os.getenv("PROSODY_MUC_LOG_BY_DEFAULT") ~= "false"
muc_log_presences = Lua.os.getenv("PROSODY_MUC_LOG_PRESENCES") == "true"
log_all_rooms = Lua.os.getenv("PROSODY_MUC_LOG_ALL_ROOMS") == "true"
muc_log_expires_after = Lua.os.getenv("PROSODY_MUC_LOG_EXPIRES_AFTER") or "1y"
muc_log_cleanup_interval = Lua.tonumber(Lua.os.getenv(
                                            "PROSODY_MUC_LOG_CLEANUP_INTERVAL")) or
                               86400
muc_max_archive_query_results = Lua.tonumber(Lua.os.getenv(
                                                 "PROSODY_MUC_MAX_ARCHIVE_QUERY_RESULTS")) or
                                    100
muc_log_store = Lua.os.getenv("PROSODY_MUC_LOG_STORE") or "muc_log"
muc_log_compression = Lua.os.getenv("PROSODY_MUC_LOG_COMPRESSION") ~= "false"
muc_mam_smart_enable = Lua.os.getenv("PROSODY_MUC_MAM_SMART_ENABLE") == "true"

-- muc_dont_archive_namespaces = {
-- "http://jabber.org/protocol/chatstates",
-- "urn:xmpp:jingle-message:0",
-- "http://jabber.org/protocol/muc#user",
-- }

-- muc_archive_policy = "all"
-- muc_log_notification = true

-- Pastebin settings
-- pastebin_threshold = 800
-- pastebin_line_threshold = 6

-- HTTP File Upload component
Component("upload." .. domain) "http_file_share"
ssl = {
    key = Lua.os.getenv("PROSODY_SSL_KEY") or
        ("certs/live/" .. domain .. "/privkey.pem"),
    certificate = Lua.os.getenv("PROSODY_SSL_CERT") or
        ("certs/live/" .. domain .. "/fullchain.pem")
}
name = "upload." .. domain
http_external_url = Lua.os.getenv("PROSODY_UPLOAD_EXTERNAL_URL") or
                        ("https://upload." .. domain .. "/")

-- SOCKS5 Proxy component
Component("proxy." .. domain) "proxy65"
ssl = {
    key = Lua.os.getenv("PROSODY_SSL_KEY") or
        ("certs/live/" .. domain .. "/privkey.pem"),
    certificate = Lua.os.getenv("PROSODY_SSL_CERT") or
        ("certs/live/" .. domain .. "/fullchain.pem")
}
name = "proxy." .. domain
proxy65_address = Lua.os.getenv("PROSODY_PROXY_ADDRESS") or ("proxy." .. domain)

-- ===============================================
-- CONTACT INFO, ROLES, ACCOUNT CLEANUP
-- ===============================================

-- Domain and contact configuration
local domain = Lua.os.getenv("PROSODY_DOMAIN") or "atl.chat"
local admin_email = Lua.os.getenv("PROSODY_ADMIN_EMAIL") or ("admin@" .. domain)

contact_info = {
	admin = {
		"xmpp:admin@" .. domain,
		"mailto:" .. admin_email,
	},
	abuse = {
		"xmpp:admin@" .. domain,
		"mailto:" .. admin_email,
	},
	support = {
		"xmpp:admin@" .. domain,
		"mailto:" .. admin_email,
	},
	security = {
		"xmpp:admin@" .. domain,
		"mailto:" .. admin_email,
	},
}

server_info = {
	name = Lua.os.getenv("PROSODY_SERVER_NAME") or domain,
	website = Lua.os.getenv("PROSODY_SERVER_WEBSITE") or ("https://" .. domain),
	description = Lua.os.getenv("PROSODY_SERVER_DESCRIPTION") or (domain .. " XMPP service"),
}

account_cleanup = {
	inactive_period = Lua.tonumber(Lua.os.getenv("PROSODY_ACCOUNT_INACTIVE_PERIOD")) or (365 * 24 * 3600),
	grace_period = Lua.tonumber(Lua.os.getenv("PROSODY_ACCOUNT_GRACE_PERIOD")) or (30 * 24 * 3600),
}
