-- mod_migrate

local unpack = table.unpack or unpack; --luacheck: ignore 113/unpack
local sm = require"core.storagemanager";
local um = require"core.usermanager";

local function users(store, host)
	if store.users then
		return store:users();
	else
		return um.users(host);
	end
end

local function stores(host)
	if store.users then
		return store:users();
	else
		return um.users(host);
	end
end

local function migrate_store(host, source_store, store_type, migrate_to, migrate_users)
	local module = module:context(host);
	local storage = module:open_store(source_store, store_type);
	local target = assert(sm.load_driver(host, migrate_to));
	target = assert(target:open(source_store, store_type));

	local function migrate_user(username)
		module:log("info", "Migrating %s data for %s", source_store, username);
		if username == "" then username = nil; end
		local data, err = storage:get(username);
		if not data and err then
			module:log("error", "Could not read data: %s", err);
		else
			local ok, err = target:set(username, data);
			if not ok then
				module:log("error", "Could not write data: %s", err);
			end
		end
	end

	if store_type == "archive" then
		function migrate_user(username)
			module:log("info", "Migrating %s archive items for %s", source_store, username);
			if username == "" then username = nil; end
			local count, errs = 0, 0;
			for id, item, when, with in storage:find(username) do
				local ok, err = target:append(username, id, item, when, with);
				if ok then
					count = count + 1;
				else
					module:log("warn", "Error: %s", err);
					errs = errs + 1;
				end
				if ( count + errs ) % 100 == 0 then
					module:log("info", "%d items migrated, %d errors", count, errs);
				end
			end
			module:log("info", "%d items migrated, %d errors", count, errs);
		end
	end

	if migrate_users then
		for _, username in ipairs(migrate_users) do
			migrate_user(username);
		end
	else
		xpcall(function()
			for username in users(storage, host) do
				migrate_user(username);
			end
		end,
		function (err)
			module:log("error", "Could not list users, you'll have to supply them as arguments");
			module:log("error", "The error was: %s", err);
		end);
	end
end

function module.command(arg)
	local host, source_stores, migrate_to = unpack(arg);
	if not migrate_to then
		return print("Usage: prosodyctl mod_migrate example.com <source-store>[-<store-type>] <target-driver> [users]*");
	end
	if not prosody.hosts[host] then
		return print(("The host %q is not know by Prosody."):format(host));
	end
	sm.initialize_host(host);
	um.initialize_host(host);
	for source_store in source_stores:gmatch("[^,]+") do
		local store_type = source_store:match("%-(%a+)$");
		if store_type then
			source_store = source_store:sub(1, -2-#store_type);
		end
		local migrate_users;
		if arg[4] then
			migrate_users = {};
			for i = 4, #arg do
				migrate_users[i-3] = arg[i];
			end
		end
		if source_store == "pep_data" then
			for store in sm.get_driver(host, source_store):stores(true) do
				if store:match("^pep_") then
					print("Migrating "..store);
					migrate_store(host, store, store_type, migrate_to, migrate_users);
				end
			end
		else
			migrate_store(host, source_store, store_type, migrate_to, migrate_users);
		end
	end
end
