local id = require "util.id";
local http_formdecode = require "net.http".formdecode;
local usermanager = require "core.usermanager";
local modulemanager = require "core.modulemanager";
local nodeprep = require "util.encodings".stringprep.nodeprep;
local st = require "util.stanza";
local url_escape = require "util.http".urlencode;
local render_html_template = require"util.interpolation".new("%b{}", st.xml_escape, {
	urlescape = url_escape;
});
local render_url = require "util.interpolation".new("%b{}", url_escape, {
	urlescape = url_escape;
	noscheme = function (url)
		return (url:gsub("^[^:]+:", ""));
	end;
});

module:depends("register_apps");
local mod_password_policy = module:depends("password_policy");

local site_name = module:get_option_string("site_name", module.host);
local site_apps = module:shared("register_apps/apps");

local webchat_url = module:get_option_string("webchat_url");

-- If not provided, but mod_conversejs is loaded, default to that
if not webchat_url and modulemanager.get_modules_for_host(module.host):contains("conversejs") then
	local conversejs = module:depends("conversejs");
	webchat_url = conversejs.module:http_url();
end

module:depends("http");

local invites = module:depends("invites");
local invites_page = module:depends("invites_page");

local template_path = module:get_option_path("invites_register_template_path", "html");
function serve_register_page(event)
	local register_page_template = assert(module:load_resource(template_path .. "/register.html")):read("*a");

	local query_params = event.request.url.query and http_formdecode(event.request.url.query);

	local invite = query_params and invites.get(query_params.t);
	if not invite then
		return {
			status_code = 303;
			headers = {
				["Location"] = invites_page.module:http_url().."?"..(event.request.url.query or "");
			};
		};
	end

	event.response.headers["Content-Type"] = "text/html; charset=utf-8";

	local invite_page = render_html_template(register_page_template, {
		site_name = site_name;
		token = invite.token;
		domain = module.host;
		uri = invite.uri;
		type = invite.type;
		jid = invite.jid;
		inviter = invite.inviter;
		app = query_params.c and site_apps[query_params.c];
		password_policy = mod_password_policy.get_policy();
	});
	return invite_page;
end

function handle_register_form(event)
	local request, response = event.request, event.response;
	local form_data = http_formdecode(request.body);
	local user, password, token = form_data["user"], form_data["password"], form_data["token"];
	local app_id = form_data["app_id"];

	local register_page_template = assert(module:load_resource(template_path .. "/register.html")):read("*a");
	local error_template = assert(module:load_resource(template_path .. "/register_error.html")):read("*a");

	local invite = invites.get(token);
	if not invite then
		return {
			status_code = 303;
			headers = {
				["Location"] = invites_page.module:http_url().."?"..event.request.url.query;
			};
		};
	end

	event.response.headers["Content-Type"] = "text/html; charset=utf-8";

	if not user or #user == 0 or not password or #password == 0 or not token then
		return render_html_template(register_page_template, {
			site_name = site_name;
			token = invite.token;
			domain = module.host;
			uri = invite.uri;
			type = invite.type;
			jid = invite.jid;
			password_policy = mod_password_policy.get_policy();

			msg_class = "alert-warning";
			message = "Please fill in all fields.";
		});
	end

	-- Shamelessly copied from mod_register_web.
	local prepped_username = nodeprep(user);

	if not prepped_username or #prepped_username == 0 then
		return render_html_template(register_page_template, {
			site_name = site_name;
			token = invite.token;
			domain = module.host;
			uri = invite.uri;
			type = invite.type;
			jid = invite.jid;
			password_policy = mod_password_policy.get_policy();

			msg_class = "alert-warning";
			message = "This username contains invalid characters.";
		});
	end

	if usermanager.user_exists(prepped_username, module.host) then
		return render_html_template(register_page_template, {
			site_name = site_name;
			token = invite.token;
			domain = module.host;
			uri = invite.uri;
			type = invite.type;
			jid = invite.jid;
			password_policy = mod_password_policy.get_policy();

			msg_class = "alert-warning";
			message = "This username is already in use.";
		});
	end

	local pw_ok, pw_error = mod_password_policy.check_password(password, {
		username = prepped_username;
	});
	if not pw_ok then
		return render_html_template(register_page_template, {
			site_name = site_name;
			token = invite.token;
			domain = module.host;
			uri = invite.uri;
			type = invite.type;
			jid = invite.jid;
			password_policy = mod_password_policy.get_policy();

			msg_class = "alert-warning";
			message = pw_error;
		});
	end

	local registering = {
		validated_invite = invite;
		username = prepped_username;
		host = module.host;
		ip = request.ip;
		allowed = true;
	};

	module:fire_event("user-registering", registering);

	if not registering.allowed then
		return render_html_template(error_template, {
			site_name = site_name;
			msg_class = "alert-danger";
			message = registering.reason or "Registration is not allowed.";
		});
	end

	local ok, err = usermanager.create_user(prepped_username, password, module.host);

	if ok then
		module:fire_event("user-registered", {
			username = prepped_username;
			host = module.host;
			source = "mod_"..module.name;
			validated_invite = invite;
			ip = request.ip;
		});

		local app_info = site_apps[app_id];

		local success_template;
		if app_info then
			if app_info.login_link_format then
				local redirect_url = render_url(app_info.login_link_format, {
					site_name = site_name;
					username = prepped_username;
					domain = module.host;
					password = password;
					app = app_info;
				});
				return {
					status_code = 303;
					headers = {
						["Location"] = redirect_url;
					};
				};
			end
			-- If recognised app, we serve a page that includes setup instructions
			success_template = assert(module:load_resource(template_path .. "/register_success_setup.html")):read("*a");
		else
			success_template = assert(module:load_resource(template_path .. "/register_success.html")):read("*a");
		end

		-- Due to the credentials being served here, ensure that
		-- the browser or any intermediary does not cache the page
		event.response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate";
		event.response.headers["Pragma"] = "no-cache";
		event.response.headers["Expires"] = "0";

		return render_html_template(success_template, {
			site_name = site_name;
			username = prepped_username;
			domain = module.host;
			password = password;
			app = app_info;
			webchat_url = webchat_url;
		});
	else
		local err_id = id.short();
		module:log("warn", "Registration failed (%s): %s", err_id, tostring(err));
		return render_html_template(error_template, {
			site_name = site_name;
			msg_class = "alert-danger";
			message = ("An unknown error has occurred (%s)"):format(err_id);
		});
	end
end

module:provides("http", {
	default_path = "register";
	route = {
		["GET"] = serve_register_page;
		["POST"] = handle_register_form;
	};
});
