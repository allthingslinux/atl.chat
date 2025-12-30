-- mod_muc_mam_markers
--
-- Copyright (C) 2019 Marcos de Vera Piquero <marcos.devera@quobis.com>
--
-- This file is MIT/X11 licensed.
--
-- A module to make chat markers get stored in the MUC archives
--

module:depends"muc_mam"

local function handle_muc_message (event)
	local stanza = event.stanza;
	local is_received = stanza:get_child("received", "urn:xmpp:chat-markers:0");
	local is_displayed = stanza:get_child("displayed", "urn:xmpp:chat-markers:0");
	local is_acked = stanza:get_child("acknowledged", "urn:xmpp:chat-markers:0");
	if (is_received or is_displayed or is_acked) then
		return true;
	end
	return nil;
end

module:hook("muc-message-is-historic", handle_muc_message);

module:log("debug", "Module loaded");
