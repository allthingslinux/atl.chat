module:set_global();

local helpers = require "util.helpers";

local function init(module, events, name)
	helpers.log_events(events, name, module._log);

	function module.unload()
		helpers.revert_log_events(events);
	end
end

init(module, prosody.events, "global");

function module.add_host(module)
	init(module, prosody.hosts[module.host].events, module.host);
end
