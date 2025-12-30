-- mod_s2s_keysize_policy.lua
-- Requires LuaSec with this patch: https://github.com/brunoos/luasec/pull/12

module:set_global();

local datetime_parse = require"util.datetime".parse;
local pat = "^([JFMAONSD][ceupao][glptbvyncr])  ?(%d%d?) (%d%d):(%d%d):(%d%d) (%d%d%d%d) GMT$";
local months = {Jan=1,Feb=2,Mar=3,Apr=4,May=5,Jun=6,Jul=7,Aug=8,Sep=9,Oct=10,Nov=11,Dec=12};
local function parse_x509_datetime(s)
	local month, day, hour, min, sec, year = s:match(pat); month = months[month];
	return datetime_parse(("%04d-%02d-%02dT%02d:%02d:%02dZ"):format(year, month, day, hour, min, sec));
end

local weak_key_cutoff = datetime_parse("2014-01-01T00:00:00Z");

-- From RFC 4492
local weak_key_size = {
	RSA = 2048,
	DSA = 2048,
	DH  = 2048,
	EC  =  233,
}

module:hook("s2s-check-certificate", function(event)
	local host, session, cert = event.host, event.session, event.cert;
	if cert and cert.pubkey then
		local _, key_type, key_size = cert:pubkey();
		if key_size < ( weak_key_size[key_type] or 0 ) then
			local issued = parse_x509_datetime(cert:notbefore());
			if issued > weak_key_cutoff then
				session.log("warn", "%s has a %s-bit %s key issued after 31 December 2013, invalidating trust!", host, key_size, key_type);
				session.cert_chain_status = "invalid";
				session.cert_identity_status = "invalid";
			else
				session.log("warn", "%s has a %s-bit %s key", host, key_size, key_type);
			end
		else
			session.log("info", "%s has a %s-bit %s key", host, key_size, key_type);
		end
	end
end);
