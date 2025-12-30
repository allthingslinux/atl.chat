module:set_global();

local statsmanager = require "prosody.core.statsmanager";

local measure_features = module:metric("gauge", "features", "", "Features advertized by clients", {"feature"});

local disco_ns = "http://jabber.org/protocol/disco#info";

module:hook("stats-update", function ()
	local total = 0;
	local buckets = {};
	for _, session in pairs(prosody.full_sessions) do
		local disco_info = session.caps_cache;
		if disco_info ~= nil then
			for feature in disco_info:childtags("feature", disco_ns) do
				local var = feature.attr.var;
				if var ~= nil then
					if buckets[var] == nil then
						buckets[var] = 0;
					end
					buckets[var] = buckets[var] + 1;
				end
			end
			total = total + 1;
		end
	end
	statsmanager.cork();
	measure_features:clear();
	for bucket, count in pairs(buckets) do
		measure_features:with_labels(bucket):add(count);
	end
	measure_features:with_labels("total"):add(total);
	statsmanager.uncork();
end)
