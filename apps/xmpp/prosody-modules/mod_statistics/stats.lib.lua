local it = require "util.iterators";
local log = require "util.logger".init("stats");
local has_pposix, pposix = pcall(require, "util.pposix");
local human;
do
	local tostring = tostring;
	local s_format = string.format;
	local m_floor = math.floor;
	local m_max = math.max;
	local prefixes = "kMGTPEZY";
	local multiplier = 1024;

	function human(num)
		num = tonumber(num) or 0;
		local m = 0;
		while num >= multiplier and m < #prefixes do
			num = num / multiplier;
			m = m + 1;
		end

		return s_format("%0."..m_max(0,3-#tostring(m_floor(num))).."f%sB",
		num, m > 0 and (prefixes:sub(m,m) .. "i") or "");
	end
end

local last_cpu_wall, last_cpu_clock;
local get_time = require "socket".gettime;

local active_sessions, active_jids = {}, {};
local c2s_sessions, s2s_sessions;
if prosody and prosody.arg then
	c2s_sessions = module:shared("/*/c2s/sessions");
	s2s_sessions = module:shared("/*/s2s/sessions");
end

local stats = {
	total_users = {
		get = function () return it.count(it.keys(bare_sessions)); end
	};
	total_c2s = {
		get = function () return it.count(it.keys(full_sessions)); end
	};
	total_s2sin = {
		get = function () local i = 0; for conn,sess in next,s2s_sessions do if sess.direction == "incoming" then i = i + 1 end end return i end
	};
	total_s2sout = {
		get = function () local i = 0; for conn,sess in next,s2s_sessions do if sess.direction == "outgoing" then i = i + 1 end end return i end
	};
	total_s2s = {
		get = function () return it.count(it.keys(s2s_sessions)); end
	};
	total_component = {
		get = function ()
			local count = 0;
			for host, host_session in pairs(hosts) do
				if host_session.type == "component" then
					local c = host_session.modules.component;
					if c and c.connected then -- 0.9 only
						count = count + 1;
					end
				end
			end
			return count;
		end
	};
	up_since = {
		get = function () return prosody.start_time; end;
		tostring = function (up_since)
			return tostring(os.time()-up_since).."s";
		end;
	};
	memory_lua = {
		get = function () return math.ceil(collectgarbage("count")*1024); end;
		tostring = human;
	};
	time = {
		tostring = function () return os.date("%T"); end;
	};
	cpu = {
		get = function ()
			local new_wall, new_clock = get_time(), os.clock();
			local pc = 0;
			if last_cpu_wall then
				pc = 100/((new_wall-last_cpu_wall)/(new_clock-last_cpu_clock));
			end
			last_cpu_wall, last_cpu_clock = new_wall, new_clock;
			return math.ceil(pc);
		end;
		tostring = "%s%%";
	};
};

local memory_update_interval = 60;
if prosody and prosody.arg then
	memory_update_interval = module:get_option_number("statistics_meminfo_interval", 60);
end


if has_pposix and pposix.meminfo then

	local cached_meminfo, last_cache_update;
	local function meminfo()
		if not cached_meminfo or (os.time() - last_cache_update) > memory_update_interval then
			cached_meminfo = pposix.meminfo();
			last_cache_update = os.time();
		end
		return cached_meminfo;
	end

	stats.memory_allocated = {
		get = function () return math.ceil(meminfo().allocated); end;
		tostring = human;
	}
	stats.memory_used = {
		get = function () return math.ceil(meminfo().used); end;
		tostring = human;
	}
	stats.memory_unused = {
		get = function () return math.ceil(meminfo().unused); end;
		tostring = human;
	}
	stats.memory_returnable = {
		get = function () return math.ceil(meminfo().returnable); end;
		tostring = human;
	}
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
	local filters = require "util.filters";
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

return {
	stats = stats;
	active_sessions = active_sessions;
	filter_hook = add_statistics_filter;
};
