-- mod_benchmark_storage
-- Copyright (C) 2015 Kim Alvefur
--
-- Prime numbers are pretty cool

local gettime = require"socket".gettime;

local sm = require"core.storagemanager";
local um = require"core.usermanager";
local mm = require"core.modulemanager";

local test_data, test_users;

function module.command(arg)
	local test_driver = arg[1];
	if not test_driver then
		return print("Usage: prosodyctl mod_"..module.name.." <storage driver>");
	end

	local hostname = "benchmark.invalid";
	prosody.hosts[hostname] = {
		type = "local",
		events = prosody.events,
		modules = {},
		sessions = {},
		users = require "core.usermanager".new_null_provider(hostname)
	};

	sm.initialize_host(hostname);
	um.initialize_host(hostname);

	local start_time = gettime();
	local storage = assert(sm.load_driver(hostname, test_driver));
	storage = assert(storage:open("benchmark"));
	-- for i = 1, 23 do
		-- storage:set(test_users[i], test_data);
	-- end
	local floor, sin, random, pi = math.floor, math.sin, math.random, math.pi;
	for i = 1, 10079 do
		if i % 11 == 1 then
			storage:set(test_users[i%23+1], test_data[3-floor(sin(random()*pi)*3)]);
		else
			storage:get(test_users[i%23+1]);
		end
		if i % 151 == 0 then
			-- Give indication of progress
			io.write("*");
			io.flush();
		end
	end
	-- Cleanup
	for i = 1, 23 do
		storage:set(test_users[i], nil);
	end
	mm.unload(hostname, "storage_"..test_driver);
	local time_taken = gettime() - start_time;
	io.write("\27[0G\27[K"); -- Clear current line
	io.flush();
	print(("Took %fs with mod_storage_%s"):format(time_taken, test_driver));
end

-- 23 usernames
test_users = {
	"tritonymph"; "ankylotomy"; "tron"; "barbaric"; "twiddler"; 
	"spiritful"; "unmollifiably"; "suggestion"; "presubsistence"; 
	"unneeded"; "taxemic"; "teloteropathic"; "nonbending"; "mev"; 
	"septifragally"; "clame"; "obsolescent"; "unconceivable"; 
	"foolishly"; "conjunctur"; "precirculation"; "bethump"; "vermivorous";
};

test_data = {
	{ some_data = "tiny data" };
	--
	{ [false] = { version = 1; pending = {}; }; -- Medium data
		["user@example.com"] = { subscription = "both"; groups = {};
			name = "My Best Friend"; }; };
	--
	{ attr = { xmlns = "vcard-temp"; }; name = "vCard"; -- The largest data
	{ attr = { xmlns = "vcard-temp"; }; name = "NICKNAME"; "Buster"; };
	{ attr = { xmlns = "vcard-temp"; }; name = "PHOTO";
	{ attr = { xmlns = "vcard-temp"; }; name = "TYPE"; "image/jpeg"; };
	{ attr = { xmlns = "vcard-temp"; }; name = "BINVAL"; [[
	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
	FsQtGrr65p97R/X/ANxCn6r/2Q==]]; }; }; };
};
