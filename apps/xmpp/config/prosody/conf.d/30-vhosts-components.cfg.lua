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
    "muc_offline_delivery" -- Offline delivery for MUC events
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
