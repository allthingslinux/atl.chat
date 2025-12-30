-- Prosody IM
-- Copyright (C) 2008-2010 Matthew Wild
-- Copyright (C) 2008-2010 Waqas Hussain
--
-- This project is MIT/X11 licensed. Please see the
-- COPYING file in the source package for more information.
--

if module:get_host_type() ~= "component" then
	error("Don't load mod_component manually, it should be for a component, please see http://prosody.im/doc/components", 0);
end

local hosts = _G.hosts;

local t_concat = table.concat;

local sha1 = require "util.hashes".sha1;
local st = require "util.stanza";

local log = module._log;

local sessions = module:shared("sessions");

local last_session;
local function on_destroy(session, err)
	if sessions[session] then
		if last_session == session then last_session = nil; end
		sessions[session] = nil;
		session.on_destroy = nil;
	end
end

local function handle_stanza(event)
	local stanza = event.stanza;
	if next(sessions) then
		stanza.attr.xmlns = nil;
		last_session = next(sessions, last_session) or next(sessions);
		last_session.send(stanza);
	else
		log("warn", "Component not connected, bouncing error for: %s", stanza:top_tag());
		if stanza.attr.type ~= "error" and stanza.attr.type ~= "result" then
			event.origin.send(st.error_reply(stanza, "wait", "service-unavailable", "Component unavailable"));
		end
	end
	return true;
end

module:hook("iq/bare", handle_stanza, -0.5);
module:hook("message/bare", handle_stanza, -0.5);
module:hook("presence/bare", handle_stanza, -0.5);
module:hook("iq/full", handle_stanza, -0.5);
module:hook("message/full", handle_stanza, -0.5);
module:hook("presence/full", handle_stanza, -0.5);
module:hook("iq/host", handle_stanza, -0.5);
module:hook("message/host", handle_stanza, -0.5);
module:hook("presence/host", handle_stanza, -0.5);

--- Handle authentication attempts by components
function handle_component_auth(event)
	local session, stanza = event.origin, event.stanza;

	if session.type ~= "component_unauthed" then return; end
	if sessions[session] then return; end

	if (not session.host) or #stanza.tags > 0 then
		(session.log or log)("warn", "Invalid component handshake for host: %s", session.host);
		session:close("not-authorized");
		return true;
	end

	local secret = module:get_option("component_secret");
	if not secret then
		(session.log or log)("warn", "Component attempted to identify as %s, but component_secret is not set", session.host);
		session:close("not-authorized");
		return true;
	end

	local supplied_token = t_concat(stanza);
	local calculated_token = sha1(session.streamid..secret, true);
	if supplied_token:lower() ~= calculated_token:lower() then
		log("info", "Component authentication failed for %s", session.host);
		session:close{ condition = "not-authorized", text = "Given token does not match calculated token" };
		return true;
	end

	-- Add session to sessions table
	sessions[session] = true;
	session.on_destroy = on_destroy;
	session.component_validate_from = module:get_option_boolean("validate_from_addresses", true);
	session.type = "component";
	log("info", "Component successfully authenticated: %s", session.host);
	session.send(st.stanza("handshake"));

	return true;
end

module:hook("stanza/jabber:component:accept:handshake", handle_component_auth, 10);
