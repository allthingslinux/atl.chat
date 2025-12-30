--% requires: s2sout-pre-connect-event

local basic_resolver = require "net.resolvers.basic";

local injected = module:get_option("s2s_connect_overrides");

module:hook("s2sout-pre-connect", function (event)
	local session = event.session;
	local to_host = session.to_host;
	local inject = injected and injected[to_host];
	if not inject then return end

	local host, port = inject[1] or inject, tonumber(inject[2]) or 5269;
	event.resolver = basic_resolver.new(host, port, "tcp");
end);
