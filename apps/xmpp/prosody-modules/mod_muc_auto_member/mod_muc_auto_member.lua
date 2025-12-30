module:hook("muc-occupant-joined", function (event)
	local room = event.room;
	local occupant_jid = event.occupant.bare_jid;
	local aff = room:get_affiliation(occupant_jid);
	if aff then return; end -- user already registered
	module:log("debug", "Automatically registering %s as a member in %s", occupant_jid, room.jid);
	room:set_affiliation(true, occupant_jid, "member");
end);
