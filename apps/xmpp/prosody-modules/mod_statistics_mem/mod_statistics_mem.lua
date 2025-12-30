-- Probably Linux-specific memory statistics

module:set_global();

local human;
do
	local tostring = tostring;
	local s_format = string.format;
	local m_floor = math.floor;
	local m_max = math.max;
	local prefixes = "kMGTPEZY";
	local multiplier = 1024;

	function human(num)
		num = tonumber(num) or 0;
		local m = 0;
		while num >= multiplier and m < #prefixes do
			num = num / multiplier;
			m = m + 1;
		end

		return s_format("%0."..m_max(0,3-#tostring(m_floor(num))).."f%sB",
		num, m > 0 and (prefixes:sub(m,m) .. "i") or "");
	end
end


local pagesize = 4096; -- according to getpagesize()
module:provides("statistics", {
	statistics = {
		memory_total = { -- virtual memory
			get = function ()
				local statm, err = io.open"/proc/self/statm";
				if statm then
					local total = statm:read"*n";
					statm:close();
					return total * pagesize;
				else
					module:log("debug", err);
				end
			end;
			tostring = human;
		};
		memory_rss = { -- actual in-memory data size
			get = function ()
				local statm, err = io.open"/proc/self/statm";
				if statm then
					statm:read"*n"; -- Total size, ignore
					local rss = statm:read"*n";
					statm:close();
					return rss * pagesize;
				else
					module:log("debug", err);
				end
			end;
			tostring = human;
		};
	}
});
