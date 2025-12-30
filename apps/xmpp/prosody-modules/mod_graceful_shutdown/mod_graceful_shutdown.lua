-- luacheck: ignore 122/prosody 113/prosody

local timer = require "util.timer";
local portman = require "core.portmanager";
local server = require "net.server";

module:set_global();
local orig_shutdown = prosody.shutdown;

local pause = module:get_option_number("shutdown_pause", 1);

function module.unload()
	prosody.shutdown = orig_shutdown;
end

prosody.shutdown = coroutine.wrap(function (reason, code)
	prosody.shutdown_reason = reason;
	prosody.shutdown_code = code;
	timer.add_task(pause, prosody.shutdown);
	coroutine.yield(true, "shutdown initiated");
	-- Close c2s ports, stop accepting new connections
	portman.deactivate("c2s");
	portman.deactivate("legacy_ssl");
	portman.deactivate("c2s_direct_tls");

	-- Close multiplexing ports to ensure c2s is not reachable via those either
	portman.deactivate("multiplex");
	portman.deactivate("multiplex_ssl");
	portman.deactivate("proxy"); -- mod_net_proxy

	-- Close all c2s sessions
	for _, sess in pairs(prosody.full_sessions) do
		sess:close{ condition = "system-shutdown", text = reason }
	end
	-- Wait for notifications to be sent
	coroutine.yield(pause);
	-- Event for everything else to shut down
	prosody.events.fire_event("server-stopping", {
		reason = reason;
		code = code;
	});
	-- And wait
	coroutine.yield(pause);
	-- And stop main event loop
	server.setquitting(true);
	-- And wait for death
	coroutine.yield(pause * 3);
	-- you came back? die zombie!
	os.exit(1);
end);
