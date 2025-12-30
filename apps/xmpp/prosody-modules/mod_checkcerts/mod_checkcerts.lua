local config = require "core.configmanager";
local ssl = require"ssl";
local datetime_parse = require"util.datetime".parse;
local load_cert = ssl.loadcertificate;
local st = require"util.stanza"

-- These are in days.
local nag_time = module:get_option_number("checkcerts_notify", 7) * 86400;

if not load_cert then
	module:log("error", "This version of LuaSec (%s) does not support certificate checking", ssl._VERSION);
	return
end

local pat = "^([JFMAONSD][ceupao][glptbvyncr])  ?(%d%d?) (%d%d):(%d%d):(%d%d) (%d%d%d%d) GMT$";
local months = {Jan=1,Feb=2,Mar=3,Apr=4,May=5,Jun=6,Jul=7,Aug=8,Sep=9,Oct=10,Nov=11,Dec=12};
local function parse_x509_datetime(s)
	local month, day, hour, min, sec, year = s:match(pat); month = months[month];
	return datetime_parse(("%04d-%02d-%02dT%02d:%02d:%02dZ"):format(year, month, day, hour, min, sec));
end

local timeunits = {"minute",60,"hour",3600,"day",86400,"week",604800,"month",2629746,"year",31556952,};
local function humantime(timediff)
	local ret = {};
	for i=#timeunits,2,-2 do
		if timeunits[i] < timediff then
			local n = math.floor(timediff / timeunits[i]);
			if n > 0 and #ret < 2 then
				ret[#ret+1] = ("%d %s%s"):format(n, timeunits[i-1], n ~= 1 and "s" or "");
				timediff = timediff - n*timeunits[i];
			end
		end
	end
	return table.concat(ret, " and ")
end

local function check_certs_validity()
	local now = os.time();

	-- First, let's find out what certificate this host uses.
	local ssl_config = config.rawget(module.host, "ssl");
	if not ssl_config or not ssl_config.certificate then
		ssl_config = config.get(module.host:match("%.(.*)"), "ssl");
	end
	if not ssl_config or not ssl_config.certificate then
		ssl_config = config.get("*", "ssl");
	end
	if not ssl_config or not ssl_config.certificate then
		module:log("warn", "Could not find a certificate to check");
		return;
	end

	local certfile = ssl_config.certificate;
	local fh, ferr = io.open(certfile); -- Load the file.
	if not fh then
		module:log("warn", "Could not open certificate %s", ferr);
		return;
	end
	local cert, lerr = load_cert(fh:read("*a")); -- And parse
	fh:close();
	if not cert then
		module:log("warn", "Could not parse certificate %s: %s", certfile, lerr or "");
		return;
	end

	local expires_at = parse_x509_datetime(cert:notafter());
	local expires_in = os.difftime(expires_at, now);
	local fmt =  "Certificate %s expires in %s"
	local nag_admin = expires_in < nag_time;
	local log_warn = expires_in < nag_time * 2;
	local timediff = expires_in;
	if expires_in < 0 then
		fmt =  "Certificate %s expired %s ago";
		timediff = -timediff;
	end
	timediff = humantime(timediff);
	module:log(log_warn and "warn" or "info", fmt, certfile, timediff);
	if nag_admin then
		local body = fmt:format("for host ".. module.host, timediff);
		for admin in module:get_option_inherited_set("admins", {}) do
			module:send(st.message({ from = module.host, to = admin, type = "chat" }, body));
		end
	end
	return math.max(86400, expires_in / 3);
end

module:add_timer(1, check_certs_validity);
