local hosts = _G.hosts;
local st = require "util.stanza";
local nameprep = require "util.encodings".stringprep.nameprep;
local cert_verify_identity = require "util.x509".verify_identity;

module:hook("stanza/jabber:server:dialback:result", function(event)
	local origin, stanza = event.origin, event.stanza;

	if origin.cert_chain_status == "valid" and origin.type == "s2sin_unauthed" or origin.type == "s2sin" then
		local attr = stanza.attr;
		local to, from = nameprep(attr.to), nameprep(attr.from);

		local conn = origin.conn:socket()
		local cert;
		if conn.getpeercertificate then
			cert = conn:getpeercertificate()
		end

		if cert and hosts[to] and cert_verify_identity(from, "xmpp-server", cert) then

			-- COMPAT: ejabberd, gmail and perhaps others do not always set 'to' and 'from'
			-- on streams. We fill in the session's to/from here instead.
			if not origin.from_host then
				origin.from_host = from;
			end
			if not origin.to_host then
				origin.to_host = to;
			end

			module:log("info", "Accepting Dialback without Dialback for %s", from);
			module:fire_event("s2s-authenticated", { session = origin, host = from });
			origin.sends2s(
				st.stanza("db:result", { from = attr.to, to = attr.from, id = attr.id, type = "valid" }));

			return true;
		end
	end
end, 100);


