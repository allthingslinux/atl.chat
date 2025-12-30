module:hook("message/host", function (event)
	local stanza = event.stanza;
	if #stanza.tags == 1 and stanza.tags[1].attr.xmlns == "http://jabber.org/protocol/chatstates" then
		return true;
	end
end, -10);
