local adns = require "net.adns";
local rbl = module:get_option_string("registration_rbl");

local function reverse(ip, suffix)
	if ip:sub(1,7):lower() == "::ffff:" then
		ip = ip:sub(8);
	end
	local a,b,c,d = ip:match("^(%d+).(%d+).(%d+).(%d+)$");
	if not a then return end
	return ("%d.%d.%d.%d.%s"):format(d,c,b,a, suffix);
end

-- TODO async
-- module:hook("user-registering", function (event) end);

module:hook("user-registered", function (event)
	local session = event.session;
	local ip = session and session.ip;
	local rbl_ip = ip and reverse(ip, rbl);
	if rbl_ip then
		local log = session.log;
		adns.lookup(function (reply)
			if reply and reply[1] then
				log("warn", "Account %s@%s registered from IP %s found in RBL (%s)", event.username, event.host or module.host, ip, reply[1].a);
			end
		end, rbl_ip);
	end
end);
