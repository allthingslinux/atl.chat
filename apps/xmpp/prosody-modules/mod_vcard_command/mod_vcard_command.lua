-----------------------------------------------------------
-- mod_vcard_command: Manage vcards through prosodyctl
-- version 0.02
-----------------------------------------------------------
-- Copyright (C) 2013 Stefan `Sec` Zehl
--
-- This project is MIT/X11 licensed. Please see the
-- COPYING file in the source package for more information.
-----------------------------------------------------------

function module.load()
        module:log("error", "Do not load this module in Prosody");
        module.host = "*";
        return;
end


-- Workaround for lack of util.startup...
_G.bare_sessions = _G.bare_sessions or {};

local storagemanager = require "core.storagemanager";
local datamanager = require "util.datamanager";
local xml = require "util.xml";
local jid = require "util.jid";
local warn = prosodyctl.show_warning;
local st = require "util.stanza"
-- local vcards = module:open_store("vcard");

-- Print anything - including nested tables
function table_print (tt, indent, done)
  done = done or {}
  indent = indent or 0
  if type(tt) == "table" then
    for key, value in pairs (tt) do
      io.write(string.rep (" ", indent)) -- indent it
      if type (value) == "table" and not done [value] then
        done [value] = true
        io.write(string.format("[%s] => table\n", tostring (key)));
        io.write(string.rep (" ", indent+4)) -- indent it
        io.write("(\n");
        table_print (value, indent + 7, done)
        io.write(string.rep (" ", indent+4)) -- indent it
        io.write(")\n");
      else
        io.write(string.format("[%s] => %s\n",
            tostring (key), tostring(value)))
      end
    end
  else
    io.write(tt .. "\n")
  end
end

-- Make a *one-way* subscription. User will see when contact is online,
-- contact will not see when user is online.
function vcard_get(user_jid)
        local user_username, user_host = jid.split(user_jid);
        if not hosts[user_host] then
                warn("The host '%s' is not configured for this server.", user_host);
                return;
        end
        storagemanager.initialize_host(user_host);
	local vCard;
	vCard = st.deserialize(datamanager.load(user_username, user_host, "vcard"));
	if vCard then
		print(vCard);
	else
		warn("The user '%s' has no vCard configured.",user_jid);
	end
end

function vcard_set(user_jid, file)
        local user_username, user_host = jid.split(user_jid);
        if not hosts[user_host] then
                warn("The host '%s' is not configured for this server.", user_host);
                return;
        end
        storagemanager.initialize_host(user_host);
	local f = io.input(file);
	local xmldata=io.read("*all");
	io.close(f);

	local vCard=st.preserialize(xml.parse(xmldata));

	if vCard then
		datamanager.store(user_username, user_host, "vcard", vCard);
	else
		warn("Could not parse the file.");
	end
end

function vcard_delete(user_jid)
        local user_username, user_host = jid.split(user_jid);
        if not hosts[user_host] then
                warn("The host '%s' is not configured for this server.", user_host);
                return;
        end
        storagemanager.initialize_host(user_host);
	datamanager.store(user_username, user_host, "vcard", nil);
end

function module.command(arg)
        local command = arg[1];
        if not command then
                warn("Valid subcommands: get | set | delete ");
                return 0;
        end
        table.remove(arg, 1);
        if command == "get" then
                vcard_get(arg[1]);
                return 0;
        elseif command == "set" then
                vcard_set(arg[1], arg[2]);
                return 0;
        elseif command == "delete" then
                vcard_delete(arg[1]);
                return 0;
        else
                warn("Unknown command: %s", command);
                return 1;
        end
        return 0;
end
