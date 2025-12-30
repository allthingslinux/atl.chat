module:set_global();

local mm = require "core.modulemanager";
local sm = require "core.statsmanager";

local measure_status = sm.metric("gauge", "prosody_module_status", "", "Prosody module status", { "host"; "module" });

local status_priorities = { error = 3; warn = 2; info = 1; core = 0 };

function module.add_host(module)
	local measure = measure_status:with_partial_label(module.host);

	if module.global then
		measure = measure_status:with_partial_label(":global");
	end

	-- Already loaded modules
	local modules = mm.get_modules(module.host);
	for name, mod in pairs(modules) do
		measure:with_labels(name):set(status_priorities[mod.module.status_type] or 0);
	end

	-- TODO hook module load and unload

	-- Future changes
	module:hook("module-status/updated", function(event)
		local mod = mm.get_module(event.name);
		measure:with_labels(event.name):set(status_priorities[mod and mod.module.status_type] or 0);
	end);

end

module:add_host(); -- Initialize global context
