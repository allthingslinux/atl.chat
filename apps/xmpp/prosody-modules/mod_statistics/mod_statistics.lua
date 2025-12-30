module:set_global();

local stats = module:require("mod_statistics/stats");
local filters = require "util.filters";
local serialize = require "util.serialization".serialize;

local cached_values = {};

local sessions = {};

local function push_stat(conn, name, value)
	local value_str = serialize(value);
	return conn:write((("STAT %q (%s)\n"):format(name, value_str):gsub("\\\n", "\\n")));
end

local function push_stat_to_all(name, value)
	for conn in pairs(sessions) do
		push_stat(conn, name, value);
	end
end

local session_stats_tpl = ([[{
	message_in = %d, message_out = %d;
	presence_in = %d, presence_out = %d;
	iq_in = %d, iq_out = %d;
	bytes_in = %d, bytes_out = %d;
}]]):gsub("%s", "");


local jid_fields = {
	c2s = "full_jid";
	s2sin = "from_host";
	s2sout = "to_host";
	component = "host";
};

local function push_session_to_all(session, stats)
	local id = tostring(session):match("[a-f0-9]+$"); -- FIXME: Better id? :/
	local stanzas_in, stanzas_out = stats.stanzas_in, stats.stanzas_out;
	local s = (session_stats_tpl):format(
		stanzas_in.message, stanzas_out.message,
		stanzas_in.presence, stanzas_out.presence,
		stanzas_in.iq, stanzas_out.iq,
		stats.bytes_in, stats.bytes_out);
	local jid = session[jid_fields[session.type]] or "";
	for conn in pairs(sessions) do
		conn:write(("SESS %q %q %s\n"):format(id, jid, s));
	end
end

local available_stats = stats.stats;
local active_sessions = stats.active_sessions;

-- Handle statistics provided by other modules
local function item_handlers(host)
	host = host and (host.."/") or "";

	return function (event) -- Added
		local stats = event.item.statistics;
		local group = host..(stats.name and (stats.name.."::") or "");
		for name, stat in pairs(stats) do
			available_stats[group..name] = stat;
		end
	end, function (event) -- Removed
		local stats = event.item.statistics;
		local group = host..(stats.name and (stats.name.."::") or "");
		for name, stat in pairs(stats) do
			available_stats[group..name] = nil;
		end
	end;
end

module:handle_items("statistics-provider", item_handlers());
function module.add_host(module)
	module:handle_items("statistics-provider", item_handlers(module.host));
end

-- Network listener
local listener = {};

function listener.onconnect(conn)
	sessions[conn] = {};
	push_stat(conn, "version", prosody.version);
	for name, value in pairs(cached_values) do
		push_stat(conn, name, value);
	end
	conn:write("\n"); -- Signal end of first batch (for non-streaming clients)
end

function listener.onincoming(conn, data)
end

function listener.ondisconnect(conn)
	sessions[conn] = nil;
end

function listener.onreadtimeout()
	return true;
end

function module.load()
	if not(prosody and prosody.arg) then
		return;
	end
	filters.add_filter_hook(stats.filter_hook);

	module:add_timer(1, function ()
		for stat_name, stat in pairs(available_stats) do
			if stat.get then
				local cached = cached_values[stat_name];
				local new_value = stat.get();
				if new_value ~= cached then
					push_stat_to_all(stat_name, new_value);
					cached_values[stat_name] = new_value;
				end
			end
		end
		for session, session_stats in pairs(active_sessions) do
			active_sessions[session] = nil;
			push_session_to_all(session, session_stats);
		end
		return 1;
	end);

end
function module.unload()
	filters.remove_filter_hook(stats.filter_hook);
end
function module.command( args )
	local command = args[1];
	if command == "top" then
		local dir = module:get_directory();
		package.path = dir.."/?.lua;"..dir.."/?.lib.lua;"..package.path;
		local prosodytop = module:require "prosodytop";
		prosodytop.run();
	end
end

if prosody and prosody.arg then
	module:provides("net", {
		default_port = 5782;
		listener = listener;
		private = true;
	});
end
