-- Copyright (c) 2019 Kim Alvefur
--
-- This project is MIT/X11 licensed. Please see the
-- COPYING file in the source package for more information.
--
-- Yes, this module touches stores data in user sessions
-- luacheck: ignore 122

local grace_period = module:get_option_number("grace_period", 30);

local user_sessions = prosody.hosts[module.host].sessions;

module:hook("csi-is-stanza-important", function (event)
	if event.stanza.name ~= "message" then return end
	local session = event.session;
	if not session then return; end

	local user_session = user_sessions[session.username];
	if not user_session then return; end

	if user_session.grace_time_start then
		if user_session.last_active == session.resource then
			return;
		end
		if (os.time() - user_session.grace_time_start) < grace_period then
			session.log("debug", "Within grace period, probably seen");
			event.reason = "grace period";
			return false;
		end
	end
end, 1);

local function on_activity(event)
	local stanza, origin = event.stanza, event.origin;
	local user_session = user_sessions[origin.username];
	if not user_session then return; end

	if stanza:get_child("body") or stanza:get_child("active", "http://jabber.org/protocol/chatstates") then
		user_session.last_active = origin.resource;
		user_session.grace_time_start = os.time();
	end
end
module:hook("pre-message/full", on_activity);
module:hook("pre-message/bare", on_activity);
module:hook("pre-message/host", on_activity);
