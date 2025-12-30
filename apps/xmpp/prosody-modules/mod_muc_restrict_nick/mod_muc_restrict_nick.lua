local jid = require "util.jid";
local st = require "util.stanza";

local nick_pattern = module:get_option_string("muc_restrict_nick_pattern", "^%w+$");

module:hook("muc-occupant-pre-join", function (event)
	local nick = jid.resource(event.occupant.nick);
	if not nick:match(nick_pattern) then
		local reply = st.error_reply(event.stanza, "modify", "policy-violation", "Unacceptable nickname, please try another");
		module:send(reply);
		return true;
	end
end);
