local jid = require "util.jid";
local st = require "util.stanza";

local local_rooms = module:get_option_inherited_set("muc_local_only", {});

module:hook("muc-occupant-pre-join", function (event)
	local room = event.room;
	if not local_rooms:contains(room.jid) then
		return; -- Not a protected room, ignore
	end
	local user_jid = event.occupant.bare_jid;
	local user_host = jid.host(user_jid);
	if not prosody.hosts[user_host] then
		local error_reply = st.error_reply(event.stanza, "cancel", "forbidden", "This group is only available to local users", room.jid);
		event.origin.send(error_reply);
		return true;
	end
	room:set_affiliation(true, user_jid, "member", "Granting access to local user");
end);
