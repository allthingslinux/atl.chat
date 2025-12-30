-- mod_conversejs
-- Copyright (C) 2017-2022 Kim Alvefur

local json_encode = require"util.json".encode;
local xml_escape = require "util.stanza".xml_escape;
local urlencode = require "util.http".urlencode;
local render = require "util.interpolation".new("%b{}", xml_escape, { json = json_encode });

module:depends"http";

local has_bosh = pcall(function ()
	module:depends"bosh";
end);

local has_ws = pcall(function ()
	module:depends("websocket");
end);

pcall(function ()
	module:depends("bookmarks");
end);

local cdn_url = module:get_option_string("conversejs_cdn", "https://cdn.conversejs.org");

local version = module:get_option_string("conversejs_version", "");
if version ~= "" then version = "/" .. version end

local serve_dist = nil;
local resources = module:get_option_path("conversejs_resources");
if resources then
	local http_files = require "net.http.files";
	local mime_map = module:shared("/*/http_files/mime").types or {css = "text/css"; js = "application/javascript"};
	serve_dist = http_files.serve({path = resources; mime_map = mime_map});

	cdn_url = module:http_url();
end

local js_url = module:get_option_string("conversejs_script", cdn_url..version.."/dist/converse.min.js");
local css_url = module:get_option_string("conversejs_css", cdn_url..version.."/dist/converse.min.css");

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

local function get_converse_options()
	local user_options = module:get_option("conversejs_options");

	local authentication = module:get_option_string("authentication");
	local allow_registration = module:get_option_boolean("allow_registration", false);
	local converse_options = {
		-- Auto-detected connection endpoints
		bosh_service_url = has_bosh and module:http_url("bosh","/http-bind") or nil;
		websocket_url = has_ws and module:http_url("websocket","xmpp-websocket"):gsub("^http", "ws") or nil;
		-- Since we provide those, XEP-0156 based auto-discovery should not be used
		discover_connection_methods = false;
		-- Authentication mode to use (normal or guest login)
		authentication = authentication == "anonymous" and "anonymous" or "login";
		-- Host to connect to for anonymous access
		jid = authentication == "anonymous" and module.host or nil;
		-- Let users login with only username
		default_domain = module.host;
		domain_placeholder = module.host;
		-- If registration is enabled
		allow_registration = allow_registration;
		-- and if it is, which domain to register with
		registration_domain = allow_registration and module.host or nil;
		-- Path to resources like emoji, icons, sounds
		assets_path = cdn_url..version.."/dist/";
		-- Default most suited for use as a "normal" client
		view_mode = "fullscreen";
	};

	-- Let config override the above defaults
	if type(user_options) == "table" then
		for k,v in pairs(user_options) do
			converse_options[k] = v;
		end
	end

	return converse_options;
end

local add_tags = module:get_option_array("conversejs_tags", {});

local service_name = module:get_option_string("conversejs_name", module:get_option_string("name", "Prosody IM and Converse.js"));
local service_short_name = module:get_option_string("conversejs_short_name", "Converse");
local service_description = module:get_option_string("conversejs_description", "Messaging Freedom")
local pwa_color = module:get_option_string("conversejs_pwa_color", "#397491")

module:provides("http", {
	title = "Converse.js";
	route = {
		["GET /"] = function (event)
			local converse_options = get_converse_options();

			event.response.headers.content_type = "text/html";
			return render(html_template, {
					service_name = service_name;
					-- note that using a relative path won’t work as this URL doesn’t end in a /
					manifest_url = module:http_url().."/manifest.json",
					header_scripts = { js_url };
					header_style = { css_url };
					header_tags = add_tags;
					conversejs = {
						options = converse_options;
						startup = { script = js_template:format(json_encode(converse_options)); }
					};
				});
		end;

		["GET /prosody-converse.js"] = function (event)
			local converse_options = get_converse_options();

			event.response.headers.content_type = "application/javascript";
			return js_template:format(json_encode(converse_options));
		end;
		["GET /manifest.json"] = function (event)
			-- See manifest.json in the root of Converse.js’s git repository
			local data = {
				short_name = service_short_name,
				name = service_name,
				description = service_description,
				categories = {"social"},
				icons = module:get_option_array("manifest_icons", {
					{
						src = cdn_url..version.."/dist/images/logo/conversejs-filled-512.png",
						sizes = "512x512",
					},
					{
						src = cdn_url..version.."/dist/images/logo/conversejs-filled-192.png",
						sizes = "192x192",
					},
					{
						src = cdn_url..version.."/dist/images/logo/conversejs-filled-192.svg",
						sizes = "192x192",
					},
					{
						src = cdn_url..version.."/dist/images/logo/conversejs-filled-512.svg",
						sizes = "512x512",
					},
				}),
				start_url = module:http_url().."/",
				background_color = pwa_color,
				display = "standalone",
				scope = module:http_url().."/",
				theme_color = pwa_color,
			}
			return {
				headers = { content_type = "application/schema+json" },
				body = json_encode(data),
			}
		end;
		["GET /dist/*"] = serve_dist;
	}
});

module:provides("site-app", {
	name = "Converse.js";
	text = [[A free and open-source XMPP chat client in your browser]];
	image = "assets/logos/converse-js.svg";
	link = "https://conversejs.org/";
	magic_link_format = "/register?t={invite.token}&c=converse-js";
	login_link_format = module:http_url();
	platforms = { "Web" };
	download = {
		buttons = {
			{
				text = "Open web chat";
				url = module:http_url();
			};
		};
	};

});
