-- mod_offline_hints
--
-- Copyright (C) 2019 Marcos de Vera Piquero <marcos.devera@quobis.com>
--
-- This file is MIT/X11 licensed.
--
-- A module to discard hinted messages with no-store at mod_offline
--

module:depends"offline";

local function handle_offline (event)
	local stanza = event.stanza;
	if (stanza:get_child("no-store", "urn:xmpp:hints") or
		stanza:get_child("no-permanent-store", "urn:xmpp:hints")) then
		module:log("debug", "Not storing offline stanza: %s (urn:xmpp:hints)", stanza);
		return false;
	end
	return nil;
end

module:hook("message/offline/handle", handle_offline);

module:log("debug", "Module loaded");
