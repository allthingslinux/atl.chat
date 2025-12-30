-- This module is based on the shell command code from mod_account_activity

local autoremove = module:get_option_boolean("migrate_lastlog2_auto_remove", true);

local function do_migration()
	local store = module:open_store("account_activity", "keyval+");
	local lastlog2 = module:open_store("lastlog2", "keyval+");
	local n_updated, n_errors, n_skipped = 0, 0, 0;

	local async = require "prosody.util.async";

	local p = require "prosody.util.promise".new(function (resolve)
		local async_runner = async.runner(function ()
			local n = 0;
			for username in lastlog2:items() do
				local was_error = nil;
				n = n + 1;
				if n % 100 == 0 then
					module:log("debug", "Processed %d...", n);
					async.sleep(0);
				end
				local lastlog2_data = lastlog2:get(username);
				if lastlog2_data then
					local current_data, err = store:get(username);
					if not current_data then
						if not err then
							current_data = {};
						else
							n_errors = n_errors + 1;
						end
					end
					if current_data then
						local imported_timestamp = current_data.timestamp;
						local latest;
						for k, v in pairs(lastlog2_data) do
							if k ~= "registered" and (not latest or v.timestamp > latest) then
								latest = v.timestamp;
							end
						end
						if latest and (not imported_timestamp or imported_timestamp < latest) then
							local ok, err = store:set_key(username, "timestamp", latest);
							if ok then
								n_updated = n_updated + 1;
							else
								module:log("error", "Failed to import %q: %s", username, err);
								was_error = true;
								n_errors = n_errors + 1;
							end
						else
							n_skipped = n_skipped + 1;
						end
					end
					if autoremove and not was_error then
						lastlog2:set(username, nil);
					end
				end
			end
			return resolve(("%d accounts imported, %d errors, %d skipped"):format(n_updated, n_errors, n_skipped));
		end);
		async_runner:run(true);
	end);
	return p;
end

function module.ready()
	do_migration();
end
