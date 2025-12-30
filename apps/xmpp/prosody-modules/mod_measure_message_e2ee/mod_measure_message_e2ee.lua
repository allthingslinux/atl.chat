local count_message = module:measure("message", "rate");
local count_plain = module:measure("plain", "rate");
local count_openpgp = module:measure("openpgp", "rate");
local count_otr = module:measure("otr", "rate");
local count_ox = module:measure("ox", "rate");
local count_omemo2 = module:measure("omemo2", "rate");
local count_omemo = module:measure("omemo", "rate");
local count_encrypted = module:measure("encrypted", "rate");

local function message_handler(event)
	local origin, stanza = event.origin, event.stanza;

	-- This counts every message, even those with no body-like content.
	count_message();

	-- Annotates that a message is encrypted, using any of the following methods.
	if stanza:get_child("encryption", "urn:xmpp:eme:0") then
		count_encrypted();
	end

	if stanza:get_child("openpgp", "urn:xmpp:openpgp:0") then
		count_ox();
		return;
	end

	if stanza:get_child("encrypted", "urn:xmpp:omemo:2") then
		count_omemo2();
		return;
	end

	if stanza:get_child("encrypted", "eu.siacs.conversations.axolotl") then
		count_omemo();
		return;
	end

	if stanza:get_child("x", "jabber:x:encrypted") then
		count_openpgp();
		return;
	end

	local body = stanza:get_child_text("body");
	if body then
		if body:sub(1,4) == "?OTR" then
			count_otr();
			return;
		end

		count_plain();
	end
end

module:hook("pre-message/host", message_handler, 2);
module:hook("pre-message/bare", message_handler, 2);
module:hook("pre-message/full", message_handler, 2);
