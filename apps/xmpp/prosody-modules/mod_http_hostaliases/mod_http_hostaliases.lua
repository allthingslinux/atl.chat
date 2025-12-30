module:set_global();

local host_map = { };

module:wrap_object_event(require "net.http.server"._events, false, function (handlers, event_name, event_data)
	local verb, host, path = event_name:match("^(%w+ )(.-)(/.*)");
	host = host_map[host];
	event_name = verb .. host .. path;
	return handlers(event_name, event_data);
end);

function module.add_host(module)
	local http_host = module:get_option_string("http_host");
	for host in module:get_option_set("http_host_aliases", {}) do
		host_map[host] = http_host;
	end
end
