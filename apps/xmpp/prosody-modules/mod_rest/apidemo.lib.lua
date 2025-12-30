
local _M = {};

local api_demo = module:get_option_path("rest_demo_resources", nil);
local http_files = require "net.http.files";

local mime_map = module:shared("/*/http_files/mime").types or {css = "text/css"; js = "application/javascript"};
_M.resources = http_files.serve({
		path = api_demo;
		mime_map = mime_map;
	});

local index do
	local f, err = io.open(api_demo.."/index.html");
	if not f then
		module:log("error", "Could not open resource: %s", err);
		module:log("error", "'rest_demo_resources' should point to the 'dist' directory");
		return _M
	end
	index = f:read("*a");
	f:close();

	-- SUCH HACK, VERY GSUB, WOW!
	index = index:gsub("(%s?url%s*:%s*)%b\"\"", string.format("%%1%q", module:http_url().."/demo/openapi.yaml"), 1);
	index = index:gsub("(%s*SwaggerUIBundle%s*%(%s*{)(%s*)", "%1%2validatorUrl: false,%2");
end

do
	local f = module:load_resource("res/openapi.yaml");
	local openapi = f:read("*a");
	openapi = openapi:gsub("https://example%.com/oauth2", module:http_url("oauth2"));
	_M.schema = {
		headers = {
			content_type = "text/x-yaml";
		};
		body = openapi;
	}
	f:close();
end

_M.redirect = {
	status_code = 303;
	headers = {
		location = module:http_url().."/demo/";
	};
};

_M.main_page = {
	headers = {
		content_type = "text/html";
		content_security_policy = "default-src 'self' data:; style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline'; frame-ancestors 'none'";
	};
	body = index;
}

return _M
