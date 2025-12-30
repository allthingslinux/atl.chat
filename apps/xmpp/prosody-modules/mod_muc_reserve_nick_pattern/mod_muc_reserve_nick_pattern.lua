local jid = require "util.jid";
local st = require "util.stanza";

local nick_patterns = module:get_option_array("muc_reserve_nick_patterns", {});

module:hook("muc-occupant-pre-join", function (event)
	local nick = jid.resource(event.occupant.nick);
	for k, nick_pattern in pairs(nick_patterns) do
		if nick:match(nick_pattern) then
			local reply = st.error_reply(event.stanza, "modify", "conflict", "Unacceptable nickname, please try another");
			module:send(reply);
			return true;
		end
	end
end);
