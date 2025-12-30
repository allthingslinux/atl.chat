module:depends("cache_c2s_caps");

local st = require "util.stanza";

local function disco_handler(event)
	local stanza, origin = event.stanza, event.origin;
	local query = stanza.tags[1];
	local to = stanza.attr.to;
	local node = query.attr.node;

	local target_session = prosody.full_sessions[to];
	if target_session == nil then
		return;
	end

	local disco_info = target_session.caps_cache;
	if disco_info ~= nil and (node == nil or node == disco_info.attr.node) then
		local iq = st.reply(stanza);
		iq:add_child(st.clone(disco_info));
		local log = origin.log or module._log;
		log("debug", "Answering disco#info on the behalf of %s", to);
		module:send(iq);
		return true;
	end
end

module:hook("iq/full", function(event)
	local stanza = event.stanza;
	if stanza.attr.type == "get" then
		if stanza:get_child("query", "http://jabber.org/protocol/disco#info") then
			return disco_handler(event);
		end
	end
end, 1);
