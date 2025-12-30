
local setmetatable = setmetatable;
local pcall = pcall;
local type = type;
local t_concat = table.concat;
local print = print;

local socket_url = require "socket.url";
local http = require "socket.http";
local ltn12 = require "ltn12";

--local json = require "json";
local json = module:require("couchdb/json");

--module("couchdb")
local _M = {};

local function urlcat(url, path)
	return url:gsub("/*$", "").."/"..path:gsub("^/*", "");
end

local doc_mt = {};
doc_mt.__index = doc_mt;

function doc_mt:get()
	return self.db:get(socket_url.escape(self.id));
end
function doc_mt:put(val)
	return self.db:put(socket_url.escape(self.id), val);
end
function doc_mt:__tostring()
	return "couchdb.doc("..self.url..")";
end


local db_mt = {};
db_mt.__index = db_mt;

function db_mt:__tostring()
	return "couchdb.db("..self.url..")";
end
function db_mt:doc(id)
	local url = urlcat(self.url, socket_url.escape(id));
	return setmetatable({ url = url, db = self, id = id }, doc_mt);
end
function db_mt:get(id)
	local url = urlcat(self.url, id);
	local a,b = http.request(url);
	local r,x = pcall(json.decode, a);
	if r then a = x; end
	return a,b;
end
function db_mt:put(id, value)
	local url = urlcat(self.url, id);
	if type(value) == "table" then
		value = json.encode(value);
	elseif value ~= nil and type(value) ~= "string" then
		return nil, "Invalid type";
	end
	local t = {};
	local a,b = http.request {
		url = url,
		sink = ltn12.sink.table(t),
		source = ltn12.source.string(value),
		method = "PUT",
		headers = {
			["Content-Length"] = #value,
			["Content-Type"] = "application/json"
		}
	};
	a = t_concat(t);
	local r,x = pcall(json.decode, a);
	if r then a = x; end
	return a,b;
end


local server_mt = {};
server_mt.__index = server_mt;

function server_mt:db(name)
	local url = urlcat(self.url, socket_url.escape(name));
	return setmetatable({ url = url }, db_mt);
end
function server_mt:__tostring()
	return "couchdb.server("..self.url..")";
end


function _M.server(url)
	return setmetatable({ url = url }, server_mt);
end
function _M.db(url)
	return setmetatable({ url = url }, db_mt);
end

return _M;
