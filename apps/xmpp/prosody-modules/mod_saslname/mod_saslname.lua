local hostname = module:get_option_string("sasl_hostname", module.host);

module:hook("stream-features", function(event)
	local features = event.features;
	local mechs = features:get_child("mechanisms", "urn:ietf:params:xml:ns:xmpp-sasl");
	if mechs then
		mechs:tag("hostname", { xmlns = "urn:xmpp:domain-based-name:1" })
			:text(hostname):up();
	end
end);
