local st = require "util.stanza";
local time = require "socket".gettime;

local heartbeat_interval = module:get_option_number("status_check_heartbeat_interval", 5);
local heartbeat_mode = module:get_option_string("status_check_heartbeat_mode", "remote");

local local_heartbeats = module:shared("/*/host_status_check/heartbeats");

local heartbeat_methods = {
	["local"] = function()
		module:log("debug", "Local heartbeat");
		local_heartbeats[module.host] = time();
		return heartbeat_interval;
	end;

	["remote"] = function ()
		module:fire_event("route/remote", {
			origin = prosody.hosts[module.host];
			stanza = st.stanza("heartbeat", { xmlns = "xmpp:prosody.im/heartbeat" });
		});
		return heartbeat_interval;
	end;		
}

local send_heartbeat = assert(heartbeat_methods[heartbeat_mode], "Unknown heartbeat_mode: "..heartbeat_mode);

module:add_timer(0, send_heartbeat);
