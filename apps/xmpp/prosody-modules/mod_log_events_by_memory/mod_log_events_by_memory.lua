module:set_global();

local treshold = module:get_option_number("log_memory_threshold", 20*1024);

function event_wrapper(handlers, event_name, event_data)
	local memory_before = collectgarbage("count")*1024;
	local ret = handlers(event_name, event_data);
	local memory_after = collectgarbage("count")*1024;
	if (memory_after - memory_before) > treshold then
		module:log("warn", "Memory increased by %g bytes while processing event '%s'", (memory_after - memory_before), event_name);
	end
	return ret;
end

local http_events = require "net.http.server"._events;
module:wrap_object_event(http_events, false, event_wrapper);

module:wrap_event(false, event_wrapper);
function module.add_host(module)
	module:wrap_event(false, event_wrapper);
end
