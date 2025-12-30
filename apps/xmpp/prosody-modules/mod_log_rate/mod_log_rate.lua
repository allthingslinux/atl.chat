module:set_global();

local function sink_maker(config)
	local levels = {
		debug = module:measure("log.debug", "rate");
		info = module:measure("log.info", "rate");
		warn = module:measure("log.warn", "rate");
		error = module:measure("log.error", "rate");
	};
	return function (_, level)
		return levels[level]();
	end
end

require"core.loggingmanager".register_sink_type("measure", sink_maker);
