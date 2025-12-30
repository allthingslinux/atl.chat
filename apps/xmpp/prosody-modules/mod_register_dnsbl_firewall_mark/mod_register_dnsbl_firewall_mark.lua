local adns = require "net.adns";
local rbl = module:get_option_string("registration_rbl");
local rbl_message = module:get_option_string("registration_rbl_message");
local st = require "util.stanza";


local function cleanup_ip(ip)
	if ip:sub(1,7):lower() == "::ffff:" then
		return ip:sub(8);
	end
	return ip;
end

local function reverse(ip, suffix)
	local a,b,c,d = ip:match("^(%d+).(%d+).(%d+).(%d+)$");
	if not a then return end
	return ("%d.%d.%d.%d.%s"):format(d,c,b,a, suffix);
end

local store = module:open_store("firewall_marks", "map");

module:hook("user-registered", function (event)
	local session = event.session;
	local ip = session and session.ip and cleanup_ip(session.ip);
	local rbl_ip = ip and reverse(ip, rbl);
	if rbl_ip then
		local registration_time = os.time();
		local log = session.log;
		adns.lookup(function (reply)
			if reply and reply[1] then
				log("warn", "Account %s@%s registered from IP %s found in RBL (%s)", event.username, event.host or module.host, ip, reply[1].a);
				local user = prosody.bare_sessions[event.username .. "@" .. module.host];
				if user and user.firewall_marks then
					user.firewall_marks.dnsbl_hit = registration_time;
				else
					store:set(event.username, "dnsbl_hit", registration_time);
				end
				if rbl_message then
					module:log("debug", "Warning RBL registered user %s@%s", event.username, event.host);
					event.ip = ip;
					local rbl_stanza =
						st.message({ to = event.username.."@"..event.host, from = event.host },
							rbl_message:gsub("$(%w+)", event));
					module:send(rbl_stanza);
				end
			end
		end, rbl_ip);
	end
end);

module:add_item("account-trait", {
	name = "register-dnsbl-hit";
	prob_bad_true = 0.6;
	prob_bad_false = 0.4;
});

module:hook("get-account-traits", function (event)
	event.traits["register-dnsbl-hit"] = not not store:get(event.username, "dnsbl_hit");
end);
