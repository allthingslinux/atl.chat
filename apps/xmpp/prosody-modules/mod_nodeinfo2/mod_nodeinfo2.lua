local json = require "util.json";
local array = require "util.array";
local add_task = require "util.timer".add_task;
local get_stats = require "core.statsmanager".get_stats;
local list_users = require "core.usermanager".users;
local os_time = os.time;

assert(get_stats, "not compatible with trunk based on openmetrics");

module:depends("http");

local expose_users = module:get_option_boolean("nodeinfo2_expose_users", true);
if expose_users then
	module:depends("lastlog");
end

local expose_posts = module:get_option_boolean("nodeinfo2_expose_posts", true);
if expose_posts then
	module:depends("measure_message_e2ee");
end

local main_store = module:open_store();
local lastlog_store = module:open_store("lastlog");

local data;
if expose_posts then
	data = main_store:get("nodeinfo2") or { message_count = 0 };
end

local total_users = 0;
local week_users = 0;
local month_users = 0;
local half_year_users = 0;

local function update_user_list()
	for user in list_users(module.host) do
		total_users = total_users + 1;
		local lastlog = lastlog_store:get(user);
		if lastlog and lastlog.timestamp then
			local delta = os_time() - lastlog.timestamp;
			if delta < 7 * 86400 then
				week_users = week_users + 1;
			end
			if delta < 30 * 86400 then
				month_users = month_users + 1;
			end
			if delta < 6 * 30 * 86400 then
				half_year_users = half_year_users + 1;
			end
		end
	end

	-- Remove the properties if we couldn’t find a single active user.  It most likely means mod_lastlog isn’t in use.
	if half_year_users == 0 and month_users == 0 and week_users == 0 then
		week_users = nil;
		month_users = nil;
		half_year_users = nil;
	end
end

if expose_users then
	add_task(86400, update_user_list);
	update_user_list();
end

module:provides("http", {
	default_path = "/.well-known/x-nodeinfo2";
	route = {
		GET = function (event)
			local usage = {};
			if expose_users then
				usage.users = {
					total = total_users;
					activeWeek = week_users;
					activeMonth = month_users;
					activeHalfyear = half_year_users;
				};
			end

			if expose_posts then
				local stats, changed_only, extras = get_stats();
				for stat, _ in pairs(stats) do
					if stat == "/"..module.host.."/mod_measure_message_e2ee/message:rate" then
						local new_message_count = extras[stat].total;
						if new_message_count ~= data.message_count then
							data = { message_count = new_message_count };
							main_store:set("nodeinfo2", data);
						end
					end
				end
				usage.localPosts = data.message_count;
				-- TODO: also count PubSub replies here.
				usage.localComments = 0;
			end

			event.response.headers.content_type = "application/json";
			return json.encode({
				version = "1.0";
				server = {
					baseUrl = module:http_url("","/");
					name = module.host;
					software = "Prosody";
					version = prosody.version;
				};
				--[[ TODO re-use data from mod_server_contact_info ?
				organization = {
					name = "";
					contact = "";
					account = "";
				};
				--]]
				protocols = array {
					"xmpp",
				};
				services = {
					inbound = array {
						"xmpp";
					};
					outbound = array {
						"xmpp";
					};
				};
				openRegistrations = module:get_option_boolean("allow_registration", false);
				usage = usage;
			});
		end;
	}
});

