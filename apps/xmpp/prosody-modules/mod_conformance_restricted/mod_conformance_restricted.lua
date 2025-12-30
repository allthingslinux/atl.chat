-- Prosody IM
-- Copyright (C) 2012 Florian Zeitz
--
-- This project is MIT/X11 licensed. Please see the
-- COPYING file in the source package for more information.
--

local st = require "util.stanza";
local jid = require "util.jid";

module:hook("message/host", function (event)
	local origin, stanza = event.origin, event.stanza;
	local node, host, resource = jid.split(stanza.attr.to);
	local body = stanza:get_child_text("body");

	if resource ~= "conformance" then
		return; -- Not interop testing
	end

	if body == "PI" then
		origin.send("<?testing this='out'?>");
	elseif body == "comment" then
		origin.send("<!-- no comment -->");
	elseif body == "DTD" then
		origin.send("<!DOCTYPE greeting [\n<!ENTITY test 'You should not see this'>\n]>");
	elseif body == "entity" then
		origin.send("<message type='chat' to='"..stanza.attr.from.."'><body>&test;</body></message>");
	else
		local reply = st.reply(stanza);
		reply:body("Send me one of: PI, comment, DTD, or entity");
		origin.send(reply);
	end

	return true;
end);
