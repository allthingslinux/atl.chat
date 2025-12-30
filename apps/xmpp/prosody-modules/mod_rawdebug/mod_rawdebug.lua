module:set_global();

local tostring = tostring;
local filters = require "util.filters";

local function log_send(t, session)
	if t and t ~= "" and t ~= " " then
		session.log("debug", "SEND(%d): %s", #t, tostring(t));
	end
	return t;
end

local function log_recv(t, session)
	if t and t ~= "" and t ~= " " then
		session.log("debug", "RECV(%d): %s", #t, tostring(t));
	end
	return t;
end

local function init_raw_logging(session)
	filters.add_filter(session, "bytes/in",  log_recv, -10000);
	filters.add_filter(session, "bytes/out", log_send,  10000);
end

filters.add_filter_hook(init_raw_logging);

function module.unload() -- luacheck: ignore
	filters.remove_filter_hook(init_raw_logging);
end
