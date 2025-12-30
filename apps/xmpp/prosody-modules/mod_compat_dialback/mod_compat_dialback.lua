-- Prosody IM
-- Copyright (C) 2008-2010 Matthew Wild
-- Copyright (C) 2008-2010 Waqas Hussain
--
-- This project is MIT/X11 licensed. Please see the
-- COPYING file in the source package for more information.
--

module:set_global();

module:hook("s2s-stream-features-legacy", function (data)
	if data.origin.type == "s2sin_unauthed" then
		data.features:tag("dialback", { xmlns='urn:xmpp:features:dialback' }):up();
	end
end);
