-- Based on mod_mam_sql
-- Copyright (C) 2011-2012 Kim Alvefur
--
-- This file is MIT/X11 licensed.

local st = require "util.stanza";
local jid_bare = require "util.jid".bare;
local jid_split = require "util.jid".split;

local serialize = require"util.json".encode, require"util.json".decode;
local tostring = tostring;
local time_now = os.time;


local table_name = module:get_option("message_log_sql_table", pcall(require, "util.cache") and "messages" or "prosodyarchive");

local sql, setsql, getsql = {};
do -- SQL stuff
local connection;
local resolve_relative_path = require "core.configmanager".resolve_relative_path;
local params = module:get_option("message_log_sql", module:get_option("sql"));


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
		dbh:autocommit(false); -- don't commit automatically
		connection = dbh;

	end
	return connection;
end


do -- process options to get a db connection
	local ok;
	prosody.unlock_globals();
	ok, DBI = pcall(require, "DBI");
	if not ok then
		package.loaded["DBI"] = {};
		module:log("error", "Failed to load the LuaDBI library for accessing SQL databases: %s", DBI);
		module:log("error", "More information on installing LuaDBI can be found at http://prosody.im/doc/depends#luadbi");
	end
	prosody.lock_globals();
	if not ok or not DBI.Connect then
		return; -- Halt loading of this module
	end

	params = params or { driver = "SQLite3" };

	if params.driver == "SQLite3" then
		params.database = resolve_relative_path(prosody.paths.data or ".", params.database or "prosody.sqlite");
	end

	assert(params.driver and params.database, "Both the SQL driver and the database need to be specified");

	assert(connect());

end

function getsql(sql, ...)
	if params.driver == "PostgreSQL" then
		sql = sql:gsub("`", "\"");
	end
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
function setsql(sql, ...)
	local stmt, err = getsql(sql, ...);
	if not stmt then return stmt, err; end
	return stmt:affected();
end
function sql.rollback(...)
	if connection then connection:rollback(); end -- FIXME check for rollback error?
	return ...;
end
function sql.commit(...)
	local ok, err = connection:commit();
	if not ok then
		module:log("error", "SQL commit failed: %s", tostring(err));
		return nil, "SQL commit failed: "..tostring(err);
	end
	return ...;
end

end

-- Handle messages
local function message_handler(event, c2s)
	local origin, stanza = event.origin, event.stanza;
	local orig_type = stanza.attr.type or "normal";
	local orig_to = stanza.attr.to;
	local orig_from = stanza.attr.from;

	if not orig_from and c2s then
		orig_from = origin.full_jid;
	end
	orig_to = orig_to or orig_from; -- Weird corner cases

	-- Don't store messages of these types
	if orig_type == "error"
	or orig_type == "headline"
	or orig_type == "groupchat"
	or not stanza:get_child("body") then
		return;
		-- TODO Maybe headlines should be configurable?
	end

	local store_user, store_host = jid_split(c2s and orig_from or orig_to);
	local target_jid = c2s and orig_to or orig_from;
	local target_bare = jid_bare(target_jid);
	local _, _, target_resource = jid_split(target_jid);

	--local id = uuid();
	local when = time_now();
	-- And stash it
	local ok, err = setsql([[
	INSERT INTO `]]..table_name..[[`
	(`host`, `user`, `store`, `when`, `with`, `resource`, `stanza`)
	VALUES (?, ?, ?, ?, ?, ?, ?);
	]], store_host, store_user, "message_log", when, target_bare, target_resource, serialize(st.preserialize(stanza)))
	if ok then
		sql.commit();
	else
		module:log("error", "SQL error: %s", err);
		sql.rollback();
	end
end

local function c2s_message_handler(event)
	return message_handler(event, true);
end

-- Stanzas sent by local clients
module:hook("pre-message/bare", c2s_message_handler, 2);
module:hook("pre-message/full", c2s_message_handler, 2);
-- Stanszas to local clients
module:hook("message/bare", message_handler, 2);
module:hook("message/full", message_handler, 2);

-- In the telnet console, run:
-- >hosts["this host"].modules.mam_sql.environment.create_sql()
function create_sql()
	local stm = assert(getsql([[
	CREATE TABLE `]]..table_name..[[` (
		`host` TEXT,
		`user` TEXT,
		`store` TEXT,
		`id` INTEGER PRIMARY KEY AUTOINCREMENT,
		`when` INTEGER,
		`with` TEXT,
		`resource` TEXT,
		`stanza` TEXT
	);
	CREATE INDEX `hus` ON `]]..table_name..[[` (`host`, `user`, `store`);
	CREATE INDEX `with` ON `]]..table_name..[[` (`with`);
	CREATE INDEX `thetime` ON `]]..table_name..[[` (`when`);
	]]));
	stm:execute();
	sql.commit();
end
