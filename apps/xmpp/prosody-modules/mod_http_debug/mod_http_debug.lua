local json = require "util.json"

module:depends("http")
local function handle_request(event)
	local request = event.request;
	(request.log or module._log)("debug", "%s -- %s %q HTTP/%s -- %q -- %s", request.ip, request.method, request.url, request.httpversion, request.headers, request.body);
	return {
		status_code = 200;
		headers = { content_type = "application/json" };
		host = module.host;
		body = json.encode {
			body = request.body;
			headers = request.headers;
			httpversion = request.httpversion;
			id = request.id;
			ip = request.ip;
			method = request.method;
			path = request.path;
			secure = request.secure;
			url = request.url;
		};
	}
end

local methods = module:get_option_set("http_debug_methods", { "GET"; "HEAD"; "DELETE"; "OPTIONS"; "PATCH"; "POST"; "PUT" });
local route = {};
for method in methods do
	route[method] = handle_request;
	route[method .. " /*"] = handle_request;
end

module:provides("http", {
	route = route;
})
