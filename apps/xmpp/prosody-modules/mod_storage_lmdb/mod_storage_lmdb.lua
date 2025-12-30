-- mod_storage_lmdb
-- Copyright (C) 2015 Kim Alvefur
--
-- This file is MIT/X11 licensed.
-- 
-- Depends on lightningdbm
-- https://github.com/shmul/lightningdbm
--
-- luacheck: globals prosody open

local assert = assert;
local select = select;
local xpcall = xpcall;
local traceback = debug.traceback;

local lmdb = require"lightningmdb";
local lfs = require"lfs";
local path = require"util.paths";
local serialization = require"util.serialization";
local serialize = serialization.serialize;
local deserialize = serialization.deserialize;

local function transaction(env, flag, func, ...)
	local args, n_args = {...}, select("#", ...);
	local t = env:txn_begin(nil, flag);
	local function f() return func(t, unpack(args, 1, n_args)); end
	local success, a, b, c = xpcall(f, traceback);
	if not success then
		t:abort();
		return success, a;
	end
	local ok, err = t:commit();
	if not ok then
		return ok, err;
	end
	return success, a, b, c;
end

local function keyvalue_set(t, db, key, value)
	if value ~= nil then
		return assert(t:put(db, key, value, 0));
	else
		return t:del(db, key, value);
	end
end

local function keyvalue_get(t, db, key)
	local data, err = t:get(db, key, 0);
	assert(data or not err, err);
	return data;
end

local drivers = {};
local provider = {};

local keyval = {};
local keyval_mt = { __index = keyval, flags = lmdb.MDB_CREATE };
drivers.keyval = keyval_mt;

function keyval:set(key, value)
	if type(value) == "table" and next(value) == nil then
		value = nil;
	end
	if value ~= nil then
		value = serialize(value);
	end
	return transaction(self.env, 0, keyvalue_set, self.db, key, value);
end

function keyval:get(key)
	local ok, data = transaction(self.env, lmdb.MDB_RDONLY, keyvalue_get, self.db, key);
	if not ok then return ok, data; end
	return deserialize(data);
end

function provider:init(config)
	if config.base_path then
		lfs.mkdir(config.base_path);
	end
	local env = lmdb.env_create();
	env:set_maxdbs(config.maxdbs or 20);
	local env_flags = 0;
	if config.flags then
		for flag in config.flags do
			env_flags = env_flags + assert(lmdb["MDB_"..flag:upper()], "No such flag "..flag);
		end
	end
	env:open(config.base_path or ".", env_flags, tonumber("640", 8));
	self.env = env;
end

function provider:open(store, typ)
	typ = typ or "keyval";
	local driver_mt = drivers[typ];
	if not driver_mt then
		return nil, "unsupported-store";
	end
	local env = self.env;
	local t = env:txn_begin(nil, 0);
	local db = t:dbi_open(store.."_"..typ, driver_mt.flags);
	local ok, err = t:commit();
	if not ok then
		module:log("error", "Could not open database %s_%s: %s", store, typ, tostring(err));
		return ok, err;
	end

	return setmetatable({ env = env, store = store, type = typ, db = db }, driver_mt);
end

if prosody then
	provider:init({
		base_path = path.resolve_relative_path(prosody.paths.data, module.host);
		flags = module:get_option_set("lmdb_flags", {});
		maxdbs = module:get_option_number("lmdb_maxdbs", 20);
	});

	function module.unload() --luacheck: ignore
		provider.env:sync(1);
		provider.env:close();
	end

	module:provides("storage", provider);
else
	return provider;
end
