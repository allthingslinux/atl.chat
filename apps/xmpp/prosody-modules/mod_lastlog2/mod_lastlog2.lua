local jid = require "util.jid";
local time = os.time;
local log_ip = module:get_option_boolean("lastlog_ip_address", false);

local store;
if module.host ~= "*" then -- workaround for prosodyctl loading into global context
	store = module:open_store(nil, "map");
end

module:hook("authentication-success", function(event)
	local session = event.session;
	if session.username then
		store:set(session.username, "login", {
			timestamp = time(),
			ip = log_ip and session and session.ip or nil,
		});
	end
end);

module:hook("resource-unbind", function(event)
	local session = event.session;
	if session.username then
		store:set(session.username, "logout", {
			timestamp = time(),
			ip = log_ip and session and session.ip or nil,
		});
	end
end);

module:hook("user-registered", function(event)
	local session = event.session;
	store:set(event.username, "registered", {
		timestamp = time(),
		ip = log_ip and session and session.ip or nil,
	});
end);


if module:get_host_type() == "component" then
	module:hook("message/bare", function(event)
		local room = jid.split(event.stanza.attr.to);
		if room then
			store:set(room, module.host, "message", {
				timestamp = time(),
			});
		end
	end);
end

if module.host ~= "*" then
	local user_sessions = prosody.hosts[module.host].sessions;
	local kv_store = module:open_store();
	function get_last_active(username) --luacheck: ignore 131/get_last_active
		if user_sessions[username] then
			return os.time(); -- Currently connected
		else
			local last_activity = kv_store:get(username);
			if not last_activity then return nil; end
			local last_login = last_activity.login;
			local last_logout = last_activity.logout;
			local latest = math.max(last_login and last_login.timestamp or 0, last_logout and last_logout.timestamp or 0);
			if latest == 0 then
				return nil; -- Never logged in
			end
			return latest;
		end
	end
end

module:add_item("shell-command", {
	section = "lastlog";
	section_desc = "View and manage user activity data";
	name = "show";
	desc = "View recorded user activity for user";
	args = { { name = "jid"; type = "string" } };
	host_selector = "jid";
	handler = function(self, userjid)
		local kv_store = module:open_store();
		local username = jid.prepped_split(userjid);
		local lastlog, err = kv_store:get(username);
		if err then return false, err; end
		if not lastlog then return true, "No record found"; end
		local print = self.session.print;
		for event, data in pairs(lastlog) do
			print(("Last %s: %s"):format(event,
				data.timestamp and os.date("%Y-%m-%d %H:%M:%S", data.timestamp) or "<unknown>"));
			if data.ip then
				print("IP address: "..data.ip);
			end
		end
		return true, "Record shown"
	end;
});

function module.command(arg)
	if not arg[1] or arg[1] == "--help" then
		require"util.prosodyctl".show_usage([[mod_lastlog2 <user@host>]], [[Show when user last logged in or out]]);
		return 1;
	end
	local user, host = jid.prepped_split(table.remove(arg, 1));
	require"core.storagemanager".initialize_host(host);
	store = module:context(host):open_store();
	local lastlog = store:get(user);
	if lastlog then
		for event, data in pairs(lastlog) do
			print(("Last %s: %s"):format(event,
				data.timestamp and os.date("%Y-%m-%d %H:%M:%S", data.timestamp) or "<unknown>"));
			if data.ip then
				print("IP address: "..data.ip);
			end
		end
	else
		print("No record found");
		return 1;
	end
	return 0;
end
