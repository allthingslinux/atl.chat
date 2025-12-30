-- mod_adhoc_blacklist
--
-- http://xmpp.org/extensions/xep-0133.html#edit-blacklist
--
-- Copyright (C) 2015 Kim Alvefur
--
-- This file is MIT/X11 licensed.
--

module:depends("adhoc");
local adhoc = module:require "adhoc";
local st = require"util.stanza";
local set = require"util.set";
local dataform = require"util.dataforms";
local adhoc_inital_data = require "util.adhoc".new_initial_data_form;

local blocklist_form = dataform.new {
	title = "Editing the Blacklist";
	instructions = "Fill out this form to edit the list of entities with whom communications are disallowed.";
	{
		type = "hidden";
		name = "FORM_TYPE";
		value = "http://jabber.org/protocol/admin";
	};
	{
		type = "jid-multi";
		name = "blacklistjids";
		label = "The blacklist";
	};
}

local blocklists = module:open_store("blocklist");

local blocklist_handler = adhoc_inital_data(blocklist_form, function ()
	local blacklistjids = {};
	local blacklist = blocklists:get();
	if blacklist then
		for jid in pairs(blacklist) do
			table.insert(blacklistjids, jid);
		end
	end
	return { blacklistjids = blacklistjids };
end, function(fields, form_err)
	if form_err then
		return { status = "completed", error = { message = "Problem in submitted form" } };
	end
	local blacklistjids = set.new(fields.blacklistjids);
	local ok, err = blocklists:set(nil, blacklistjids._items);
	if ok then
		return { status = "completed", info = "Blacklist updated" };
	else
		return { status = "completed", error = { message = "Error saving blacklist: "..err } };
	end
end);

module:add_item("adhoc", adhoc.new("Edit Blacklist", "http://jabber.org/protocol/admin#edit-blacklist", blocklist_handler, "admin"));

local function is_blocked(host)
	local blacklistjids = blocklists:get();
	return blacklistjids and blacklistjids[host];
end

module:hook("route/remote", function (event)
	local origin, stanza = event.origin, event.stanza;
	if is_blocked(event.to_host) then
		if origin and stanza then
			origin.send(st.error_reply(stanza, "cancel", "not-allowed", "Communication with this domain is not allowed"));
			return true;
		end
		return false;
	end
end, 1000);


module:hook("s2s-stream-features", function (event)
	local session = event.origin;
	if is_blocked(session.from_host) then
		session:close("policy-violation");
		return false;
	end
end, 1000);

module:hook("stanza/http://etherx.jabber.org/streams:features", function (event)
	local session = event.origin;
	if is_blocked(session.to_host) then
		session:close("policy-violation");
		return true;
	end
end, 1000);

