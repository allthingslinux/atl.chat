-- Prosody IM
--
-- mod_admin_message -- Console-over-XMPP implementation.
--
-- This module depends on Prosody's admin_telnet module
--
-- Copyright (C) 2008-2010 Matthew Wild
-- Copyright (C) 2008-2010 Waqas Hussain
-- Copyright (C) 2012-2013 Mikael Berthe
--
-- This project is MIT/X11 licensed. Please see the
-- COPYING file in the source package for more information.
--

local st = require "util.stanza";
local um_is_admin = require "core.usermanager".is_admin;

local admin_telnet = module:depends("admin_telnet");
local telnet_def_env = module:shared("/*/admin_telnet/env");
local telnet_commands = module:shared("/*/admin_telnet/commands");
local default_env_mt = { __index = telnet_def_env };

local host = module.host;

-- Create our own session.  print() will store the results in a text
-- string.  send(), quit(), disconnect() are no-op.
local function new_session ()
	local session = {
			send        = function ()  end;
			quit        = function ()  end;
			disconnect  = function ()  end;
			};

	session.print = function (...)
		local t = {};
		for i=1,select("#", ...) do
			t[i] = tostring(select(i, ...));
		end
		local text = "| "..table.concat(t, "\t");
		if session.fulltext then
		    session.fulltext = session.fulltext .. "\n" .. text;
		else
		    session.fulltext = text;
		end
	end

	session.env = setmetatable({}, default_env_mt);

	-- Load up environment with helper objects
	for name, t in pairs(telnet_def_env) do
		if type(t) == "table" then
			session.env[name] = setmetatable({ session = session },
							 { __index = t });
		end
	end

	return session;
end

local function on_message(event)
	-- Check the type of the incoming stanza to avoid loops:
	if event.stanza.attr.type == "error" then
		return; -- We do not want to reply to these, so leave.
	end

	local userjid = event.stanza.attr.from;
	local bodytag = event.stanza:get_child("body");
	local body = bodytag and bodytag:get_text() or "";
	if not body or body == "" then
		-- We do not reply to empty messages (chatstates, etc.)
		return true;
	end

	-- Check the requester is an admin user
	if not um_is_admin(userjid, module.host) then
		module:log("info", "Ignored request from non-admin: %s",
			   userjid);
		return;
	end

	-- Create a session in order to use an admin_telnet-like environment
	local session = new_session();

	-- Process the message using admin_telnet's onincoming function
	admin_telnet.console:process_line(session, body.."\n");

	-- Strip trailing blank line
	session.fulltext = tostring(session.fulltext):gsub("\n|%s*$", "")

	-- Send the reply stanza
	local reply_stanza = st.message({ from = host, to = userjid,
					type = "chat" }, session.fulltext);
	module:send(reply_stanza);

	return true;
end

local function on_presence(event)

	local send_presence = false;

	local userjid = event.stanza.attr.from;

	-- Check the requester is an admin user
	if not um_is_admin(userjid, module.host) then
		module:log("info", "Ignored presence from non-admin: %s",
			   userjid);
		return;
	end

	if (event.stanza.attr.type == "subscribe") then
		module:log("info", "Subscription request from %s", userjid);
		send_presence = true;
		-- Send a subscription ack
		local presence_stanza = st.presence({ from = host,
					to = userjid, type = "subscribed",
					id = event.stanza.attr.id });
		module:send(presence_stanza);
	elseif (event.stanza.attr.type == "probe") then
		send_presence = true;
	elseif (event.stanza.attr.type == "unsubscribe") then
		-- For information only...
		module:log("info", "Unsubscription request from %s", userjid);
	end

	if (send_presence == true) then
		-- Send a presence stanza
		module:send(st.presence({ from = host, to = userjid }));
	end
	return true;
end

module:hook("message/bare", on_message);
module:hook("presence/bare", on_presence);
