-- Register via OOB URL
-- Copyright (c) 2018 Daniel Gultsch
--
-- This module is MIT/X11 licensed
--

local st = require "util.stanza";
local namespace = "http://jabber.org/features/iq-register"
local register_stream_feature = st.stanza("register", {xmlns=namespace}):up();
local allow_registration = module:get_option_boolean("allow_registration", false);
local registration_url = module:get_option_string("register_oob_url", nil)

if allow_registration then
	module:log("info","obb registration is disabled as long as IBR is allowed. Set `allow_registration` to false")
end

if not registration_url then
	module:log("info","registration url not configured. Add `register_oob_url` to prosody.cfg")
end

local function on_stream_features(event)
	if not registration_url then
		return
	end
	local session, features = event.origin, event.features;
	if session.type == "c2s_unauthed" and not allow_registration then
		features:add_child(register_stream_feature);
	end
end

local function on_registration_requested(event)
	local session, stanza = event.origin, event.stanza
	if session.type ~= "c2s_unauthed" or stanza.attr.type ~= "get" then
		return
	end
	if not allow_registration and registration_url then
		local reply = st.reply(stanza)
		reply:query("jabber:iq:register")
			:tag("x", {xmlns = "jabber:x:oob"})
				:tag("url"):text(registration_url);
		return session.send(reply)
	end
end

module:hook("stream-features", on_stream_features)
module:hook("stanza/iq/jabber:iq:register:query", on_registration_requested, 1)

-- vim: noexpandtab tabstop=4 shiftwidth=4
