local st = require"util.stanza";
local datetime = require"util.datetime";

local presence = st.presence({ from = module.host })
	:tag("delay", { xmlns = "urn:xmpp:delay",
		stamp = datetime.datetime(prosody.start_time) });

module:hook("presence/host", function(event)
	local stanza = event.stanza;
	if stanza.attr.type == "probe" then
		presence.attr.id = stanza.attr.id;
		presence.attr.to = stanza.attr.from;
		module:send(presence);
		return true;
	end
end, 10);

