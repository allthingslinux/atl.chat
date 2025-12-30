-- Wordpress authentication backend for Prosody
--
-- Copyright (C) 2011 Waqas Hussain
-- Copyright (C) 2011 Kim Alvefur
--

local log = require "util.logger".init("auth_sql");
local new_sasl = require "util.sasl".new;
local nodeprep = require "util.encodings".stringprep.nodeprep;
local saslprep = require "util.encodings".stringprep.saslprep;
local DBI = require "DBI"
local md5 = require "util.hashes".md5;
local uuid_gen = require "util.uuid".generate;

local connection;
local params = module:get_option("sql");
local table_prefix = module:get_option_string("wordpress_table_prefix", "wp_");

local resolve_relative_path = require "core.configmanager".resolve_relative_path;

local function test_connection()
	if not connection then return nil; end
	if connection:ping() then
		return true;
	else
		module:log("debug", "Database connection closed");
		connection = nil;
	end
end
local function connect()
	if not test_connection() then
		prosody.unlock_globals();
		local dbh, err = DBI.Connect(
			params.driver, params.database,
			params.username, params.password,
			params.host, params.port
		);
		prosody.lock_globals();
		if not dbh then
			module:log("debug", "Database connection failed: %s", tostring(err));
			return nil, err;
		end
		module:log("debug", "Successfully connected to database");
		dbh:autocommit(true); -- don't run in transaction
		connection = dbh;
		return connection;
	end
end

do -- process options to get a db connection
	params = params or { driver = "SQLite3" };

	if params.driver == "SQLite3" then
		params.database = resolve_relative_path(prosody.paths.data or ".", params.database or "prosody.sqlite");
	end

	assert(params.driver and params.database, "Both the SQL driver and the database need to be specified");

	assert(connect());
end

local function getsql(sql, ...)
	if params.driver == "PostgreSQL" then
		sql = sql:gsub("`", "\"");
	end
	if not test_connection() then connect(); end
	-- do prepared statement stuff
	local stmt, err = connection:prepare(sql);
	if not stmt and not test_connection() then error("connection failed"); end
	if not stmt then module:log("error", "QUERY FAILED: %s %s", err, debug.traceback()); return nil, err; end
	-- run query
	local ok, err = stmt:execute(...);
	if not ok and not test_connection() then error("connection failed"); end
	if not ok then return nil, err; end

	return stmt;
end
local function setsql(sql, ...)
	local stmt, err = getsql(sql, ...);
	if not stmt then return stmt, err; end
	return stmt:affected();
end

local function get_password(username)
	local stmt, err = getsql("SELECT `user_pass` FROM `"..table_prefix.."users` WHERE `user_login`=?", username);
	if stmt then
		for row in stmt:rows(true) do
			return row.user_pass;
		end
	end
end


local itoa64 = "./0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz";
local function hashEncode64(input, count)
	local output = "";
	local i, value = 0, 0;

	while true do
		value = input:byte(i+1)
		i = i+1;
		local idx = value % 0x40 + 1;
		output = output .. itoa64:sub(idx, idx);

		if i < count then
			value = value + input:byte(i+1) * 256;
		end
		local _ = value % (2^6);
		local idx = ((value - _) / (2^6)) % 0x40 + 1
		output = output .. itoa64:sub(idx, idx);

		if i >= count then break; end
		i = i+1;

		if i < count then
			value = value + input:byte(i+1) * 256 * 256;
		end
		local _ = value % (2^12);
		local idx = ((value - _) / (2^12)) % 0x40 + 1
		output = output .. itoa64:sub(idx, idx);

		if i >= count then break; end
		i = i+1;

		local _ = value % (2^18);
		local idx = ((value - _) / (2^18)) % 0x40 + 1
		output = output .. itoa64:sub(idx, idx);

		if not(i < count) then break; end
	end
	return output;
end
local function hashCryptPrivate(password, genSalt)
	local output = "*";
	if not genSalt:match("^%$P%$") then return output; end

	local count_log2 = itoa64:find(genSalt:sub(4,4)) - 1;
	if count_log2 < 7 or count_log2 > 30 then return output; end

	local count = 2 ^ count_log2;
	local salt = genSalt:sub(5, 12);

	if #salt ~= 8 then return output; end

	local hash = md5(salt..password);

	while true do
		hash = md5(hash..password);
		if not(count > 1) then break; end
		count = count-1;
	end

	output = genSalt:sub(1, 12);
	output = output .. hashEncode64(hash, 16);

	return output;
end
local function hashGensaltPrivate(input)
	local iteration_count_log2 = 6;
	local output = "$P$";
	local idx = math.min(iteration_count_log2 + 5, 30) + 1;
	output = output .. itoa64:sub(idx, idx);
	output = output .. hashEncode64(input, 6);
	return output;
end
local function wordpressCheckHash(password, hash)
	if #hash == 32 then return hash == md5(password, true); end
	return #hash == 34 and hashCryptPrivate(password, hash) == hash;
end
local function wordpressCreateHash(password)
	local random = uuid_gen():sub(-6);
	local salt = hashGensaltPrivate(random);
	local hash = hashCryptPrivate(password, salt);
	if #hash == 34 then return hash; end
	return md5(password, true);
end


provider = {};

function provider.test_password(username, password)
	local hash = get_password(username);
	return hash and wordpressCheckHash(password, hash);
end
function provider.user_exists(username)
	module:log("debug", "test user %s existence", username);
	return get_password(username) and true;
end

function provider.get_password(username)
	return nil, "Getting password is not supported.";
end
function provider.set_password(username, password)
	local hash = wordpressCreateHash(password);
	local stmt, err = setsql("UPDATE `"..table_prefix.."users` SET `user_pass`=? WHERE `user_login`=?", hash, username);
	return stmt and true, err;
end
function provider.create_user(username, password)
	return nil, "Account creation/modification not supported.";
end

local escapes = {
	[" "] = "\\20";
	['"'] = "\\22";
	["&"] = "\\26";
	["'"] = "\\27";
	["/"] = "\\2f";
	[":"] = "\\3a";
	["<"] = "\\3c";
	[">"] = "\\3e";
	["@"] = "\\40";
	["\\"] = "\\5c";
};
local unescapes = {};
for k,v in pairs(escapes) do unescapes[v] = k; end
local function jid_escape(s) return s and (s:gsub(".", escapes)); end
local function jid_unescape(s) return s and (s:gsub("\\%x%x", unescapes)); end

function provider.get_sasl_handler()
	local sasl = {};
	function sasl:clean_clone() return provider.get_sasl_handler(); end
	function sasl:mechanisms() return { PLAIN = true; }; end
	function sasl:select(mechanism)
		if not self.selected and mechanism == "PLAIN" then
			self.selected = mechanism;
			return true;
		end
	end
	function sasl:process(message)
		if not message then return "failure", "malformed-request"; end
		local authorization, authentication, password = message:match("^([^%z]*)%z([^%z]+)%z([^%z]+)");
		if not authorization then return "failure", "malformed-request"; end
		authentication = saslprep(authentication);
		password = saslprep(password);
		if (not password) or (password == "") or (not authentication) or (authentication == "") then
			return "failure", "malformed-request", "Invalid username or password.";
		end
		local function test(authentication)
			local prepped = nodeprep(authentication);
			local normalized = jid_unescape(prepped);
			return normalized and provider.test_password(normalized, password) and prepped;
		end
		local username = test(authentication) or test(jid_escape(authentication));
		if username then
			self.username = username;
			return "success";
		end
		return "failure", "not-authorized", "Unable to authorize you with the authentication credentials you've sent.";
	end
	return sasl;
end

module:provides("auth", provider);

