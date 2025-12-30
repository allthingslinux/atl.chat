-- This module is only for 0.12, later versions have mod_flags bundled
--% conflicts: mod_flags

local flags_map;
if prosody.process_type ~= "prosodyctl" then
	flags_map = module:open_store("account_flags", "map");
end

-- API

function add_flag(username, flag, comment) -- luacheck: ignore 131/add_flag
	local flag_data = {
		when = os.time();
		comment = comment;
	};

	local ok, err = flags_map:set(username, flag, flag_data);
	if not ok then
		return nil, err;
	end

	module:fire_event("user-flag-added/"..flag, {
		user = username;
		flag = flag;
		data = flag_data;
	});

	return true;
end

function remove_flag(username, flag) -- luacheck: ignore 131/remove_flag
	local ok, err = flags_map:set(username, flag, nil);
	if not ok then
		return nil, err;
	end

	module:fire_event("user-flag-removed/"..flag, {
		user = username;
		flag = flag;
	});

	return true;
end

function has_flag(username, flag) -- luacheck: ignore 131/has_flag
	local ok, err = flags_map:get(username, flag);
	if not ok and err then
		error("Failed to check flags for user: "..err);
	end
	return not not ok;
end

function get_flag_info(username, flag) -- luacheck: ignore 131/get_flag_info
	return flags_map:get(username, flag);
end


-- Migration from mod_firewall marks

local function migrate_marks(host)
	local usermanager = require "core.usermanager";

	local flag_storage = module:open_store("account_flags");
	local mark_storage = module:open_store("firewall_marks");

	local migration_comment = "Migrated from mod_firewall marks at "..os.date("%Y-%m-%d %R");

	local migrated, empty, errors = 0, 0, 0;
	for username in usermanager.users(host) do
		local marks, err = mark_storage:get(username);
		if marks then
			local flags = {};
			for mark_name, mark_timestamp in pairs(marks) do
				flags[mark_name] = {
					when = mark_timestamp;
					comment = migration_comment;
				};
			end
			local saved_ok, saved_err = flag_storage:set(username, flags);
			if saved_ok then
				prosody.log("error", "Failed to save flags for %s: %s", username, saved_err);
				migrated = migrated + 1;
			else
				errors = errors + 1;
			end
		elseif err then
			prosody.log("error", "Failed to load marks for %s: %s", username, err);
			errors = errors + 1;
		else
			empty = empty + 1;
		end
	end

	print(("Finished - %d migrated, %d users with no marks, %d errors"):format(migrated, empty, errors));
end

function module.command(arg)
	local storagemanager = require "core.storagemanager";
	local usermanager = require "core.usermanager";
	local jid = require "util.jid";
	local warn = require"util.prosodyctl".show_warning;

	local command = arg[1];
	if not command then
		warn("Valid subcommands: migrate_marks");
		return 0;
	end
	table.remove(arg, 1);

	local node, host = jid.prepped_split(arg[1]);
	if not host then
		warn("Please specify a host or JID after the command");
		return 1;
	elseif not prosody.hosts[host] then
		warn("Unknown host: "..host);
		return 1;
	end

	table.remove(arg, 1);

	module.host = host; -- luacheck: ignore 122
	storagemanager.initialize_host(host);
	usermanager.initialize_host(host);

	flags_map = module:open_store("account_flags", "map");

	if command == "migrate_marks" then
		migrate_marks(host);
		return 0;
	elseif command == "find" then
		local flag = assert(arg[1], "expected argument: flag");
		local flags = module:open_store("account_flags", "map");
		local users_with_flag = flags:get_all(flag);

		local c = 0;
		for user, flag_data in pairs(users_with_flag) do
			print(user, os.date("%Y-%m-%d %R", flag_data.when), flag_data.comment or "");
			c = c + 1;
		end

		print(("%d accounts listed"):format(c));
		return 1;
	elseif command == "add" then
		local username = assert(node, "expected a user JID, got "..host);
		local flag = assert(arg[1], "expected argument: flag");
		local comment = arg[2];

		local ok, err = add_flag(username, flag, comment);
		if not ok then
			print("Failed to add flag: "..err);
			return 1;
		end

		print("Flag added");
		return 1;
	elseif command == "remove" then
		local username = assert(node, "expected a user JID, got "..host);
		local flag = assert(arg[1], "expected argument: flag");

		local ok, err = remove_flag(username, flag);
		if not ok then
			print("Failed to remove flag: "..err);
			return 1;
		end

		print("Flag removed");
		return 1;
	elseif command == "list" then
		local username = assert(node, "expected a user JID, got "..host);

		local c = 0;

		local flags = module:open_store("account_flags");
		local user_flags, err = flags:get(username);

		if not user_flags and err then
			print("Unable to list flags: "..err);
			return 1;
		end

		if user_flags then
			for flag_name, flag_data in pairs(user_flags) do
				print(flag_name, os.date("%Y-%m-%d %R", flag_data.when), flag_data.comment or "");
				c = c + 1;
			end
		end

		print(("%d flags listed"):format(c));
		return 0;
	else
		warn("Unknown command: %s", command);
		return 1;
	end
end
