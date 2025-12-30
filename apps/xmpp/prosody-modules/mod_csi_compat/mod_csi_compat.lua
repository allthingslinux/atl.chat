local st = require "util.stanza";

module:depends("csi");

module:add_feature("google:queue");

module:hook("iq-set/self/google:queue:query", function(event)
	local origin, stanza = event.origin, event.stanza;
	(origin.log or module._log)("debug", "Google queue invoked (CSI compat mode)")
	local payload = stanza:get_child("query", "google:queue");
	if payload:get_child("enable") then
		module:fire_event("csi-client-inactive", event);
	elseif payload:get_child("disable") then
		module:fire_event("csi-client-active", event);
	end
	-- <flush/> is implemented as a noop, any IQ stanza would flush the queue anyways.
	origin.send(st.reply(stanza));
	return true;
end, 10);
