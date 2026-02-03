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
