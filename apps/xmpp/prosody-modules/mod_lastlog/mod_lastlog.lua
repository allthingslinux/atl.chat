local datamanager = require "util.datamanager";
local jid = require "util.jid";
local time = os.time;
local log_ip = module:get_option_boolean("lastlog_ip_address", false);
local host = module.host;

module:hook("authentication-success", function(event)
	local session = event.session;
	if session.username then
		datamanager.store(session.username, host, "lastlog", {
			event = "login";
			timestamp = time(),
			ip = log_ip and session and session.ip or nil,
		});
	end
end);

module:hook("resource-unbind", function(event)
	local session = event.session;
	if session.username then
		datamanager.store(session.username, host, "lastlog", {
			event = "logout";
			timestamp = time(),
			ip = log_ip and session and session.ip or nil,
		});
	end
end);

module:hook("user-registered", function(event)
	local session = event.session;
	datamanager.store(event.username, host, "lastlog", {
		event = "registered";
		timestamp = time(),
		ip = log_ip and session and session.ip or nil,
	});
end);


if module:get_host_type() == "component" then
	module:hook("message/bare", function(event)
		local room = jid.split(event.stanza.attr.to);
		if room then
			datamanager.store(room, module.host, "lastlog", {
				event = "message";
				timestamp = time(),
			});
		end
	end);

elseif module:get_option_boolean("lastlog_stamp_offline") then
	local datetime = require"util.datetime".datetime;
	local function offline_stamp(event)
		local stanza = event.stanza;
		local node, to_host = jid.split(stanza.attr.from);
		if to_host == host and event.origin == hosts[host] and stanza.attr.type == "unavailable" then
			local data = datamanager.load(node, host, "lastlog");
			local timestamp = data and data.timestamp;
			if timestamp then
				stanza:tag("delay", {
					xmlns = "urn:xmpp:delay",
					from = host,
					stamp = datetime(timestamp),
				}):up();
			end
		end
	end

	module:hook("pre-presence/bare", offline_stamp);
	module:hook("pre-presence/full", offline_stamp);
end

function module.command(arg)
	if not arg[1] or arg[1] == "--help" then
		require"util.prosodyctl".show_usage([[mod_lastlog <user@host>]], [[Show when user last logged in or out]]);
		return 1;
	end
	local user, host = jid.prepped_split(table.remove(arg, 1));
	require"core.storagemanager".initialize_host(host);
	local lastlog = datamanager.load(user, host, "lastlog");
	if lastlog then
		print(("Last %s: %s"):format(lastlog.event or "login",
		lastlog.timestamp and os.date("%Y-%m-%d %H:%M:%S", lastlog.timestamp) or "<unknown>"));
		if lastlog.ip then
			print("IP address: "..lastlog.ip);
		end
	else
		print("No record found");
		return 1;
	end
	return 0;
end
