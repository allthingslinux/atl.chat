local store = module:open_store("lastlog2");

local measure_d1 = module:measure("active_users_1d", "amount");
local measure_d7 = module:measure("active_users_7d", "amount");
local measure_d30 = module:measure("active_users_30d", "amount");

local is_enabled = require "core.usermanager".user_is_enabled;

-- Exclude disabled user accounts from the counts if usermanager supports that API
local count_disabled = module:get_option_boolean("measure_active_users_count_disabled", is_enabled == nil);

local get_last_active = module:depends("lastlog2").get_last_active;

function update_calculations()
	module:log("debug", "Calculating active users");
	local host = module.host;
	local host_user_sessions = prosody.hosts[host].sessions;
	local active_d1, active_d7, active_d30 = 0, 0, 0;
	local now = os.time();
	for username in store:users() do
		if host_user_sessions[username] then
			-- Active now
			active_d1, active_d7, active_d30 =
				active_d1 + 1, active_d7 + 1, active_d30 + 1;
		elseif count_disabled or is_enabled(username, host) then
			local last_active = get_last_active(username);
			if last_active then
				if now - last_active < 86400 then
					active_d1 = active_d1 + 1;
				end
				if now - last_active < 86400*7 then
					active_d7 = active_d7 + 1;
				end
				if now - last_active < 86400*30 then
					active_d30 = active_d30 + 1;
				end
			end
		end
	end
	module:log("debug", "Active users (took %ds): %d (24h), %d (7d), %d (30d)", os.time()-now, active_d1, active_d7, active_d30);
	measure_d1(active_d1);
	measure_d7(active_d7);
	measure_d30(active_d30);
end

-- Schedule at startup
module:add_timer(15, update_calculations);

-- Recalculate hourly
module:hourly(update_calculations);
