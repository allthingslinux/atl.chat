local jid_bare = require "util.jid".bare;
local jid_split = require "util.jid".split;
local sessions = prosody.full_sessions;

module:hook("presence/full", function (event)
	local stanza = event.stanza;
	local session = sessions[stanza.attr.to];
	if not session then return end;
	if not session.directed then return end -- hasn't sent presence yet
	local log = session.log or module._log;

	local muc_x = stanza:get_child("x", "http://jabber.org/protocol/muc#user");
	if not muc_x then return end -- Not MUC related

	local from_jid = stanza.attr.from;
	local room = jid_bare(from_jid);
	local _,_,nick = jid_split(from_jid);
	local joined = stanza.attr.type;
	if joined == nil then
		joined = nick;
	elseif joined == "unavailable" then
		joined = nil;
	else
		-- Ignore errors and whatever
		return;
	end

	if joined and not session.directed[from_jid] then
		return; -- Never sent presence there, can't be a MUC join
	end

	-- Check for status code 110, meaning it's their own reflected presence
	for status in muc_x:childtags("status") do
		log("debug", "Status code %d", status.attr.code);
		if status.attr.code == "110" then
			log("debug", "%s room %s", joined and "Joined" or "Left", room);
			local rooms = session.rooms_joined;
			if not rooms then
				if not joined then return; end
				session.rooms_joined = { [room] = joined };
			else
				rooms[room] = joined;
			end
			return;
		end
	end
end, 1);

