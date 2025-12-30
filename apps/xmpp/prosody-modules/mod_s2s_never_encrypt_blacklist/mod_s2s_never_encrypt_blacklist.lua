-- Filter out servers which gets choppy and buggy when it comes to starttls.
-- (C) 2011-2013, Marco Cirillo (LW.Org)

local bad_servers = module:get_option_set("tls_s2s_blacklist", {})
local bad_servers_ip = module:get_option_set("tls_s2s_blacklist_ip", {})
local libev = module:get_option_boolean("use_libevent")

local function disable_tls_for_baddies_in(event)
	local session = event.origin
	if bad_servers:contains(session.from_host) or bad_servers_ip:contains(session.conn:ip()) then
		module:log("debug", "disabling tls on incoming stream from %s...", tostring(session.from_host));
		if libev then session.conn.starttls = false; else session.conn.starttls = nil; end
	end
end

local function disable_tls_for_baddies_out(event)
	local session = event.origin
	if bad_servers:contains(session.to_host) then
		module:log("debug", "disabling tls on outgoing stream from %s...", tostring(session.to_host));
		if libev then session.conn.starttls = false; else session.conn.starttls = nil; end
	end
end

module:hook("s2s-stream-features", disable_tls_for_baddies_in, 600)
module:hook("stanza/http://etherx.jabber.org/streams:features", disable_tls_for_baddies_out, 600)
