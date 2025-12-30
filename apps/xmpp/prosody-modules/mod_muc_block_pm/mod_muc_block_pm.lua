local st = require "util.stanza";

module:hook("muc-disco#info", function(event)
	table.insert(event.form, { name = "muc#roomconfig_allowpm"; value = "moderators" });
end);

module:hook("muc-private-message", function(event)
	local stanza, room = event.stanza, event.room;
	local from_occupant = room:get_occupant_by_nick(stanza.attr.from);

	if from_occupant and from_occupant.role == "moderator" then
		return -- moderators may message anyone
	end

	local to_occupant = room:get_occupant_by_nick(stanza.attr.to)
	if to_occupant and to_occupant.role == "moderator" then
		return -- messaging moderators is ok
	end

	if to_occupant.bare_jid == from_occupant.bare_jid then
		return -- to yourself is okay, used by some clients to sync read state in public channels
	end

	room:route_to_occupant(from_occupant, st.error_reply(stanza, "cancel", "policy-violation", "Private messages are disabled", room.jid))
	return false;
end, 1);
