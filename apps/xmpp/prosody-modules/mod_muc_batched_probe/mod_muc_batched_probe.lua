-- This module allows you to probe the MUC presences for multiple occupants.
-- Copyright (C) 2020 JC Brand

local st = require "util.stanza";
local mod_muc = module:depends"muc";
local get_room_from_jid = rawget(mod_muc, "get_room_from_jid") or
	function (jid)
		local rooms = rawget(mod_muc, "rooms");
		return rooms[jid];
	end

module:log("debug", "Module loaded");

local function respondToBatchedProbe(event)
	local stanza = event.stanza;
	if stanza.attr.type ~= "get" then
		return;
	end
	local query = stanza:get_child("query", "http://jabber.org/protocol/muc#user");
	if not query then
		return;
	end;

	local origin = event.origin;
	local room = get_room_from_jid(stanza.attr.to);
	local probing_occupant = room:get_occupant_by_real_jid(stanza.attr.from);
	if probing_occupant == nil then
		origin.send(st.error_reply(stanza, "cancel", "not-acceptable", "You are not currently connected to this chat", room.jid));
		return true;
	end

	for item in query:children() do
		local probed_jid = item.attr.jid;
		local probed_occupant = room:get_occupant_by_nick(probed_jid);
		if probed_occupant == nil then
			local pr = room:build_unavailable_presence(probed_jid, stanza.attr.from);
			if pr then
				room:route_stanza(pr);
			end
		else
			local x = st.stanza("x", {xmlns = "http://jabber.org/protocol/muc#user"});
			room:publicise_occupant_status(probed_occupant, x, nil, nil, nil, nil, false, probing_occupant);
		end
	end
	origin.send(st.reply(stanza));
	return true;
end


module:hook("iq/bare", respondToBatchedProbe, 1);
