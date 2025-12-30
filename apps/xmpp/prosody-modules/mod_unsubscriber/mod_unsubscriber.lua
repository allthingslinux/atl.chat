assert(module:get_host_type() == "component", "This module should be loaded as a Component");

local st = require "util.stanza";

module:hook("presence/bare", function(event)
	local origin, stanza = event.origin, event.stanza;
	if stanza.attr.type == "probe" then
		-- they are subscribed and want our current presence
		-- tell them we denied their subscription
		local reply = st.reply(stanza)
		reply.attr.type = "unsubcribed";
		origin.send(reply);
		return true;
	elseif stanza.attr.type == nil then
		-- they think we are subscribed and sent their current presence
		-- tell them we unsubscribe
		local reply = st.reply(stanza)
		reply.attr.type = "unsubcribe";
		origin.send(reply);
		return true;
	end
	-- fall trough to default error
end);
