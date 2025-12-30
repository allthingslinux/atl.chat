
module:set_global();

local b64_decode = require "util.encodings".base64.decode;
local server = require "net.http.server";

local credentials = module:get_option_string("http_credentials", "username:secretpassword");
local unauthed_endpoints = module:get_option_set("unauthenticated_http_endpoints", { "/http-bind", "/http-bind/" })._items;

module:wrap_object_event(server._events, false, function (handlers, event_name, event_data)
	local request = event_data.request;
	if event_name ~= "http-error" and request and not unauthed_endpoints[request.path] then
		local response = event_data.response;
		local headers = request.headers;
		if not headers.authorization then
			response.headers.www_authenticate = ("Basic realm=%q"):format(module.host.."/"..module.name);
			return 401;
		end
		local user_password = b64_decode(headers.authorization:match("%s(%S*)$"));
		if user_password ~= credentials then
			return 401;
		end
	end
	return handlers(event_name, event_data);
end);
