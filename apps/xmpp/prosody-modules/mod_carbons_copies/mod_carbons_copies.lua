-- Send carbons v0 style copies of incoming messages to clients which
-- are not (yet) capable of Message Carbons (XEP-0280).
--
-- This extension integrates with the mod_carbons plugin in such a way
-- that a client capable of Message Carbons will not get a v0 copy.
--
-- This extension can be enabled for all users by default by setting
-- carbons_copies_default = true.
--
-- Alternatively or additionally setting carbons_copies_adhoc = true
-- will allow the user to enable or disable copies through Adhoc
-- commands.
--
-- Copyright (C) 2012 Michael Holzt
--
-- This file is MIT/X11 licensed.

local jid_split = require "util.jid".split;
local dm_load = require "util.datamanager".load;
local dm_store = require "util.datamanager".store;
local adhoc_new = module:require "adhoc".new;
local xmlns_carbons_v0 = "urn:xmpp:carbons:0";
local storename = "mod_carbons_copies";

local function toggle_copies(data, on)
	local username, hostname, resource = jid_split(data.from);
	dm_store(username, hostname, storename, { enabled = on });
end

local function adhoc_enable_copies(self, data, state)
	toggle_copies(data, true);
	return { info = "Copies are enabled for you now.\nPlease restart/reconnect clients.", status = "completed" };
end

local function adhoc_disable_copies(self, data, state)
	toggle_copies(data, false);
	return { info = "Copies are disabled for you now.\nPlease restart/reconnect clients.", status = "completed" };
end

module:hook("resource-bind", function(event)
	local session = event.session;
	local username, hostname, resource = jid_split(session.full_jid);

	local store = dm_load(username, hostname, storename) or
		{ enabled =
		module:get_option_boolean("carbons_copies_default") };

	if store.enabled then
		session.want_carbons = xmlns_carbons_v0;
		module:log("debug", "%s enabling copies", session.full_jid);
	end
end);

-- Adhoc-Support
if module:get_option_boolean("carbons_copies_adhoc") then
	local enable_desc = adhoc_new("Carbons: Enable Copies",
		"mod_carbons_copies#enable", adhoc_enable_copies);
	local disable_desc = adhoc_new("Carbons: Disable Copies",
		"mod_carbons_copies#disable", adhoc_disable_copies);

	module:add_item("adhoc", enable_desc);
	module:add_item("adhoc", disable_desc);
end
