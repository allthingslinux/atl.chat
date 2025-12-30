-- mod_storage_multi

local storagemanager = require"core.storagemanager";
local backends = module:get_option_array(module.name); -- TODO better name?

-- TODO migrate data "upwards"

-- one → one successful write is success
-- all → all backends must report success
-- majority → majority of backends must report success
local policy = module:get_option_string(module.name.."_policy", "all");

local keyval_store = {};
keyval_store.__index = keyval_store;

function keyval_store:get(username)
	local backends = self.backends;
	local data, err;
	for i = 1, #backends do
		module:log("debug", "%s:%s:get(%q)", tostring(backends[i].get), backends[i]._store, username);
		data, err = backends[i]:get(username);
		if err then
			module:log("error", tostring(err));
		elseif not data then
			module:log("debug", "No data returned");
		else
			module:log("debug", "Data returned");
			return data, err;
		end
	end
end

-- This is where it gets complicated
function keyval_store:set(username, data)
	local backends = self.backends;
	local ok, err, backend;
	local all, one, oks = true, false, 0;
	for i = 1, #backends do
		backend = backends[i];
		module:log("debug", "%s:%s:set(%q)", tostring(backends[i].get), backends[i].store, username);
		ok, err = backend:set(username, data);
		if not ok then
			module:log("error", "Error in storage driver %s: %s", backend.name, tostring(err));
		else
			oks = oks + 1;
		end
		one = one or ok; -- At least one successful write
		all = all and ok; -- All successful
	end
	if policy == "all" then
		return all, err
	elseif policy == "majority" then
		return oks > (#backends/2), err;
	end
	-- elseif policy == "one" then
	return one, err;
end

local stores = {
	keyval = keyval_store;
}

local driver = {};

function driver:open(store, typ)
	local store_mt = stores[typ or "keyval"];
	if store_mt then
		local my_backends = {};
		local driver, opened
		for i = 1, #backends do
			 driver = storagemanager.load_driver(module.host, backends[i]);
			 opened = driver:open(store, typ);
			 my_backends[i] = assert(driver:open(store, typ));
			 my_backends[i]._store = store;
		end
		return setmetatable({ backends = my_backends }, store_mt);
	end
	return nil, "unsupported-store";
end

module:provides("storage", driver);
