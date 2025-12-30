-- mod_jsxc
-- Copyright (C) 2021 Kim Alvefur

local json_encode = require"util.json".encode;
local xml_escape = require "util.stanza".xml_escape;
local render = require "util.interpolation".new("%b{}", xml_escape, { json = json_encode });

module:depends"http";
module:depends"bosh";
module:depends"http_libjs";

local jquery_url = module:get_option_string("jquery_url", "/share/jquery/jquery.min.js");

local cdn_url = module:get_option_string("jsxc_cdn", "");

local version = module:get_option_string("jsxc_version", "");
if version ~= "" then version = "/" .. version end

local serve_dist = nil;
local resources = module:get_option_path("jsxc_resources");
if resources then
	local http_files = require "net.http.files";
	local mime_map = module:shared("/*/http_files/mime").types or { css = "text/css", js = "application/javascript" };
	serve_dist = http_files.serve({ path = resources, mime_map = mime_map });

	cdn_url = module:http_url();
end

local js_url = module:get_option_string("jsxc_script", cdn_url..version.."/dist/jsxc.bundle.js");
local css_url = module:get_option_string("jsxc_css", cdn_url..version.."/dist/styles/jsxc.bundle.css");

local html_template;

do
	local template_filename = module:get_option_string(module.name .. "_html_template", "templates/template.html");
	local template_file, err = module:load_resource(template_filename);
	if template_file then
		html_template, err = template_file:read("*a");
		template_file:close();
	end
	if not html_template then
		module:log("error", "Error loading HTML template: %s", err);
		html_template = render("<h1>mod_{module} could not read the template</h1>\
		<p>Tried to open <b>{filename}</b></p>\
		<pre>{error}</pre>",
			{ module = module.name, filename = template_filename, error = err });
	end
end

local js_template;
do
	local template_filename = module:get_option_string(module.name .. "_js_template", "templates/template.js");
	local template_file, err = module:load_resource(template_filename);
	if template_file then
		js_template, err = template_file:read("*a");
		template_file:close();
	end
	if not js_template then
		module:log("error", "Error loading JS template: %s", err);
		js_template = render("console.log(\"mod_{module} could not read the JS template: %s\", {error|json})",
			{ module = module.name, filename = template_filename, error = err });
	end
end

local function get_jsxc_options()
	return { xmpp = { url = module:http_url("bosh", "/http-bind"), domain = module.host } };
end

local add_tags = module:get_option_array("jsxc_tags", {});

module:provides("http", {
	title = "jsxc.js";
	route = {
		GET = function (event)
			local jsxc_options = get_jsxc_options();

			event.response.headers.content_type = "text/html";
			return render(html_template, {
					service_name = module:get_option_string("name");
					header_scripts = { jquery_url, js_url };
					header_style = { css_url };
					header_tags = add_tags;
					jsxcjs = {
						options = jsxc_options;
						startup = { script = js_template:format(json_encode(jsxc_options)); }
					};
				});
		end;

		["GET /prosody-jsxc.js"] = function (event)
			local jsxc_options = get_jsxc_options();

			event.response.headers.content_type = "application/javascript";
			return js_template:format(json_encode(jsxc_options));
		end;
		["GET /dist/*"] = serve_dist;
	}
});

