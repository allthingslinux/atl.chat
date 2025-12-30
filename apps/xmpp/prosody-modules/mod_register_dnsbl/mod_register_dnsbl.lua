local adns = require "net.adns";
local async = require "util.async";
local inet_pton = require "util.net".pton;
local to_hex = require "util.hex".to;

local rbl = module:get_option_string("registration_rbl");

local function reverse(ip, suffix)
	local n, err = inet_pton(ip);
	if not n then return n, err end
	if #n == 4 then
		local a,b,c,d = n:byte(1,4);
		return ("%d.%d.%d.%d.%s"):format(d,c,b,a, suffix);
	elseif #n == 16 then
		return to_hex(n):reverse():gsub("%x", "%1.") .. suffix;
	end
end

module:hook("user-registering", function (event)
	local session, ip = event.session, event.ip;
	local log = (session and session.log) or module._log;
	if not ip then
		log("debug", "Unable to check DNSBL when IP is unknown");
		return;
	end
	local rbl_ip, err = reverse(ip, rbl);
	if not rbl_ip then
		log("debug", "Unable to check DNSBL for ip %s: %s", ip, err);
		return;
	end

	local wait, done = async.waiter();
	adns.lookup(function (reply)
		if reply and reply[1] and reply[1].a then
			log("debug", "DNSBL response: %s IN A %s", rbl_ip, reply[1].a);
			log("info", "Blocking %s from registering %s (dnsbl hit)", ip, event.username);
			event.allowed = false;
			event.reason = "Blocked by DNSBL";
		end
		done();
	end, rbl_ip);
	wait();
end);
