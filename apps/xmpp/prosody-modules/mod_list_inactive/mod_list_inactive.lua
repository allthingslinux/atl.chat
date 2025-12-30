-- Copyright (C) 2012-2013 Kim Alvefur

local um = require "core.usermanager";
local sm = require "core.storagemanager";
local dm_load = require "util.datamanager".load;
local jid_join = require"util.jid".join;

local multipliers = {
	d = 86400, -- day
	w = 604800, -- week
	m = 2629746, -- month
	y = 31556952, -- year
}

local output_formats = {
	default = "%s",
	event = "%s %s %s",
	delete = "user:delete%q -- %s -- %s"
}

function module.command(arg)
	if #arg < 2 then
		print("usage: prosodyctl mod_list_inactive example.net time [format]");
		print("time is a number followed by 'day', 'week', 'month' or 'year'");
		print("formats are:");
		for name, fmt in pairs(output_formats) do
			print(name, fmt:format("user@example.com", "<last action>", "<last action timestamp>"))
		end
		return;
	end
	local items = {};
	local host = arg[1];
	assert(hosts[host], "Host "..tostring(host).." does not exist");
	sm.initialize_host(host);
	um.initialize_host(host);

	local max_age, unit = assert(arg[2], "No time range given"):match("^(%d*)%s*([dwmy]?)");
	max_age = os.time() - ( tonumber(max_age) or 1 ) * ( multipliers[unit] or 1 );

	local output = assert(output_formats[arg[3] or "default"], "No such output format: "..tostring(arg[3] or "default"));

	for user in um.users(host) do
		local last_active = dm_load(user, host, "lastlog");
		local last_action = last_active and last_active.event or "?"
		last_active = last_active and last_active.timestamp or 0;
		if last_active < max_age then
			print(output:format(jid_join(user, host), last_action, os.date('%Y-%m-%d %H:%M:%S', last_active)));
		end
	end
end

