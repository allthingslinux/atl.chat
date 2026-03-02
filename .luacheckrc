-- Global Luacheck Configuration for atl.chat
std = "min"
max_line_length = 300

exclude_files = {
   "node_modules",
   "**/node_modules",
   ".git"
}

-- Default globals (Prosody Configs)
globals = {
   "pidfile", "user", "group", "admins", "log",
   "VirtualHost", "Component", "Include", "Lua",
   -- Network
   "c2s_ports", "s2s_ports", "http_ports", "https_ports", "ssl",
   "c2s_direct_tls_ports", "s2s_direct_tls_ports", "component_ports",
   "interfaces", "c2s_interfaces", "c2s_direct_tls_interfaces",
   "s2s_interfaces", "s2s_direct_tls_interfaces", "local_interfaces",
   "external_addresses", "use_ipv6", "network_backend", "network_settings",
   "proxy65_ports", "proxy65_interfaces", "proxy65_address",
   -- HTTP
   "http_default_host", "http_external_url", "http_interfaces", "https_interfaces",
   "http_files_dir", "trusted_proxies", "http_cors_override", "http_headers",
   "http_file_share_size_limit", "http_file_share_daily_quota",
   "http_file_share_expire_after", "http_file_share_global_quota",
   "http_paths", "http_status_allow_cidr",
   -- BOSH/WebSocket
   "bosh_max_inactivity", "bosh_max_polling", "bosh_max_requests",
   "bosh_max_wait", "bosh_session_timeout", "bosh_hold_timeout", "bosh_window",
   "websocket_frame_buffer_limit", "websocket_frame_fragment_limit", "websocket_max_frame_size",
   -- Database
   "storage", "default_storage", "sql",
   "archive_expires_after", "default_archive_policy", "archive_compression",
   "archive_store", "max_archive_query_results", "mam_smart_enable",
   "dont_archive_namespaces",
   -- Auth
   "authentication", "sasl_mechanisms",
   "user_account_management", "block_registrations_users", "block_registrations_require",
   "allow_registration", "allow_unencrypted_plain_auth", "https_ssl",
   "allowed_oauth2_grant_types", "allowed_oauth2_response_types",
   "oauth2_access_token_ttl", "oauth2_refresh_token_ttl",
   "oauth2_require_code_challenge", "oauth2_registration_key",
   -- Modules
   "modules_enabled", "modules_disabled",
   -- Lua/GC
   "lua_gc_step_size", "lua_gc_pause", "gc",
   -- Plugins
   "plugin_paths", "plugin_server", "installer_plugin_path",
   -- TURN
   "turn_external_secret", "turn_external_host", "turn_external_port",
   "turn_external_ttl", "turn_external_tcp", "turn_external_tls_port",
   -- Stats
   "statistics", "statistics_interval", "openmetrics_allow_ips", "openmetrics_allow_cidr",
   -- Limits
   "limits", "max_connections_per_ip", "registration_throttle_max", "registration_throttle_period",
   -- TLS
   "certificates", "c2s_require_encryption", "s2s_require_encryption", "s2s_secure_auth",
   "tls_channel_binding",
   -- Push
   "push_notification_with_body", "push_notification_with_sender", "push_notification_important_body",
   "push_max_errors", "push_max_devices", "push_max_hibernation_timeout",
   -- MUC
   "muc_notifications", "muc_offline_delivery", "restrict_room_creation",
   "muc_room_default_public", "muc_room_default_persistent", "muc_room_locking",
   "muc_room_default_public_jids", "muc_log_by_default", "muc_log_presences",
   "log_all_rooms", "muc_log_expires_after", "muc_log_cleanup_interval",
   "muc_max_archive_query_results", "muc_log_store", "muc_log_compression", "muc_mam_smart_enable",
   "muc_event_rate", "muc_burst_factor", "muc_max_nick_length", "muc_max_char_count",
   "muc_max_line_count", "muc_limit_base_cost", "muc_line_count_multiplier",
   "default_mucs",
  "default_bookmarks",
   -- Misc
   "name", "domain", "contact_info", "server_info", "account_cleanup", "component_secret",
   "conversejs_options",  -- mod_conversejs
   "component_interfaces", "http_host", "pastebin_threshold", "pastebin_line_threshold",
   "support_contact", "support_contact_nick", "support_contact_group",
   "report_forward_to", "report_forward_to_origin", "report_forward_to_origin_fallback",
   "anti_spam_services", "anti_spam_block_strings", "anti_spam_block_patterns",
   -- PubSub
   "feeds", "add_permissions",
}

-- Per-file overrides
files = {
   ["apps/prosody/config/prosody.cfg.lua"] = {
      unused = false,  -- Prosody config uses env vars; some locals reserved for future use
   },
}
