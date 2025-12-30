
-- mod_ipcheck.lua
-- Implementation of XEP-0279: Server IP Check <http://xmpp.org/extensions/xep-0279.html>

local st = require "util.stanza";

module:add_feature("urn:xmpp:sic:0");

module:hook("iq-get/bare/urn:xmpp:sic:0:ip", function(event)
	local origin, stanza = event.origin, event.stanza;
	if stanza.attr.to then
		origin.send(st.error_reply(stanza, "auth", "forbidden", "You can only ask about your own IP address"));
	elseif origin.ip then
		origin.send(st.reply(stanza):tag("ip", {xmlns='urn:xmpp:sic:0'}):text(origin.ip));
	else
		-- IP addresses should normally be available, but in case they are not
		origin.send(st.error_reply(stanza, "cancel", "service-unavailable", "IP address for this session is not available"));
	end
	return true;
end);

module:add_feature("urn:xmpp:sic:1");

module:hook("iq-get/bare/urn:xmpp:sic:1:address", function(event)
	local origin, stanza = event.origin, event.stanza;
	if stanza.attr.to then
		origin.send(st.error_reply(stanza, "auth", "forbidden", "You can only ask about your own IP address"));
	elseif origin.ip then
		local reply = st.reply(stanza):tag("address", {xmlns='urn:xmpp:sic:1'})
			:tag("ip"):text(origin.ip):up()
		if origin.conn and origin.conn.port then -- server_event
			reply:tag("port"):text(tostring(origin.conn:port()))
		elseif origin.conn and origin.conn.clientport then -- server_select
			reply:tag("port"):text(tostring(origin.conn:clientport()))
		end
		origin.send(reply);
	else
		-- IP addresses should normally be available, but in case they are not
		origin.send(st.error_reply(stanza, "cancel", "service-unavailable", "IP address for this session is not available"));
	end
	return true;
end);
