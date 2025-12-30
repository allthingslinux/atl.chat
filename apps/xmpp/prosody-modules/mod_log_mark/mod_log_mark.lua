module:set_global();

local log = _G.log;

module:add_timer(60-os.date("%S"), function (now)
	log("info", "-- MARK --");
	return 90 - ((now + 30) % 60);
end);
