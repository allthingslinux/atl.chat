local disable_tls_ports = module:get_option_set("disable_tls_ports", {});

module:hook("stream-features", function (event)
	if disable_tls_ports:contains(event.origin.conn:serverport()) then
		module:log("error", "Disabling TLS for client on port %d", event.origin.conn:serverport());
		event.origin.conn.starttls = false;
	end
end, 1000);
