-- Copyright (C) 2013-2014 Kim Alvefur
-- This file is MIT/X11 licensed.

module:set_global();

local digest_algo = module:get_option_string(module:get_name().."_digest", "sha1");

local fingerprints = {};

local function hashprep(h)
	return tostring(h):gsub(":",""):lower();
end

local function hashfmt(h)
	return h:gsub("..","%0:", #h/2-1):upper();
end

for host, set in pairs(module:get_option("s2s_trusted_fingerprints", {})) do
	local host_set = {}
	if type(set) == "table" then -- list of fingerprints
		for i=1,#set do
			host_set[hashprep(set[i])] = true;
		end
	else -- assume single fingerprint
		host_set[hashprep(set)] = true;
	end
	fingerprints[host] = host_set;
end

module:hook("s2s-check-certificate", function(event)
	local session, host, cert = event.session, event.host, event.cert;

	local host_fingerprints = fingerprints[host];
	if host_fingerprints then
		local digest = cert and cert:digest(digest_algo);
		if host_fingerprints[digest] then
			module:log("info", "'%s' matched %s fingerprint %s", host, digest_algo:upper(), hashfmt(digest));
			session.cert_chain_status = "valid";
			session.cert_identity_status = "valid";
			return true;
		else
			module:log("warn", "'%s' has unknown %s fingerprint %s", host, digest_algo:upper(), hashfmt(digest));
			session.cert_chain_status = "invalid";
			session.cert_identity_status = "invalid";
		end
	end
end);
