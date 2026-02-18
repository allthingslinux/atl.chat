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
   -- Database
   "storage", "default_storage", "sql",
   -- Auth
   "authentication", "sasl_mechanisms",
   -- Modules
   "modules_enabled", "modules_disabled",
}
