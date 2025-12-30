module:set_global();

local measure = require"core.statsmanager".measure;
local mt = require"util.multitable";
local get_time = require "socket".gettime;
local get_clock = os.clock;

local measure_cpu_now = measure("amount", "cpu.percent"); -- Current percentage
local measure_cpu_total = measure("counter", "cpu.clock", { units = "seconds" });

local last_cpu_wall, last_cpu_clock;
module:hook("stats-update", function ()
	local new_wall, new_clock = get_time(), get_clock();
	local pc = 0;
	if last_cpu_wall then
		pc = 100/((new_wall-last_cpu_wall)/(new_clock-last_cpu_clock));
	end
	last_cpu_wall, last_cpu_clock = new_wall, new_clock;

	measure_cpu_now(pc);
	measure_cpu_total(new_clock);
end);

-- Some metadata for mod_munin
local munin_meta = mt.new(); munin_meta.data = module:shared"munin/meta";
local key = "global_cpu_amount";

munin_meta:set(key, "", "graph_args", "--base 1000 -r --lower-limit 0 --upper-limit 100");
munin_meta:set(key, "", "graph_title", "Prosody CPU Usage");
munin_meta:set(key, "", "graph_vlabel", "%");
munin_meta:set(key, "", "graph_category", "cpu");

munin_meta:set(key, "percent", "label", "CPU Usage");
munin_meta:set(key, "percent", "min", "0");

