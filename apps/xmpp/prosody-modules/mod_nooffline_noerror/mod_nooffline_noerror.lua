-- Ignore disabled offline storage
--
-- Copyright (C) 2019-2020 Thilo Molitor
--
-- This project is MIT/X11 licensed. Please see the
-- COPYING file in the source package for more information.
--

-- depend on mod_mam to make sure mam is at least loaded and active
module:depends "mam";

-- ignore offline messages and don't return any error (the message will be already in MAM at this point)
-- this is *only* triggered if mod_offline is *not* loaded and completely ignored otherwise
module:hook("message/offline/handle", function(event)
	local log = event.origin and event.origin.log or module._log;
	if log then
		log("info", "Ignoring offline message (mod_offline seems *not* to be loaded)...");
	end
	return true;
end, -100);
