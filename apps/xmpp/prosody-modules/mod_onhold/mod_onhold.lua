-- Prosody IM
-- Copyright (C) 2008-2009 Matthew Wild
-- Copyright (C) 2008-2009 Waqas Hussain
-- Copyright (C) 2009 Jeff Mitchell
--
-- This project is MIT/X11 licensed. Please see the
-- COPYING file in the source package for more information.
--

local datamanager = require "util.datamanager";
local jid_bare = require "util.jid".bare;
local jid_split = require "util.jid".split;
local st = require "util.stanza";
local datetime = require "util.datetime";
local ipairs = ipairs;
local onhold_jids = module:get_option("onhold_jids") or {};
for _, jid in ipairs(onhold_jids) do onhold_jids[jid] = true; end

function process_message(event)
	local session, stanza = event.origin, event.stanza;
	local to = stanza.attr.to;
	local from = jid_bare(stanza.attr.from);
	local node, host;
	local onhold_node, onhold_host;

	if to then
		node, host = jid_split(to)
	else
		node, host = session.username, session.host;
	end

	if onhold_jids[from] then
		stanza.attr.stamp, stanza.attr.stamp_legacy = datetime.datetime(), datetime.legacy();
		local result = datamanager.list_append(node, host, "onhold", st.preserialize(stanza));
		stanza.attr.stamp, stanza.attr.stamp_legacy = nil, nil;
		return true;
	end
	return nil;
end

module:hook("message/bare", process_message, 5);

module:hook("message/full", process_message, 5);

module:hook("presence/bare", function(event)
	if event.origin.presence then return nil; end
	local session = event.origin;
	local node, host = session.username, session.host;
	local from;
	local de_stanza;

	local data = datamanager.list_load(node, host, "onhold");
	local newdata = {};
	if not data then return nil; end
	for _, stanza in ipairs(data) do
		de_stanza = st.deserialize(stanza);
		from = jid_bare(de_stanza.attr.from);
		if not onhold_jids[from] then
			de_stanza:tag("delay", {xmlns = "urn:xmpp:delay", from = host, stamp = de_stanza.attr.stamp}):up(); -- XEP-0203
			de_stanza:tag("x", {xmlns = "jabber:x:delay", from = host, stamp = de_stanza.attr.stamp_legacy}):up(); -- XEP-0091 (deprecated)
			de_stanza.attr.stamp, de_stanza.attr.stamp_legacy = nil, nil;
			session.send(de_stanza);
		else
			table.insert(newdata, stanza);
		end
	end
	datamanager.list_store(node, host, "onhold", newdata);
	return nil;
end, 5);

