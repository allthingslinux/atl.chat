
local http = require "socket.http";
local url = require "socket.url";

local couchapi = module:require("couchdb/couchapi");
local json = module:require("couchdb/json");

local couchdb_url = assert(module:get_option("couchdb_url"), "Option couchdb_url not specified");
local db = couchapi.db(couchdb_url);

local function couchdb_get(key)
	local a,b = db:doc(key):get()
	print(json.encode(a));
	if b == 404 then return nil; end
	if b == 200 then b = nil; end
	return a.payload,b;
end

local function couchdb_put(key, value)
	local a,b = db:doc(key):get();
	return db:doc(key):put({ payload = value, _rev = a and a._rev });
end

local st = require "util.stanza";

local handlers = {};

handlers.accounts = {
	get = function(self, user)
		return couchdb_get(self.host.."/"..user.."/account");
	end;
	set = function(self, user, data)
		return couchdb_put(self.host.."/"..user.."/account", data);
	end;
};
handlers.vcard = {
	get = function(self, user)
		return couchdb_get(self.host.."/"..user.."/vcard");
	end;
	set = function(self, user, data)
		return couchdb_put(self.host.."/"..user.."/vcard", data);
	end;
};
handlers.private = {
	get = function(self, user)
		return couchdb_get(self.host.."/"..user.."/private");
	end;
	set = function(self, user, data)
		return couchdb_put(self.host.."/"..user.."/private", data);
	end;
};
handlers.roster = {
	get = function(self, user)
		return couchdb_get(self.host.."/"..user.."/roster");
	end;
	set = function(self, user, data)
		return couchdb_put(self.host.."/"..user.."/roster", data);
	end;
};

-----------------------------
local driver = {};
driver.__index = driver;

function driver:open(host, datastore, typ)
	local cache_key = host.." "..datastore;
	if self.ds_cache[cache_key] then return self.ds_cache[cache_key]; end
	local instance = setmetatable({}, self);
	instance.host = host;
	instance.datastore = datastore;
	local handler = handlers[datastore];
	if not handler then return nil; end
	for key,val in pairs(handler) do
		instance[key] = val;
	end
	if instance.init then instance:init(); end
	self.ds_cache[cache_key] = instance;
	return instance;
end

-----------------------------
local _M = {};

function _M.new()
	local instance = setmetatable({}, driver);
	instance.__index = instance;
	instance.ds_cache = {};
	return instance;
end

return _M;
