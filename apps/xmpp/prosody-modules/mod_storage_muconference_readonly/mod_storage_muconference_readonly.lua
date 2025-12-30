
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

local default_params = { driver = "MySQL" };

local engine;

local host = module.host;
local room, store;

local function get_best_affiliation(a, b)
	if a == 'owner' or b == 'owner' then
		return 'owner';
	elseif a == 'administrator' or b == 'administrator' then
		return 'administrator';
	elseif a == 'outcast' or b == 'outcast' then
		return 'outcast';
	elseif a == 'member' or b == 'member' then
		return 'member';
	end
	assert(false);
end

local function keyval_store_get()
	if store == "config" then
		local room_jid = room.."@"..host;
		local result;
		for row in engine:select("SELECT `name`,`desc`,`topic`,`public`,`secret` FROM `rooms` WHERE `jid`=? LIMIT 1", room_jid or "") do result = row end
		local name = result[1];
		local desc = result[2];
		local subject = result[3];
		local public = result[4];
		local hidden = public == 0 and true or nil;
		local secret = result[5];
		if secret == '' then secret = nil end
		local affiliations = {};
		for row in engine:select("SELECT `jid_user`,`affil` FROM `rooms_lists` WHERE `jid_room`=?", room_jid or "") do
			local jid_user = row[1];
			local affil = row[2];
			-- mu-conference has a bug where full JIDs get stored…
			local bare_jid = jid_user:gsub('/.*', '');
			local old_affil = affiliations[bare_jid];
			-- mu-conference has a bug where it can record multiple affiliations…
			if old_affil ~= nil and old_affil ~= affil then
				affil = get_best_affiliation(old_affil, affil);
			end
			-- terminology is clearly “admin”, not “administrator”.
			if affil == 'administrator' then
				affil = 'admin';
			end
			affiliations[bare_jid] = affil;
		end
		return {
			jid = room_jid,
			_data = {
				persistent = true,
				name = name,
				description = desc,
				subject = subject,
				password = secret,
				hidden = hidden,
			},
			_affiliations = affiliations,
		};
	end
end

--- Key/value store API (default store type)

local keyval_store = {};
keyval_store.__index = keyval_store;
function keyval_store:get(roomname)
	room, store = roomname, self.store;
	local ok, result = engine:transaction(keyval_store_get);
	if not ok then
		module:log("error", "Unable to read from database %s store for %s: %s", store, roomname or "<host>", result);
		return nil, result;
	end
	return result;
end

function keyval_store:users()
	local host_length = host:len() + 1;
	local ok, result = engine:transaction(function()
		return engine:select("SELECT SUBSTRING_INDEX(jid, '@', 1) FROM `rooms`");
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

function driver:stores(roomname)
	local query = "SELECT 'config'";
	if roomname == true or not roomname then
		roomname = "";
	end
	local ok, result = engine:transaction(function()
		return engine:select(query, host, roomname);
	end);
	if not ok then return ok, result end
	return iterator(result);
end

--- Initialization


local function normalize_params(params)
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
