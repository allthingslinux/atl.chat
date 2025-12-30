local st = require "util.stanza";
local url_escape = require "util.http".urlencode;

local base_url = "https://"..module.host.."/";

local render_html_template = require"util.interpolation".new("%b{}", st.xml_escape, {
	urlescape = url_escape;
	lower = string.lower;
	classname = function (s) return (s:gsub("%W+", "-")); end;
	relurl = function (s)
		if s:match("^%w+://") then
			return s;
		end
		return base_url.."/"..s;
	end;
});
local render_url = require "util.interpolation".new("%b{}", url_escape, {
	urlescape = url_escape;
	noscheme = function (url)
		return (url:gsub("^[^:]+:", ""));
	end;
});

local site_name = module:get_option_string("site_name", module.host);
local site_apps;

-- Enable/disable built-in invite pages
local external_only = module:get_option_boolean("invites_page_external", false);

local http_files;

if not external_only then
	-- Load HTTP-serving dependencies
	if prosody.shutdown then -- not if running under prosodyctl
		module:depends("http");
		http_files = require "net.http.files";
	elseif prosody.process_type and module.get_option_period then
		module:depends("http");
		http_files = require "net.http.files";
	end
	-- Calculate automatic base_url default
	base_url = module.http_url and module:http_url();

	-- Load site apps info
	module:depends("register_apps");
	site_apps = module:shared("register_apps/apps");
end

local invites = module:depends("invites");

-- Point at eg https://github.com/ge0rg/easy-xmpp-invitation
-- This URL must always be absolute, as it is shared standalone
local invite_url_template = module:get_option_string("invites_page", base_url and (base_url.."?{invite.token}") or nil);
-- This URL is relative to the invite page, or can be absolute
local register_url_template = module:get_option_string("invites_registration_page", "register?t={invite.token}&c={app.id}");

local function add_landing_url(invite)
	if not invite_url_template then return; end
	-- TODO: we don't currently have a landing page for subscription-only invites,
	-- so the user will only receive a URI. The client should be able to handle this
	-- by automatically falling back to a client-specific landing page, per XEP-0401.
	if not invite.allow_registration then return; end
	-- password reset invites are not currently supported
	if invite.additional_data and invite.additional_data.allow_reset then return end
	invite.landing_page = render_url(invite_url_template, { host = module.host, invite = invite });
end

module:hook("invite-created", add_landing_url);

if external_only then
	return;
end

local function render_app_urls(apps, invite_vars)
	local rendered_apps = {};
	for _, unrendered_app in ipairs(apps) do
		local app = setmetatable({}, { __index = unrendered_app });
		local template_vars = { app = app, invite = invite_vars, base_url = base_url };
		if app.magic_link_format then
			-- Magic link generally links directly to third-party
			app.proceed_url = render_url(app.magic_link_format or app.link or "#", template_vars);
		elseif app.supports_preauth_uri then
			-- Proceed to a page that guides the user to download, and then
			-- click the URI button
			app.proceed_url = render_url("{base_url!}/setup/{app.id}?{invite.token}", template_vars);
		else
			-- Manual means proceed to web registration, but include app id
			-- so it can show post-registration instructions
			app.proceed_url = render_url(register_url_template, template_vars);
		end
		table.insert(rendered_apps, app);
	end
	return rendered_apps;
end

function serve_invite_page(event)
	local invite_page_template = assert(module:load_resource("html/invite.html")):read("*a");
	local invalid_invite_page_template = assert(module:load_resource("html/invite_invalid.html")):read("*a");

	event.response.headers["Content-Type"] = "text/html; charset=utf-8";

	local invite = invites.get(event.request.url.query);
	if not invite then
		return render_html_template(invalid_invite_page_template, {
			site_name = site_name;
			static = base_url.."/static";
		});
	end

	local template_vars = {
		site_name = site_name;
		token = invite.token;
		uri = invite.uri;
		type = invite.type;
		jid = invite.jid;
		inviter = invite.inviter;
		static = base_url.."/static";
	};
	template_vars.apps = render_app_urls(site_apps, template_vars);

	local invite_page = render_html_template(invite_page_template, template_vars);

	event.response.headers["Link"] = ([[<%s>; rel="alternate"]]):format(template_vars.uri);
	return invite_page;
end

function serve_setup_page(event, app_id)
	local invite_page_template = assert(module:load_resource("html/client.html")):read("*a");
	local invalid_invite_page_template = assert(module:load_resource("html/invite_invalid.html")):read("*a");

	event.response.headers["Content-Type"] = "text/html; charset=utf-8";

	local invite = invites.get(event.request.url.query);
	if not invite then
		return render_html_template(invalid_invite_page_template, {
			site_name = site_name;
			static = base_url.."/static";
		});
	end

	local template_vars = {
		site_name = site_name;
		apps = site_apps;
		token = invite.token;
		uri = invite.uri;
		type = invite.type;
		jid = invite.jid;
		static = base_url.."/static";
	};
	template_vars.app = render_app_urls({ site_apps[app_id] }, template_vars)[1];

	local invite_page = render_html_template(invite_page_template, template_vars);
	return invite_page;
end

local mime_map = {
	png = "image/png";
	svg = "image/svg+xml";
	js  = "application/javascript";
};

module:provides("http", {
	route = {
		["GET"] = serve_invite_page;
		["GET /setup/*"] = serve_setup_page;
		["GET /static/*"] = http_files and http_files.serve({ path = module:get_directory().."/static", mime_map = mime_map });
	};
});
