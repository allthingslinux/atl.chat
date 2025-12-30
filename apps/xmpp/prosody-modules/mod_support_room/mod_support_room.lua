local mm = require "core.modulemanager";
local st = require "util.stanza";
local jid_host, jid_prep = import("util.jid", "host", "prep");

local invite_to_room = assert(jid_prep(module:get_option_string(module.name)),
	"The option " .. module.name .. " must be set");
local inviter = module:get_option_string(module.name .. "_inviter", module.host);
local invite_reason = module:get_option_string(module.name .. "_reason");

module:hook("user-registered", function (event)
	local user_jid = event.username .. "@" .. event.host;
	local muc = mm.get_module(jid_host(invite_to_room), "muc");
	if not muc then
		module:log("error", "There is no MUC service '%s'", jid_host(invite_to_room));
		return;
	end
	local room = muc.get_room_from_jid(invite_to_room);
	if room then
		room:set_affiliation(true, user_jid, "member", invite_reason, { reserved_nickname = event.username });
		-- Invite them to the room too
		module:send(st.message({ from = inviter, to = user_jid })
			:tag("x", { xmlns = "jabber:x:conference", jid = invite_to_room, reason = invite_reason }):up());
	else
		module:log("error", "The room %s does not exist, can't invite newly registered user", invite_to_room);
	end
end);
