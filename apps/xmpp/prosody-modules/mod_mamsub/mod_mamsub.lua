-- MAM Subscriptions prototype
-- Copyright (C) 2015 Kim Alvefur
--
-- This file is MIT/X11 licensed.

local mt = require"util.multitable";
local st = require"util.stanza";

local xmlns_mamsub = "http://prosody.im/protocol/mamsub";

module:add_feature(xmlns_mamsub);

local host_sessions = prosody.hosts[module.host].sessions;

local weak = { __mode = "k" };

module:hook("iq-set/self/"..xmlns_mamsub..":subscribe", function (event)
	local origin, stanza = event.origin, event.stanza;
	if origin.mamsub ~= nil then
		origin.send(st.error_reply(stanza, "modify", "conflict"));
		return true;
	end
	origin.mamsub = xmlns_mamsub;
	local mamsub_sessions = host_sessions[origin.username].mamsub_sessions;
	if not mamsub_sessions then
		mamsub_sessions = setmetatable({}, weak);
		host_sessions[origin.username].mamsub_sessions = mamsub_sessions;
	end
	mamsub_sessions[origin] = true;
	origin.send(st.reply(stanza));
	return true;
end);

module:hook("iq-set/self/"..xmlns_mamsub..":unsubscribe", function (event)
	local origin, stanza = event.origin, event.stanza;
	if origin.mamsub ~= xmlns_mamsub then
		origin.send(st.error_reply(stanza, "modify", "conflict"));
		return true;
	end
	origin.mamsub = nil;
	local mamsub_sessions = host_sessions[origin.username].mamsub_sessions;
	if mamsub_sessions then
		mamsub_sessions[origin] = nil;
	end
	origin.send(st.reply(stanza));
	return true;
end);

module:hook("archive-message-added", function (event)
	local user_session = host_sessions[event.for_user];
	local mamsub_sessions = user_session and user_session.mamsub_sessions;
	if not mamsub_sessions then return end;

	local for_broadcast = st.message():tag("mamsub", { xmlns = xmlns_mamsub })
		:tag("forwarded", { xmlns = "urn:xmpp:forward:0" })
			:add_child(event.stanza);

	for session in pairs(mamsub_sessions) do
		if session.mamsub == xmlns_mamsub then
			for_broadcast.attr.to = session.full_jid;
			session.send(for_broadcast);
		end
	end
end);
