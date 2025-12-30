module:set_global();

local measure = require"core.statsmanager".measure;

local measures = {};
setmetatable(measures, {
	__index = function (t, k)
		local m = measure("amount", "memory."..k, { units = "bytes" }); t[k] = m; return m;
	end
});

module:hook("stats-update", function ()
	measures.lua(collectgarbage("count")*1024);
end);

if require"lfs".attributes("/proc/self/statm", "mode") == "file" then
	local pagesize = module:get_option_number("memory_pagesize", 4096); -- getconf PAGESIZE

	module:hook("stats-update", function ()
		local statm, err = io.open("/proc/self/statm");
		if not statm then
			module:log("error", tostring(err));
			return;
		end
		-- virtual memory (caches, opened librarys, everything)
		measures.total(statm:read("*n") * pagesize);
		-- resident set size (actually used memory)
		measures.rss(statm:read("*n") * pagesize);
		statm:close();
	end);
end
