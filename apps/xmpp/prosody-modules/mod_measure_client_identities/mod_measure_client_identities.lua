module:set_global();

local measure = require"core.statsmanager".measure;

local counters = {
	unknown = measure("amount", "client_identities.unknown"),
};

module:hook("stats-update", function ()
	local buckets = {
		unknown = 0,
	};
	for _, session in pairs(prosody.full_sessions) do
		if session.caps_cache ~= nil then
			local node_string = session.caps_cache.attr.node;
			local node = node_string:match("([^#]+)");
			if buckets[node] == nil then
				buckets[node] = 0;
			end
			buckets[node] = buckets[node] + 1;
		else
			buckets.unknown = buckets.unknown + 1;
		end
	end
	local visited = {};
	for bucket, count in pairs(buckets) do
		if counters[bucket] == nil then
			counters[bucket] = measure("amount", "client_identities."..bucket);
		end
		counters[bucket](count);
		visited[bucket] = true;
	end
	for bucket, counter in pairs(counters) do
		if not visited[bucket] then
			counter(0);
		end
	end
end)
