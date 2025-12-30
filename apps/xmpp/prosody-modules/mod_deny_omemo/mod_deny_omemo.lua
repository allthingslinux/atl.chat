local st = require "util.stanza";

local omemo_namespace_prefix = "eu.siacs.conversations.axolotl."

module:hook("iq/bare/http://jabber.org/protocol/pubsub:pubsub", function (event)
	local origin, stanza = event.origin, event.stanza;

	local node = stanza.tags[1].tags[1].attr.node;
	if node and node:sub(1, #omemo_namespace_prefix) == omemo_namespace_prefix then
		origin.send(st.error_reply(stanza, "cancel", "item-not-found", "OMEMO is disabled"));
		return true;
	end
end, 10);
