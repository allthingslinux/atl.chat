-- HTTP Strict Transport Security
-- https://www.rfc-editor.org/info/rfc6797

module:set_global();

local http_server = require "net.http.server";

local hsts_header = module:get_option_string("hsts_header", "max-age=31556952"); -- This means "Don't even try to access without HTTPS for a year"
local redirect = module:get_option_boolean("hsts_redirect", true);

module:wrap_object_event(http_server._events, false, function(handlers, event_name, event_data)
	local request, response = event_data.request, event_data.response;
	if request and response then
		if request.secure then
			response.headers.strict_transport_security = hsts_header;
		elseif redirect then
			-- This won't get the port number right
			response.headers.location = "https://" .. request.host .. request.path .. (request.query and "?" .. request.query or "");
			return 301;
		end
	end
	return handlers(event_name, event_data);
end);
