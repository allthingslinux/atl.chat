module:depends("smacks");

module:hook("smacks-ack-delayed", function (event)
	if event.origin.type == "s2sin" or event.origin.type == "s2sout" then
		event.origin:close("connection-timeout");
		return true;
	end
end);
