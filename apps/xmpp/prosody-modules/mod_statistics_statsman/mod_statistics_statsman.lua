module:set_global();

local statsman = require "core.statsmanager";
local time_now = require "util.time".now;
local filters = require "util.filters";
local serialize = require "util.serialization".serialize;

assert(statsman.get_stats, "not compatible with trunk based on openmetrics");

local statistics_interval = module:context("*"):get_option_number("statistics_interval", 60);
if module:context("*"):get_option("statistics", "internal") ~= "internal" then
	module:log("error", "Not using internal statistics, can't do anyting");
	return;
end

local sessions = {};

local name_map = {
	["start_time"] = "up_since";
	["cpu.percent:amount"] = "cpu";
	["cpu.clock:amount"] = "cpu_total";
	["memory.allocated_mmap:amount"] = "memory_allocated_mmap";
	["memory.allocated:amount"] = "memory_allocated";
	["memory.lua:amount"] = "memory_lua";
	["memory.returnable:amount"] = "memory_returnable";
	["memory.rss:amount"] = "memory_rss";
	["memory.total:amount"] = "memory_total";
	["memory.unused:amount"] = "memory_unused";
	["memory.used:amount"] = "memory_used";
	["/*/mod_c2s/connections:amount"] = "total_c2s";
	["/*/mod_s2s/connections:amount"] = "total_s2s";
};

local function push_stat(conn, name, value)
	local value_str = serialize(value);
	name = name_map[name] or name;
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

local active_sessions = {};

-- Network listener
local listener = {};

function listener.onconnect(conn)
	sessions[conn] = true;
	push_stat(conn, "version", prosody.version);
	push_stat(conn, "start_time", prosody.start_time);
	push_stat(conn, "statistics_interval", statistics_interval);
	push_stat(conn, "time", time_now());
	local stats = statsman.get_stats();
	for name, value in pairs(stats) do
		push_stat(conn, name, value);
	end
	conn:write("\n"); -- Signal end of first batch (for non-streaming clients)
end

function listener.onincoming(conn, data) -- luacheck: ignore 212
	-- Discarded
end

function listener.ondisconnect(conn)
	sessions[conn] = nil;
end

function listener.onreadtimeout()
	return true;
end

local add_statistics_filter; -- forward decl
if prosody and prosody.arg then -- ensures we aren't in prosodyctl
	setmetatable(active_sessions, {
		__index = function ( t, k )
			local v = {
				bytes_in = 0, bytes_out = 0;
				stanzas_in = {
					message = 0, presence = 0, iq = 0;
				};
				stanzas_out = {
					message = 0, presence = 0, iq = 0;
				};
			}
			rawset(t, k, v);
			return v;
		end
	});
	local function handle_stanza_in(stanza, session)
		local s = active_sessions[session].stanzas_in;
		local n = s[stanza.name];
		if n then
			s[stanza.name] = n + 1;
		end
		return stanza;
	end
	local function handle_stanza_out(stanza, session)
		local s = active_sessions[session].stanzas_out;
		local n = s[stanza.name];
		if n then
			s[stanza.name] = n + 1;
		end
		return stanza;
	end
	local function handle_bytes_in(bytes, session)
		local s = active_sessions[session];
		s.bytes_in = s.bytes_in + #bytes;
		return bytes;
	end
	local function handle_bytes_out(bytes, session)
		local s = active_sessions[session];
		s.bytes_out = s.bytes_out + #bytes;
		return bytes;
	end
	function add_statistics_filter(session)
		filters.add_filter(session, "stanzas/in", handle_stanza_in);
		filters.add_filter(session, "stanzas/out", handle_stanza_out);
		filters.add_filter(session, "bytes/in", handle_bytes_in);
		filters.add_filter(session, "bytes/out", handle_bytes_out);
	end
end


function module.load()
	if not(prosody and prosody.arg) then
		return;
	end
	filters.add_filter_hook(add_statistics_filter);

	module:add_timer(1, function ()
		for session, session_stats in pairs(active_sessions) do
			active_sessions[session] = nil;
			push_session_to_all(session, session_stats);
		end
		return 1;
	end);

	module:hook("stats-updated", function (event)
		local stats = event.changed_stats;
		push_stat_to_all("time", time_now());
		for name, value in pairs(stats) do
			push_stat_to_all(name, value);
		end
	end);

	module:hook("server-stopping", function ()
		push_stat_to_all("stop_time", time_now());
	end);
end
function module.unload()
	filters.remove_filter_hook(add_statistics_filter);
end

if prosody and prosody.arg then
	module:provides("net", {
		default_port = 5782;
		listener = listener;
		private = true;
	});
end
