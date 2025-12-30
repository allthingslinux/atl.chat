
-- luacheck: ignore 212/self

local sql = require "util.sql";
local xml_parse = require "util.xml".parse;
local resolve_relative_path = require "util.paths".resolve_relative_path;
local stanza_preserialize = require "util.stanza".preserialize;

local unpack = unpack
local function iterator(result)
	return function(result_)
		local row = result_();
		if row ~= nil then
			return unpack(row);
		end
	end, result, nil;
end

local default_params = { driver = "SQLite3" };

local engine;

local host = module.host;
local user, store;

local function keyval_store_get()
	if store == "accounts" then
		--for row in engine:select("SELECT \"password\",\"created_at\" FROM \"users\" WHERE \"username\"=?", user or "") do
		local result;
		for row in engine:select("SELECT \"password\" FROM \"users\" WHERE \"username\"=? LIMIT 1", user or "") do result = row end
		local password = result[1];
		--local created_at = result[2];
		return { password = password };

	elseif store == "roster" then
		local roster = {};
		local pending = nil;
		--for row in engine:select("SELECT \"jid\",\"nick\",\"subscription\",\"ask\",\"askmessage\",\"server\",\"subscribe\",\"type\",\"created_at\" FROM \"rosterusers\" WHERE \"username\"=?", user or "") do
		for row in engine:select("SELECT \"jid\",\"nick\",\"subscription\",\"ask\" FROM \"rosterusers\" WHERE \"username\"=?", user or "") do
			local contact = row[1];
			local name = row[2];
			if name == "" then name = nil; end
			local subscription = row[3];
			if subscription == "N" then
				subscription = "none"
			elseif subscription == "B" then
				subscription = "both"
			elseif subscription == "F" then
				subscription = "from"
			elseif subscription == "T" then
				subscription = "to"
			else error("Unknown subscription type: "..subscription) end;
			local ask = row[4];
			if ask == "N" then
				ask = nil;
			elseif ask == "O" then
				ask = "subscribe";
			elseif ask == "I" then
				if pending == nil then pending = {} end;
				pending[contact] = true;
				ask = nil;
			elseif ask == "B" then
				if pending == nil then pending = {} end;
				pending[contact] = true;
				ask = "subscribe";
			else error("Unknown ask type: "..ask); end

			--local askmessage = row[5];
			--local server = row[6];
			--local subscribe = row[7];
			--local type = row[8];
			--local created_at = row[9];

			local groups = {};
			for row in engine:select("SELECT \"grp\" FROM \"rostergroups\" WHERE \"username\"=? AND \"jid\"=?", user or "", contact) do
				local group = row[1];
				groups[group] = true;
			end

			roster[contact] = { name = name, ask = ask, subscription = subscription, groups = groups };
		end
		return roster;

	elseif store == "vcard" then
		local result = nil;
		for row in engine:select("SELECT \"vcard\" FROM \"vcard\" WHERE \"username\"=? LIMIT 1", user or "") do result = row end
		if not result then
			return nil;
		end
		local data, err = xml_parse(result[1]);
		if data then
			return stanza_preserialize(data);
		end

	elseif store == "private" then
		local private = nil;
		local result;
		for row in engine:select("SELECT \"namespace\",\"data\" FROM \"private_storage\" WHERE \"username\"=?", user or "") do
			if private == nil then private = {} end;
			local namespace = row[1];
			local data, err = xml_parse(row[2]);
			if data then
				assert(namespace == data.attr.xmlns, "Wrong namespace in private data!");
				local key = data.name..":"..data.attr.xmlns;
				private[key] = stanza_preserialize(data);
			end
		end
		return private;
	end
end

--- Key/value store API (default store type)

local keyval_store = {};
keyval_store.__index = keyval_store;
function keyval_store:get(username)
	user, store = username, self.store;
	local ok, result = engine:transaction(keyval_store_get);
	if not ok then
		module:log("error", "Unable to read from database %s store for %s: %s", store, username or "<host>", result);
		return nil, result;
	end
	return result;
end

function keyval_store:users()
	local ok, result = engine:transaction(function()
		return engine:select("SELECT \"username\" FROM \"users\"");
	end);
	if not ok then return ok, result end
	return iterator(result);
end

local stores = {
	keyval = keyval_store;
};

--- Implement storage driver API

-- FIXME: Some of these operations need to operate on the archive store(s) too

local driver = {};

function driver:open(store, typ)
	local store_mt = stores[typ or "keyval"];
	if store_mt then
		return setmetatable({ store = store }, store_mt);
	end
	return nil, "unsupported-store";
end

function driver:stores(username)
	local query = "SELECT 'accounts', 'roster', 'vcard', 'private'";
	if username == true or not username then
		username = "";
	end
	local ok, result = engine:transaction(function()
		return engine:select(query, host, username);
	end);
	if not ok then return ok, result end
	return iterator(result);
end

--- Initialization


local function normalize_params(params)
	if params.driver == "SQLite3" then
		if params.database ~= ":memory:" then
			params.database = resolve_relative_path(prosody.paths.data or ".", params.database or "prosody.sqlite");
		end
	end
	assert(params.driver and params.database, "Configuration error: Both the SQL driver and the database need to be specified");
	return params;
end

function module.load()
	if prosody.prosodyctl then return; end
	local engines = module:shared("/*/sql/connections");
	local params = normalize_params(module:get_option("sql", default_params));
	engine = engines[sql.db2uri(params)];
	if not engine then
		module:log("debug", "Creating new engine");
		engine = sql:create_engine(params);
		engines[sql.db2uri(params)] = engine;
	end

	module:provides("storage", driver);
end
