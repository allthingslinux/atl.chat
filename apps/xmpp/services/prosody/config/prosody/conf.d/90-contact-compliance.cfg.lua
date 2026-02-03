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
