module:set_global();

local metric = require"core.statsmanager".metric;
local pposix = require"util.pposix";

local allocated = metric(
	"gauge", "malloc_heap_allocated", "bytes",
	"Allocated bytes by mode of allocation",
	{"mode"}
);

local used = metric(
	"gauge", "malloc_heap_used", "bytes",
	"Used bytes"
):with_labels();

local unused = metric(
	"gauge", "malloc_heap_unused", "bytes",
	"Unused bytes"
):with_labels();

local returnable = metric(
	"gauge", "malloc_heap_returnable", "bytes",
	"Returnable bytes"
):with_labels();

module:hook("stats-update", function ()
	local meminfo = pposix.meminfo();
	if meminfo.allocated then
		allocated:with_labels("sbrk"):set(meminfo.allocated);
	end
	if meminfo.allocated_mmap then
		allocated:with_labels("mmap"):set(meminfo.allocated_mmap);
	end
	if meminfo.used then
		used:set(meminfo.used);
	end
	if meminfo.unused then
		unused:set(meminfo.unused);
	end
	if meminfo.returnable then
		returnable:set(meminfo.returnable);
	end
end);
