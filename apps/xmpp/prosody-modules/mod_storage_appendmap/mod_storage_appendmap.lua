local dump = require "util.serialization".serialize;
local load = require "util.envload".envloadfile;
local datetime = require "util.datetime".datetime;
local dm = require "core.storagemanager".olddm;

local REMOVE = {}; -- Special value for removing keys

local driver = {};

local timestamps = module:get_option_boolean("appendmap_timestamps", true);

local keywords = {
	["do"] = true; ["and"] = true; ["else"] = true; ["break"] = true;
	["if"] = true; ["end"] = true; ["goto"] = true; ["false"] = true;
	["in"] = true; ["for"] = true; ["then"] = true; ["local"] = true;
	["or"] = true; ["nil"] = true; ["true"] = true; ["until"] = true;
	["elseif"] = true; ["function"] = true; ["not"] = true;
	["repeat"] = true; ["return"] = true; ["while"] = true;

	-- _ENV is not technically a keyword but we need to treat it as such
	["_ENV"] = true;
};

local function is_usable_identifier(s)
	return type(s) == "string" and not keywords[s] and s:find("^[%a_][%w_]*$");
end

local function serialize_key(key)
	if is_usable_identifier(key) then
		return key;
	else
		return "_ENV[" .. dump(key) .. "]";
	end
end

local function serialize_value(value)
	if value == REMOVE then
		return "nil";
	else
		return dump(value);
	end
end

local function serialize_pair(key, value)
	key = serialize_key(key);
	value = serialize_value(value);
	return key .. " = " .. value .. ";\n";
end

local function serialize_map(keyvalues)
	local keys, values = {}, {};
	for key, value in pairs(keyvalues) do
		key = serialize_key(key);
		value = serialize_value(value);
		table.insert(keys, key);
		table.insert(values, value);
	end
	return table.concat(keys, ", ") .. " = " .. table.concat(values, ", ") .. ";\n";
end

local map = { remove = REMOVE };
local map_mt = { __index = map };

function map:get(user, key)
	module:log("debug", "map:get(%s, %s)", tostring(user), tostring(key))
	local filename = dm.getpath(user, module.host, self.store, "map");
	module:log("debug", "File is %s", filename);
	local env = {};
	if _VERSION == "Lua 5.1" then -- HACK
		env._ENV = env; -- HACK
	end -- SO MANY HACKS
	local chunk, err, errno = load(filename, env);
	if not chunk then if errno == 2 then return end return chunk, err; end
	local ok, err = pcall(chunk);
	if not ok then return ok, err; end
	if _VERSION == "Lua 5.1" then -- HACK
		env._ENV = nil; -- HACK
	end -- HACKS EVERYWHERE
	if key == nil then
		return env;
	end
	return env[key];
end

function map:set_keys(user, keyvalues)
	local data = serialize_map(keyvalues);
	if timestamps then
		data = "-- " .. datetime() .. "\n" .. data;
	end
	return dm.append_raw(user, module.host, self.store, "map", data);
end

function map:set(user, key, value)
	if _VERSION == "Lua 5.1" then
		assert(key ~= "_ENV", "'_ENV' is a restricted key");
	end
	if key == nil then
		local filename = dm.getpath(user, module.host, self.store, "map");
		return os.remove(filename);
	end
	local data = serialize_pair(key, value);
	if timestamps then
		data = "-- " .. datetime() .. "\n" .. data;
	end
	return dm.append_raw(user, module.host, self.store, "map", data);
end

function map:items()
	return dm.users(module.host, self.store, "map");
end

local keyval = { remove = REMOVE };
local keyval_mt = { __index = keyval };

function keyval:get(user)
	return map.get(self, user, nil);
end

function keyval:set(user, keyvalues)
	local data = serialize_map(keyvalues);
	if timestamps then
		data = "-- " .. datetime() .. "\n" .. data;
	end
	return dm.store_raw(dm.getpath(user, module.host, self.store, "map"), data);
end

function keyval:users()
	return dm.users(module.host, self.store, "map");
end

-- TODO some kind of periodic compaction thing?
function map:_compact(user)
	local data = self:get(user);
	return keyval.set(self, user, data);
end

function driver:open(store, typ)
	if typ == "map" then
		return setmetatable({ store = store, }, map_mt);
	elseif typ == nil or typ == "keyval" then
		return setmetatable({ store = store, }, keyval_mt);
	end
	return nil, "unsupported-store";
end

module:provides("storage", driver);

