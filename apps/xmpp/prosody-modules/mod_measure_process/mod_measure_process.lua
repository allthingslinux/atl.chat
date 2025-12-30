module:set_global()

local get_cpu_time = os.clock

local custom_metric = require "core.statsmanager".metric
local cpu_time = custom_metric(
	"counter", "process_cpu", "seconds",
	"CPU time used by Prosody as reported by clock(3)."
):with_labels()

local lfs = require "lfs"

module:hook("stats-update", function ()
	cpu_time:set(get_cpu_time())
end);

if lfs.attributes("/proc/self/statm", "mode") == "file" then
	local pagesize = module:get_option_number("memory_pagesize", 4096); -- getconf PAGESIZE

	local vsz = custom_metric(
		"gauge", "process_virtual_memory", "bytes",
		"Virtual memory size in bytes."
	):with_labels()
	local rss = custom_metric(
		"gauge", "process_resident_memory", "bytes",
		"Resident memory size in bytes."
	):with_labels()

	module:hook("stats-update", function ()
		local statm, err = io.open("/proc/self/statm");
		if not statm then
			module:log("error", tostring(err));
			return;
		end
		-- virtual memory (caches, opened librarys, everything)
		vsz:set(statm:read("*n") * pagesize);
		-- resident set size (actually used memory)
		rss:set(statm:read("*n") * pagesize);
		statm:close();
	end);
end

if lfs.attributes("/proc/self/fd", "mode") == "directory" then
	local open_fds = custom_metric(
		"gauge", "process_open_fds", "",
		"Number of open file descriptors."
	):with_labels()

	local has_posix, posix = pcall(require, "util.pposix")
	local max_fds
	if has_posix then
		max_fds = custom_metric(
			"gauge", "process_max_fds", "",
			"Maximum number of open file descriptors"
		):with_labels()
	else
		module:log("warn", "not reporting maximum number of file descriptors because mod_posix is not available")
	end

	local function limit2num(limit)
		if limit == "unlimited" then
			return math.huge
		end
		return limit
	end

	module:hook("stats-update", function ()
		local count = 0
		for _ in lfs.dir("/proc/self/fd") do
			count = count + 1
		end
		open_fds:set(count)

		if has_posix then
			local ok, soft, hard = posix.getrlimit("NOFILE")
			if ok then
				max_fds:set(limit2num(soft or hard));
			end
		end
	end);
end
