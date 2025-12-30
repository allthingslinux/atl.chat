local st = require "util.stanza";

local blacklist = module:get_option_inherited_set("s2s_blacklist", {});

module:hook("route/remote", function (event)
	if blacklist:contains(event.to_host) then
		if event.stanza.attr.type ~= "error" then
			module:send(st.error_reply(event.stanza, "cancel", "not-allowed", "Communication with this domain is restricted"));
		end
		return true;
	end
end, 100);

module:hook("s2s-stream-features", function (event)
	if blacklist:contains(event.origin.from_host) then
		event.origin:close({
			condition = "policy-violation";
			text = "Communication with this domain is restricted";
		});
	end
end, 1000);
