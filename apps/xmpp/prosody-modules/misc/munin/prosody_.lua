#!/usr/bin/env lua

-- Script for use with mod_statistics
-- Create symlinks to this named eg prosody_c2s in /etc/munin/plugins

local print = print;
local pairs = pairs;
local socket = require"socket";

local stats = {};

stats.c2s = {
	graph_title = "Prosody C2S Connections";
	graph_vlabel = "users";
	graph_category = "Prosody";
	all_client_connections = {
		label = "client connections";
		_key = "total_c2s";
	}
}

stats.s2s = {
	graph_title = "Prosody S2S Connections";
	graph_vlabel = "servers";
	graph_category = "Prosody";
	outgoing_connections = {
		label = "outgoing connections";
		_key = "total_s2sout";
	};
	incoming_connections = {
		label = "incoming connections";
		_key = "total_s2sin";
	};
	total_connections = {
		label = "total connections";
		_key = "total_s2s";
	};
}

stats.mem = {
	graph_title = "Prosody Memory Usage";
	graph_vlabel = "Bytes";
	graph_args = "--base 1024 -l 0";
	graph_category = "Prosody"; --memory_unused
	graph_order = "memory_total memory_rss memory_allocated memory_used memory_lua memory_returnable";

	memory_allocated = { label = "Allocated", draw = "AREA"  };
	memory_lua = { label = "Lua", draw = "AREA" };
	memory_rss = { label = "RSS", draw = "AREA" };
	memory_total = { label = "Total", draw = "AREA" };
	-- memory_unused = { label = "Unused", draw = "AREA" };
	memory_used = { label = "Used", draw = "AREA" };
	memory_returnable = { label = "Returnable", draw = "AREA" };
}

stats.cpu = {
	graph_title = "Prosody CPU Usage";
	graph_category = "Prosody";
	graph_args = "-l 0";
	graph_vlabel = "CPU time used in milliseconds";

	cpu_total = { label = "CPU"; type = "DERIVE"; min = 0; };
}

stats.auth = {
	graph_title = "Prosody Authentications";
	graph_category = "Prosody";
	graph_args = "--base 1000";

	c2s_auth = {
		label = "Logins";
		type = "DERIVE";
		min = 0;
	};
	c2s_authfail = {
		label = "Failed logins";
		type = "DERIVE";
		min = 0;
	};
}

local function onerror(msg, err, exit)
	io.stderr:write(msg, '\n');
	if err then
		io.stderr:write(err, '\n');
	end
	os.exit(exit or 1);
end


local function connect()
	local conn, err = socket.connect(os.getenv"host" or "localhost", os.getenv"port" or 5782);
	if not conn then onerror("Could not connect to prosody", err); end
	conn:settimeout(1);
	return conn;
end

local function get_config(item)
	for k,v in pairs(item) do
		if type(v) == "string" then
			print(k .. " " .. v);
		elseif type(v) == "table" then
			for sk,v in pairs(v) do
				if not sk:match("^_") then
					print(k.."."..sk.." "..v);
				end
			end
		end
	end
end

local function get_stats(item)
	local labels = {};
	for key, val in pairs(item) do
		if type(val) == "table" and val.label then
			labels[val._key or key] = key;
		end
	end

	local conn = connect();
	local line, err = conn:receive("*l");
	local stat, value, label;
	while line and line ~= "" and next(labels) ~= nil do
		stat, value = line:match('^STAT%s+"([^"]*)"%s*(%b())');
		label = stat and labels[stat];
		if label then
			print(label..".value "..tonumber(value:sub(2,-2)));
			labels[stat] = nil;
		end
		line, err = conn:receive("*l");
	end
	if err then onerror(err); end
end

local function main(stat, mode)
	if mode == "suggest" then
		for available_stat in pairs(stats) do
			print(available_stat);
		end
	elseif mode == "config" then
		return get_config(stats[stat]);
	elseif stats[stat] then
		return get_stats(stats[stat]);
	end
end

if arg then return main(arg[0]:match("prosody_(%w*)"), ...); end

return {
	stats = stats,
	get_stats = get_stats,
	get_config = get_config,
}

