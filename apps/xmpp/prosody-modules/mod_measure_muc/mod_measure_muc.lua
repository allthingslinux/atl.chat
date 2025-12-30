-- Group Chat statistics
--
-- Copyright (C) 2020 kaliko <kaliko@azylum.org>
--
-- This module is MIT/X11 licensed.

-- https://prosody.im/doc/developers/modules
-- https://prosody.im/doc/developers/moduleapi
-- https://prosody.im/doc/statistics

module:log("info", "loading mod_%s", module.name);
if module:get_host_type() ~= "component" then
	module:log("error", "mod_%s should be loaded only on a MUC component, not normal hosts", module.name);
	return;
end

local mod_muc = module:depends"muc";
local all_rooms = rawget(mod_muc, "all_rooms")

-- Add relevant boolean MUC metrics here
local counters = {
	hidden = module:measure("hidden", "amount", 0),
	persistent = module:measure("persistent", "amount", 0),
	password = module:measure('passwd', "amount", 0),
	archiving = module:measure('archiving', 'amount', 0),
};
local total_counter = module:measure("total", "amount", 0);

module:hook_global("stats-update", function ()
	local total = 0;
	local buckets = {};
	-- Init buckets
	for bucket, _ in pairs(counters) do
		buckets[bucket] = 0;
	end
	for room in all_rooms() do
		--[[
		module:log('debug', 'room data for : "'..room.jid..'"');
		for conf, val in pairs(room._data) do
			module:log('debug', conf..": "..tostring(val));
		end
		]]--
		total = total + 1;
		--module:log('debug','buckets room data :');
		for bucket, _ in pairs(buckets) do
			--module:log('debug', bucket..": "..tostring(room._data[bucket]));
			if room._data[bucket] then
				buckets[bucket] = buckets[bucket] + 1;
			end
		end
	end
	for bucket, count in pairs(buckets) do
		counters[bucket](count)
	end
	total_counter(total);
end)
