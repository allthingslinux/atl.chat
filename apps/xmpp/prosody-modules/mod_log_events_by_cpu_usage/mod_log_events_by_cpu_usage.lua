module:set_global();

local treshold = module:get_option_number("log_cpu_threshold", 0.01);

function event_wrapper(handlers, event_name, event_data)
	local cpu_before = os.clock();
	local ret = handlers(event_name, event_data);
	local cpu_after = os.clock();
	if (cpu_after - cpu_before) > treshold then
		module:log("warn", "%g seconds of CPU usage while processing event '%s'", (cpu_after - cpu_before), event_name);
	end
	return ret;
end

local http_events = require "net.http.server"._events;
module:wrap_object_event(http_events, false, event_wrapper);

module:wrap_event(false, event_wrapper);
function module.add_host(module)
	module:wrap_event(false, event_wrapper);
end
