-- Compatibility with clients that set 'to' on resource bind requests
--
-- http://xmpp.org/rfcs/rfc3920.html#bind
-- http://xmpp.org/rfcs/rfc6120.html#bind-servergen-success

local st = require "util.stanza";

module:hook("iq/host/urn:ietf:params:xml:ns:xmpp-bind:bind", function(event)
	local fixed_stanza = st.clone(event.stanza);
	fixed_stanza.attr.to = nil;
	prosody.core_process_stanza(event.origin, fixed_stanza);
	return true;
end);
