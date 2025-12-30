-- Prosody IM
-- Copyright (C) 2014 Florian Zeitz
--
-- This project is MIT/X11 licensed. Please see the
-- COPYING file in the source package for more information.
--

local presence = module:depends("presence");
local send_presence_of_available_resources = presence.send_presence_of_available_resources;

local hosts = prosody.hosts;
local core_post_stanza = prosody.core_post_stanza;

local st = require "util.stanza";
local is_admin = require "core.usermanager".is_admin;
local jid_split = require "util.jid".split;

module:hook("presence/bare", function(data)
	local origin, stanza = data.origin, data.stanza;
	local to, from, type = stanza.attr.to, stanza.attr.from, stanza.attr.type;
	local node, host = jid_split(to);

	if type ~= "probe" then return; end
	if not is_admin(from, module.host) then return; end

	if 0 == send_presence_of_available_resources(node, host, from, origin) then
		core_post_stanza(hosts[host], st.presence({from=to, to=from, type="unavailable"}), true);
	end
	return true;
end, 10);
