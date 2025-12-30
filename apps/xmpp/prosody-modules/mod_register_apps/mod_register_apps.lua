-- luacheck: ignore 631
module:depends("http");
local http_files = require "net.http.files";

local app_config = module:get_option("site_apps", {
	{
		name = "Conversations";
		text = [[Conversations is a Jabber/XMPP client for Android 6.0+ smartphones that has been optimized to provide a unique mobile experience.]];
		image = "assets/logos/conversations.svg";
		link = "https://play.google.com/store/apps/details?id=eu.siacs.conversations";
		platforms = { "Android" };
		supports_preauth_uri = true;
		magic_link_format = "{app.link!}&referrer={invite.uri}";
		download = {
			buttons = {
				{
					image = "https://play.google.com/intl/en_us/badges/static/images/badges/en_badge_web_generic.png";
					url = "https://play.google.com/store/apps/details?id=eu.siacs.conversations";
				};
			};
		};
	};
	{
		name  = "yaxim";
		text  = [[A lean Jabber/XMPP client for Android. It aims at usability, low overhead and security, and works on low-end Android devices starting with Android 4.0.]];
		image = "assets/logos/yaxim.svg";
		link  = "https://play.google.com/store/apps/details?id=org.yaxim.androidclient";
		platforms = { "Android" };
		supports_preauth_uri = true;
		magic_link_format = "{app.link!}&referrer={invite.uri}";
		download = {
			buttons = {
				{
					image = "https://play.google.com/intl/en_us/badges/static/images/badges/en_badge_web_generic.png";
					url = "https://play.google.com/store/apps/details?id=org.yaxim.androidclient";
				};
			};
		};
	};
	{
		name  = "Siskin IM";
		text  = [[A lightweight and powerful XMPP client for iPhone and iPad. It provides an easy way to talk and share moments with your friends.]];
		image = "assets/logos/siskin-im.png";
		link  = "https://apps.apple.com/us/app/siskin-im/id1153516838";
		platforms = { "iOS" };
		supports_preauth_uri = true;
		download = {
			buttons = {
				{
					image = "https://toolbox.marketingtools.apple.com/api/v2/badges/download-on-the-app-store/black/en-us?releaseDate=1245024000";
					url = "https://apps.apple.com/us/app/siskin-im/id1153516838";
					target = "_blank";
				};
			};
		};
	};
	{
		name  = "Beagle IM";
		text  = [[Beagle IM by Tigase, Inc. is a lightweight and powerful XMPP client for macOS.]];
		image = "assets/logos/beagle-im.png";
		link  = "https://apps.apple.com/us/app/beagle-im/id1445349494";
		platforms = { "macOS" };
		download = {
			buttons = {
				{
					text = "Download from Mac App Store";
					url = "https://apps.apple.com/us/app/beagle-im/id1445349494";
					target = "_blank";
				};
			};
		};
		setup = {
			text = [[Launch Beagle IM, and select 'Yes' to add a new account. Click the '+'
			         button under the empty account list and then enter your credentials.]];
		};
	};
	{
		name  = "Dino";
		text  = [[A modern open-source chat client for the desktop. It focuses on providing a clean and reliable Jabber/XMPP experience while having your privacy in mind.]];
		image = "assets/logos/dino.svg";
		link  = "https://dino.im/";
		platforms = { "Linux" };
		download = {
			text = "Click the button to open the Dino website where you can download and install it on your PC.";
			buttons = {
				{ text = "Download Dino for Linux", url = "https://dino.im/#download", target="_blank" };
			};
		};
	};
	{
		name  = "Gajim";
		text  = [[A fully-featured desktop chat client for Windows and Linux.]];
		image = "assets/logos/gajim.svg";
		link  = "https://gajim.org/";
		platforms = { "Windows", "Linux" };
		download = {
			buttons = {
				{
					text = "Download Gajim";
					url = "https://gajim.org/download/";
					target = "_blank";
				};
			};
		};
	};
	{
		name  = "Monal";
		text  = [[A modern open-source chat client for iPhone and iPad. It is easy to use and has a clean user interface.]];
		image = "assets/logos/monal.svg";
		link  = "https://monal-im.org/";
		platforms = { "iOS" };
		supports_preauth_uri = true;
		download = {
			buttons = {
				{
					image = "https://toolbox.marketingtools.apple.com/api/v2/badges/download-on-the-app-store/black/en-us?releaseDate=1245024000";
					url = "https://apps.apple.com/app/id317711500";
					target = "_blank";
				};
			};
		};
	};
	{
		name  = "Monal";
		text  = [[A modern open-source chat client for Mac. It is easy to use and has a clean user interface.]];
		image = "assets/logos/monal.svg";
		link  = "https://monal-im.org/";
		platforms = { "macOS" };
		supports_preauth_uri = true;
		download = {
			buttons = {
				{
					image = "https://toolbox.marketingtools.apple.com/api/v2/badges/download-on-the-app-store/black/en-us?releaseDate=1245024000";
					url = "https://apps.apple.com/app/id1637078500";
					target = "_blank";
				};
			};
		};
	};
	{
		name  = "Renga";
		text  = [[XMPP client for Haiku]];
		image = "assets/logos/renga.svg";
		link  = "https://pulkomandy.tk/projects/renga";
		platforms = { "Haiku" };
		download = {
			buttons = {
				{ text = "Download Renga for Haiku", url = "https://depot.haiku-os.org/#!/pkg/renga?bcguid=bc233-PQIA", target="_blank" };
			};
		};
	};
});

local show_apps = module:get_option_set("site_apps_show");
local hide_apps = module:get_option_set("site_apps_hide");

local base_url = module.http_url and module:http_url();
local function relurl(s)
	if s:match("^%w+://") then
		return s;
	end
	return base_url.."/"..s;
end

local site_apps = module:shared("apps");

local function add_app(app_info, source)
	local app_id = app_info.id or app_info.name:gsub("%W+", "-"):lower();
	if (not show_apps or show_apps:contains(app_id))
	and not (hide_apps and hide_apps:contains(app_id))
	and not site_apps[app_id] then
		app_info.id = app_id;
		app_info.image = relurl(app_info.image);
		site_apps[app_id] = app_info;
		app_info._source = source;
		table.insert(site_apps, app_info);
	end
end

local function remove_app(app_info)
	local app_id = app_info.id or app_info.name:gsub("%W+", "-"):lower();
	for i = #site_apps, 1, -1 do
		if site_apps[i].id == app_id then
			table.remove(site_apps, i);
		end
	end
	site_apps[app_id] = nil;
end

local function add_config_apps()
	for _, app_info in ipairs(app_config) do
		add_app(app_info, module.name);
	end
end

local function module_app_added(event)
	module:log("info", "Adding %s", event.item.name)
	add_app(event.item, module.name);
end

local function module_app_removed(event)
	remove_app(event.item);
end

-- Remove all apps added by this module
local function remove_all_apps()
	for k, v in pairs(site_apps) do
		if v._source == module.name then
			remove_app(v);
		end
	end
end

local mime_map = {
	png = "image/png";
	svg = "image/svg+xml";
};

module:provides("http", {
	route = {
		["GET /assets/*"] = http_files.serve({
			path = module:get_directory().."/assets";
			mime_map = mime_map;
		});
	};
});

function module.load()
	add_config_apps();
	module:handle_items("site-app-provider", module_app_added, module_app_removed, true);
end

function module.unload()
	remove_all_apps();
end

