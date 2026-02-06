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
    "http_openmetrics" -- Prometheus-compatible metrics endpoint

    -- Note: MUC (multi-user chat) is loaded as a component in 30-vhosts-components.cfg.lua
    -- Note: HTTP file sharing is handled by dedicated upload component
}

-- Modules that are auto-loaded but can be explicitly disabled
modules_disabled = {
    -- "offline",  -- Uncomment to disable offline message storage
    -- "c2s",      -- Uncomment to disable client-to-server connections
    -- "s2s",      -- Uncomment to disable server-to-server connections
}

Include("conf.d/00-core.cfg.lua")
Include("conf.d/05-network.cfg.lua")
Include("conf.d/11-logging.cfg.lua")
Include("conf.d/21-security.cfg.lua")
Include("conf.d/25-push-notifications.cfg.lua")
Include("conf.d/30-vhosts-components.cfg.lua")
Include("conf.d/90-contact-compliance.cfg.lua")
