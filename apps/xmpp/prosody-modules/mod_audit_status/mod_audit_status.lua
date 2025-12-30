module:depends("audit");

local st = require "util.stanza";

-- Suppress warnings about module:audit()
-- luacheck: ignore 143/module

local heartbeat_interval = module:get_option_number("audit_status_heartbeat_interval", 60);

local store = module:open_store(nil, "keyval+");

-- This is global, to make it available to other modules
crashed = false; --luacheck: ignore 131/crashed

module:hook_global("server-started", function ()
	local recorded_status = store:get();
	if recorded_status and recorded_status.status == "started" then
		module:audit(nil, "server-crashed", { timestamp = recorded_status.heartbeat });
		crashed = true;
	end
	module:audit(nil, "server-started");
	store:set_key(nil, "status", "started");
end);

module:hook_global("server-stopped", function ()
	module:audit(nil, "server-stopped", {
		custom = {
			prosody.shutdown_reason and st.stanza("note"):text(prosody.shutdown_reason);
		};
	});
	store:set_key(nil, "status", "stopped");
end);

if heartbeat_interval then
	local async = require "util.async";
	local heartbeat_writer = async.runner(function (timestamp)
		store:set_key(nil, "heartbeat", timestamp);
	end);

	module:add_timer(0, function ()
		heartbeat_writer:run(os.time());
		return heartbeat_interval;
	end);
end
