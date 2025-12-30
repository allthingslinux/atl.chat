std = "min"
exclude_files = {
	"prosody-modules",
	"prosody-modules-enabled",
	".git"
}


-- Global variables for Prosody configuration files
globals = {
	-- Core configuration globals
	"pidfile",
	"user",
	"group",
	"admins",
	"default_storage",
	"sql",
	"storage",
	"archive_expires_after",
	"default_archive_policy",
	"archive_compression",
	"archive_store",
	"max_archive_query_results",
	"mam_smart_enable",
	"lua_gc_step_size",
	"lua_gc_pause",
	"gc",

	-- Network configuration globals
	"c2s_ports",
	"c2s_direct_tls_ports",
	"s2s_ports",
	"s2s_direct_tls_ports",
	"component_ports",
	"http_ports",
	"https_ports",
	"interfaces",
	"c2s_interfaces",
	"c2s_direct_tls_interfaces",
	"s2s_interfaces",
	"s2s_direct_tls_interfaces",
	"local_interfaces",
	"external_addresses",
	"use_ipv6",
	"network_backend",
	"network_settings",
	"proxy65_ports",
	"proxy65_interfaces",
	"http_default_host",
	"http_external_url",
	"http_interfaces",
	"https_interfaces",
	"http_files_dir",
	"trusted_proxies",
	"http_cors_override",
	"http_headers",
	"http_file_share_size_limit",
	"http_file_share_daily_quota",
	"http_file_share_expire_after",
	"http_file_share_path",
	"http_file_share_global_quota",
	"bosh_max_inactivity",
	"bosh_max_polling",
	"bosh_max_requests",
	"bosh_max_wait",
	"bosh_session_timeout",
	"bosh_hold_timeout",
	"bosh_window",
	"websocket_frame_buffer_limit",
	"websocket_frame_fragment_limit",
	"websocket_max_frame_size",
	"http_paths",
	"http_status_allow_cidr",
	"turn_external_secret",
	"turn_external_host",
	"turn_external_port",
	"turn_external_ttl",
	"turn_external_tcp",
	"turn_external_tls_port",

	-- Logging configuration globals
	"log",
	"statistics",
	"statistics_interval",
	"openmetrics_allow_ips",
	"openmetrics_allow_cidr",

	-- Security configuration globals
	"limits",
	"max_connections_per_ip",
	"registration_throttle_max",
	"registration_throttle_period",
	"certificates",
	"c2s_require_encryption",
	"s2s_require_encryption",
	"s2s_secure_auth",
	"allow_unencrypted_plain_auth",
	"tls_channel_binding",
	"push_notification_with_body",
	"push_notification_with_sender",
	"authentication",
	"sasl_mechanisms",
	"user_account_management",
	"block_registrations_users",
	"block_registrations_require",

	-- Push notification globals
	"push_notification_important_body",
	"push_max_errors",
	"push_max_devices",
	"push_max_hibernation_timeout",

	-- Virtual host and component globals
	"allow_registration",
	"ssl",
	"name",
	"modules_enabled",
	"muc_notifications",
	"muc_offline_delivery",
	"restrict_room_creation",
	"muc_room_default_public",
	"muc_room_default_persistent",
	"muc_room_locking",
	"muc_room_default_public_jids",
	"muc_log_by_default",
	"muc_log_presences",
	"log_all_rooms",
	"muc_log_expires_after",
	"muc_log_cleanup_interval",
	"muc_max_archive_query_results",
	"muc_log_store",
	"muc_log_compression",
	"muc_mam_smart_enable",
	"proxy65_address",

	-- Compliance globals
	"contact_info",
	"server_info",
	"account_cleanup",

	-- Main configuration globals
	"plugin_paths",
	"plugin_server",
	"installer_plugin_path",
	"modules_disabled",

	-- Prosody configuration functions
	"VirtualHost",
	"Component",
	"Include",

	-- Standard Lua globals used in config
	"Lua",
}

-- Allow unused arguments (common in configuration files)
unused_args = false

-- Set maximum line length to match project standards
max_line_length = 300
