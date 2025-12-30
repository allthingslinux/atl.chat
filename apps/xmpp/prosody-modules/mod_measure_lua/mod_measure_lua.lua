module:set_global()

local custom_metric = require "core.statsmanager".metric
local gc_bytes = custom_metric(
	"gauge", "lua_heap", "bytes",
	"Memory used by objects under control of the Lua garbage collector"
):with_labels()

module:hook("stats-update", function ()
	local kbytes = collectgarbage("count");
  gc_bytes:set(kbytes * 1024);
end);

custom_metric("gauge", "lua_info", "", "Lua runtime version", { "version" }):with_labels(_VERSION):set(1);
