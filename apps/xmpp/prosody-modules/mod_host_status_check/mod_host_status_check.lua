local time = require "socket".gettime;

local heartbeats = module:shared("/*/host_status_check/heartbeats");
local connection_events = module:shared("/*/host_status_check/connection_events");

if prosody.hosts[module.host].type == "component" and module:get_option_string("component_module") == "component" then
	module:hook("component-authenticated", function ()
		connection_events[module.host] = { connected = true; timestamp = time() };
	end);

	-- Note: this event is not in 0.9, and requires a recent 0.10 or trunk build
	module:hook("component-disconnected", function ()
		connection_events[module.host] = { connected = false; timestamp = time() };
	end);

	module:hook("stanza/xmpp:prosody.im/heartbeat:heartbeat", function ()
		heartbeats[module.host] = time();
		return true;
	end);
else
	connection_events[module.host] = { connected = true, timestamp = time() };
end

function module.unload()
	connection_events[module.host] = { connected = false, timestamp = time() };
	heartbeats[module.host] = nil;
end
