local st = require "util.stanza";
local watchdog = require "util.watchdog";
local dt = require "util.datetime";

local keepalive_servers = module:get_option_set("keepalive_servers");
local keepalive_interval = module:get_option_number("keepalive_interval", 60);
local keepalive_timeout = module:get_option_number("keepalive_timeout", 593);

local host = module.host;
local s2sout = prosody.hosts[host].s2sout;

local function send_pings()
	local ping_hosts = {};

	for remote_domain, session in pairs(s2sout) do
		if session.type ~= "s2sout_unauthed"
		and (not(keepalive_servers) or keepalive_servers:contains(remote_domain)) then
			session.sends2s(st.iq({ to = remote_domain, type = "get", from = host, id = "keepalive:"..dt.datetime()})
				:tag("ping", { xmlns = "urn:xmpp:ping" })
			);
		end
	end

	for session in pairs(prosody.incoming_s2s) do
		if session.type ~= "s2sin_unauthed"
		and not session.notopen
		and session.to_host == host
		and (not(keepalive_servers) or keepalive_servers:contains(session.from_host)) then
			if not s2sout[session.from_host] then ping_hosts[session.from_host] = true; end
			session.sends2s " ";
			-- If the connection is dead, this should make it time out.
		end
	end

	-- ping remotes we only have s2sin from
	for remote_domain in pairs(ping_hosts) do
		module:send(st.iq({ to = remote_domain, type = "get", from = host, id = "keepalive:"..dt.datetime() })
			:tag("ping", { xmlns = "urn:xmpp:ping" })
		);
	end

	return keepalive_interval;
end

module:hook("s2sin-established", function (event)
	local session = event.session;
	if session.watchdog_keepalive then return end -- in case mod_bidi fires this twice
	if keepalive_servers and not keepalive_servers:contains(session.from_host) then return end
	session.watchdog_keepalive = watchdog.new(keepalive_timeout, function ()
		session.log("info", "Keepalive ping timed out, closing connection");
		session:close("connection-timeout");
	end);
end);

module:hook("s2sout-established", function (event)
	local session = event.session;
	if session.watchdog_keepalive then return end -- in case mod_bidi fires this twice
	if keepalive_servers and not keepalive_servers:contains(session.from_host) then return end
	session.watchdog_keepalive = watchdog.new(keepalive_timeout, function ()
		session.log("info", "Keepalive ping timed out, closing connection");
		session:close("connection-timeout");
	end);
end);

module:hook("iq/host", function (event)
	local stanza = event.stanza;
	if stanza.attr.type ~= "result" and stanza.attr.type ~= "error" then
		return -- not a reply iq stanza
	end
	if not (stanza.attr.id and stanza.attr.id:sub(1, #"keepalive:") == "keepalive:") then
		return -- not a reply to this module
	end
	if stanza.attr.type == "error" then
		local err = stanza:get_child("error");
		local err_by = err and err.attr.by;
		if err_by and prosody.hosts[err_by] then
			return -- error produced by the local host
		end
	end

	local origin = event.origin;
	if origin.dummy then return end -- Probably a sendq bounce
	if origin.watchdog_keepalive then
		origin.log("debug", "Resetting keepalive watchdog")
		origin.watchdog_keepalive:reset();
	end
	if s2sout[origin.from_host] and s2sout[origin.from_host].watchdog_keepalive then
		s2sout[origin.from_host].watchdog_keepalive:reset();
	end
	return true;
end);

module:add_timer(keepalive_interval, send_pings);
