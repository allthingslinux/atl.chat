module:set_global();

local time_now = os.time;
local ip = require "util.ip";
local st = require "util.stanza";
local moduleapi = require "core.moduleapi";

local host_wide_user = "@";

local cleanup_after = module:get_option_period("audit_log_expires_after", "28d");

local attach_ips = module:get_option_boolean("audit_log_ips", true);
local attach_ipv4_prefix = module:get_option_number("audit_log_ipv4_prefix", nil);
local attach_ipv6_prefix = module:get_option_number("audit_log_ipv6_prefix", nil);

local have_geoip, geoip = pcall(require, "geoip.country");
local attach_location = have_geoip and module:get_option_boolean("audit_log_location", true);

local geoip4_country, geoip6_country;
if have_geoip and attach_location then
	geoip4_country = geoip.open(module:get_option_string("geoip_ipv4_country", "/usr/share/GeoIP/GeoIP.dat"));
	geoip6_country = geoip.open(module:get_option_string("geoip_ipv6_country", "/usr/share/GeoIP/GeoIPv6.dat"));
end


local stores = {};

local function get_store(self, host)
	local store = rawget(self, host);
	if store then
		return store
	end
	store = module:context(host):open_store("audit", "archive");
	rawset(self, host, store);
	return store;
end

setmetatable(stores, { __index = get_store });

local function prune_audit_log(host)
	local before = os.time() - cleanup_after;
	module:context(host):log("debug", "Pruning audit log for entries older than %s", os.date("%Y-%m-%d %R:%S", before));
	local ok, err = stores[host]:delete(nil, { ["end"] = before });
	if not ok then
		module:context(host):log("error", "Unable to prune audit log: %s", err);
		return;
	end
	local sum = tonumber(ok);
	if sum then
		module:context(host):log("debug", "Pruned %d expired audit log entries", sum);
		return sum > 0;
	end
	module:context(host):log("debug", "Pruned expired audit log entries");
	return true;
end

local function get_ip_network(ip_addr)
	local proto = ip_addr.proto;
	local network;
	if proto == "IPv4" and attach_ipv4_prefix then
		network = ip.truncate(ip_addr, attach_ipv4_prefix).normal.."/"..attach_ipv4_prefix;
	elseif proto == "IPv6" and attach_ipv6_prefix then
		network = ip.truncate(ip_addr, attach_ipv6_prefix).normal.."/"..attach_ipv6_prefix;
	end
	return network;
end

local function session_extra(session)
	local attr = {
		xmlns = "xmpp:prosody.im/audit",
	};
	if session.id then
		attr.id = session.id;
	end
	if session.type then
		attr.type = session.type;
	end
	local stanza = st.stanza("session", attr);
	local remote_ip = session.ip and ip.new_ip(session.ip);
	if attach_ips and remote_ip then
		local network;
		if attach_ipv4_prefix or attach_ipv6_prefix then
			network = get_ip_network(remote_ip);
		end
		stanza:text_tag("remote-ip", network or remote_ip.normal);
	end
	if attach_location and remote_ip then
		local geoip_info = remote_ip.proto == "IPv6" and geoip6_country:query_by_addr6(remote_ip.normal) or geoip4_country:query_by_addr(remote_ip.normal);
		stanza:text_tag("location", geoip_info.name, {
			country = geoip_info.code;
			continent = geoip_info.continent;
		}):up();
	end
	if session.client_id then
		stanza:text_tag("client", session.client_id);
	end
	return stanza
end

local function audit(host, user, source, event_type, extra)
	if not host or host == "*" then
		error("cannot log audit events for global");
	end
	local user_key = user or host_wide_user;

	local attr = {
		["source"] = source,
		["type"] = event_type,
	};
	if user_key ~= host_wide_user then
		attr.user = user_key;
	end
	local stanza = st.stanza("audit-event", attr);
	if extra then
		if extra.session then
			local child = session_extra(extra.session);
			if child then
				stanza:add_child(child);
			end
		end
		if extra.custom then
			for _, child in ipairs(extra.custom) do
				if not st.is_stanza(child) then
					error("all extra.custom items must be stanzas")
				end
				stanza:add_child(child);
			end
		end
	end

	local store = stores[host];
	local id, err = store:append(nil, nil, stanza, extra and extra.timestamp or time_now(), user_key);
	if not id then
		if err == "quota-limit" then
			local limit = store.caps and store.caps.quota or 1000;
			local truncate_to = math.floor(limit * 0.99);
			if cleanup_after ~= math.huge then
				module:log("debug", "Audit log has reached quota - forcing prune");
				if prune_audit_log(host) then
					-- Retry append
					id, err = store:append(nil, nil, stanza, extra and extra.timestamp or time_now(), user_key);
				end
			end
			if not id and (store.caps and store.caps.truncate) then
				module:log("debug", "Audit log has reached quota - truncating");
				local truncated = store:delete(nil, {
					truncate = truncate_to;
				});
				if truncated then
					-- Retry append
					id, err = store:append(nil, nil, stanza, extra and extra.timestamp or time_now(), user_key);
				end
			end
		end
		if not id then
			module:log("error", "Failed to persist audit event: %s", err);
			return;
		end
	else
		module:log("debug", "Persisted audit event %s as %s", stanza:top_tag(), id);
	end
end

function moduleapi.audit(module, user, event_type, extra)
	audit(module.host, user, "mod_" .. module:get_name(), event_type, extra);
end

function module.command(arg_)
	local jid = require "util.jid";
	local arg = require "util.argparse".parse(arg_, {
		value_params = { limit = true };
	});

	module:log("debug", "arg = %q", arg);
	local query_jid = jid.prep(arg[1]);
	local host = jid.host(query_jid);

	if arg.prune then
		local sm = require "core.storagemanager";
		if host then
			sm.initialize_host(host);
			prune_audit_log(host);
		else
			for _host in pairs(prosody.hosts) do
				sm.initialize_host(_host);
				prune_audit_log(_host);
			end
		end
		return;
	end

	if not host then
		print("EE: Please supply the host for which you want to show events");
		return 1;
	elseif not prosody.hosts[host] then
		print("EE: Unknown host: "..host);
		return 1;
	end

	require "core.storagemanager".initialize_host(host);
	local store = stores[host];
	local c = 0;

	if arg.global then
		if jid.node(query_jid) then
			print("WW: Specifying a user account is incompatible with --global. Showing only global events.");
		end
		query_jid = "@";
	elseif host == query_jid then
		query_jid = nil;
	end

	local results, err = store:find(nil, {
		with = query_jid;
		limit = arg.limit and tonumber(arg.limit) or nil;
		reverse = true;
	})
	if not results then
		print("EE: Failed to query audit log: "..tostring(err));
		return 1;
	end

	local colspec = {
		{ title = "Date", key = "when", width = 19, mapper = function (when) return os.date("%Y-%m-%d %R:%S", math.floor(when)); end };
		{ title = "Source", key = "source", width = "2p" };
		{ title = "Event", key = "event_type", width = "2p" };
	};

	if arg.show_user ~= false and (not arg.global and not query_jid) or arg.show_user then
		table.insert(colspec, {
			title = "User", key = "username", width = "2p",
			mapper = function (user)
				if user == "@" then return ""; end
				if user:sub(-#host-1, -1) == ("@"..host) then
					return (user:gsub("@.+$", ""));
				end
			end;
		});
	end
	if arg.show_ip ~= false and (not arg.global and attach_ips) or arg.show_ip then
		table.insert(colspec, {
			title = "IP", key = "ip", width = "2p";
		});
	end
	if arg.show_location ~= false and (not arg.global and attach_location) or arg.show_location then
		table.insert(colspec, {
			title = "Location", key = "country", width = 2;
		});
	end

	if arg.show_note then
		table.insert(colspec, {
			title = "Note", key = "note", width = "2p";
		});
	end

	local row, width = require "util.human.io".table(colspec);

	print(string.rep("-", width));
	print(row());
	print(string.rep("-", width));
	for _, entry, when, user in results do
		if arg.global ~= false or user ~= "@" then
			c = c + 1;
			print(row({
				when = when;
				source = entry.attr.source;
				event_type = entry.attr.type:gsub("%-", " ");
				username = user;
				ip = entry:find("{xmpp:prosody.im/audit}session/remote-ip#");
				country = entry:find("{xmpp:prosody.im/audit}session/location@country");
				note = entry:get_child_text("note");
			}));
		end
	end
	print(string.rep("-", width));
	print(("%d records displayed"):format(c));
end

function module.add_host(host_module)
	host_module:depends("cron");
	host_module:daily("Prune audit logs", function ()
		prune_audit_log(host_module.host);
	end);
end
