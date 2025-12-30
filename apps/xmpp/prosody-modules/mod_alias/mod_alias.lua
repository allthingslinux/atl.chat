-- Copyright (C) 2015 Travis Burtrum
-- This file is MIT/X11 licensed.

-- set like so in prosody config, works on full or bare jids, or hosts:
--aliases = {
--		["old@example.net"] = "new@example.net";
--		["you@example.com"] = "you@example.net";
--		["conference.example.com"] = "conference.example.net";
--}

local aliases = module:get_option("aliases", {});
local alias_response = module:get_option("alias_response", "User $alias can be contacted at $target");

local st = require "util.stanza";

function handle_alias(event)

	if event.stanza.attr.type ~= "error" then
		local alias = event.stanza.attr.to;
		local target = aliases[alias];
		if target then
			local replacements = {
				alias = alias,
				target = target
			};
			local error_message = alias_response:gsub("%$([%w_]+)", function (v)
					return replacements[v] or nil;
				end);
			local message = st.message({ type = "chat", from = alias, to = event.stanza.attr.from }, error_message);
			module:send(message);
			return event.origin.send(st.error_reply(event.stanza, "cancel", "gone", error_message));
		end
	end

end

module:hook("message/bare", handle_alias, 300);
module:hook("message/full", handle_alias, 300);
module:hook("message/host", handle_alias, 300);

module:hook("presence/bare", handle_alias, 300);
module:hook("presence/full", handle_alias, 300);
module:hook("presence/host", handle_alias, 300);
