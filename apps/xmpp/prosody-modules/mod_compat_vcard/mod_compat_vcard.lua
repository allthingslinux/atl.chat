-- Compatibility with clients and servers (i.e. ejabberd) that send vcard
-- requests to the full JID
--
-- https://support.process-one.net/browse/EJAB-1045

local jid_bare = require "util.jid".bare;
local st = require "util.stanza";
local core_process_stanza = prosody.core_process_stanza;

module:hook("iq/full", function(event)
	local stanza = event.stanza;
	local payload = stanza.tags[1];
	if payload and stanza.attr.type == "get" and payload.name == "vCard" and payload.attr.xmlns == "vcard-temp" then
		local fixed_stanza = st.clone(event.stanza);
		fixed_stanza.attr.to = jid_bare(stanza.attr.to);
		core_process_stanza(event.origin, fixed_stanza);
		return true;
	end
end, 1);
