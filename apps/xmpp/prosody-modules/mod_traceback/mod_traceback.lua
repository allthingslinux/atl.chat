module:set_global();

local traceback = require "util.debug".traceback;

local signal = module:get_option_string(module.name, "SIGUSR1");
module:hook("signal/" .. signal, function()
	module:log("info", "Received %s, writing traceback", signal);
	local f = io.open(prosody.paths.data .. "/traceback.txt", "a+");
	f:write(traceback(), "\n");
	f:close();
end);

