local st = require "util.stanza";
local url_escape = require "util.http".urlencode;
local render_html_template = require"util.interpolation".new("%b{}", st.xml_escape, {
	urlescape = url_escape;
});
local http_files = require "net.http.files";

local template_path = module:get_option_string("welcome_page_template_path", module:get_directory().."/html");
local user_vars = module:get_option("welcome_page_variables", {});
local site_name = module:get_option("site_name", module.host);
local invite_only = module:get_option_boolean("registration_invite_only", true);
local open_registration = module:get_option_boolean("welcome_page_open_registration", not invite_only);

module:depends("http");
module:depends("http_libjs");
local invites = module:depends("invites");

local function load_template(path)
	local template_file, err = io.open(path);
	if not template_file then
		error("Unable to load template file: "..tostring(err));
	end
	local template = template_file:read("*a");
	template_file:close();
	return template;
end

local template = load_template(template_path.."/index.html");

local function serve_page(event)
	event.response.headers["Content-Type"] = "text/html; charset=utf-8";
	return render_html_template(template, {
		site_name = site_name;
		request = event.request;
		var = user_vars;
	});
end

local function handle_submit(event)
	local submission = { allowed = open_registration, request = event.request };
	module:fire_event("mod_welcome_page/submission", submission);
	if not submission.allowed then
		event.response.headers["Content-Type"] = "text/html; charset=utf-8";
		return render_html_template(template, {
			site_name = site_name;
			request = event.request;
			var = user_vars;
			message = {
				class = "alert-danger";
				text = submission.reason or "Account creation is not possible at this time";
			};
		});
	end

	local invite = invites.create_account(nil, { source = module.name });
	if not invite then
		return 500;
	end

	event.response.headers.Location = invite.landing_page or invite.uri;

	return 303;
end

module:provides("http", {
	default_path = "/";
	route = {
		["GET"] = serve_page;
		["GET /*"] = http_files.serve({ path = template_path });
		["POST"] = handle_submit;
	};
});
