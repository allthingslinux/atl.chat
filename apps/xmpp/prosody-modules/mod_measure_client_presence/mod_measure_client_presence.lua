module:set_global();

local statsmanager = require "prosody.core.statsmanager";

local measure_presences = module:metric("gauge", "presence", "client", "Presence show used by clients", {"show"});

local valid_shows = {
	available = true,
	chat = true,
	away = true,
	dnd = true,
	xa = true,
	unavailable = true,
}

module:hook("stats-update", function ()
	local buckets = {
		available = 0,
		chat = 0,
		away = 0,
		dnd = 0,
		xa = 0,
		unavailable = 0,
		invalid = 0,
	};
	for _, session in pairs(prosody.full_sessions) do
		local status = "unavailable";
		if session.presence then
			status = session.presence:get_child_text("show") or "available";
		end
		if valid_shows[status] ~= nil then
			buckets[status] = buckets[status] + 1;
		else
			buckets.invalid = buckets.invalid + 1;
		end
	end
	statsmanager.cork();
	measure_presences:clear();
	for bucket, count in pairs(buckets) do
		measure_presences:with_labels(bucket):add(count);
	end
	statsmanager.uncork();
end)
