local jid = require "util.jid";
local set = require "util.set";

local active_affiliations = set.new({ "member", "admin", "owner" });

module:hook("muc-occupant-joined", function (event)
	local room, occupant = event.room, event.occupant;
	local user_jid = occupant.bare_jid;
	local user_affiliation = room:get_affiliation(user_jid);
	if not active_affiliations:contains(user_affiliation) then
		return;
	end
	local aff_data = event.room:get_affiliation_data(user_jid);
	if not aff_data then
		local reserved_nick = jid.resource(occupant.nick);
		module:log("debug", "Automatically reserving nickname '%s' for <%s>", reserved_nick, user_jid);
		room:set_affiliation_data(user_jid, "reserved_nickname", reserved_nick);
		room._reserved_nicks = nil; -- force refresh of nickname map
	end
end);
