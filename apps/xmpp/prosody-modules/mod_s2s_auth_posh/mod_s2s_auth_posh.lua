-- Copyright (C) 2013 - 2014 Tobias Markmann
-- This file is MIT/X11 licensed.
--
-- Implements authentication via POSH (PKIX over Secure HTTP)
-- http://tools.ietf.org/html/draft-miller-posh-03
--
module:set_global();
local json = require "util.json";

local base64 = require "util.encodings".base64;
local pem2der = require "util.x509".pem2der;
local hashes = require "util.hashes";
local build_url = require "socket.url".build;
local async = require "util.async";
local http = require "net.http";

local cache = require "util.cache".new(100);

local hash_order = { "sha-512", "sha-384", "sha-256", "sha-224", "sha-1" };
local hash_funcs = { hashes.sha512, hashes.sha384, hashes.sha256, hashes.sha224, hashes.sha1 };

local function posh_lookup(host_session, resume)
	-- do nothing if posh info already exists
	if host_session.posh ~= nil then return end

	local target_host = false;
	if host_session.direction == "incoming" then
		target_host = host_session.from_host;
	elseif host_session.direction == "outgoing" then
		target_host = host_session.to_host;
	end

	local cached = cache:get(target_host);
	if cached then
		if os.time() > cached.expires then
			cache:set(target_host, nil);
		else
			host_session.posh = { jwk = cached };
			return false;
		end
	end
	local log = host_session.log or module._log;

	log("debug", "Session direction: %s", tostring(host_session.direction));

	local url = build_url { scheme = "https", host = target_host, path = "/.well-known/posh/xmpp-server.json" };

	log("debug", "Request POSH information for %s", tostring(target_host));
	local redirect_followed = false;
	local function cb (response, code)
		if code ~= 200 then
			log("debug", "No or invalid POSH response received");
			resume();
			return;
		end
		log("debug", "Received POSH response");
		local jwk = json.decode(response);
		if not jwk or type(jwk) ~= "table" then
			log("error", "POSH response is not valid JSON!\n%s", tostring(response));
			resume();
			return;
		end
		if type(jwk.url) == "string" then
			if redirect_followed then
				redirect_followed = true;
				http.request(jwk.url, nil, cb);
			else
				log("error", "POSH had invalid redirect:\n%s", tostring(response));
				resume();
				return;
			end
		end

		host_session.posh = { orig = response };
		jwk.expires = os.time() + tonumber(jwk.expires) or 3600;
		host_session.posh.jwk = jwk;
		cache:set(target_host, jwk);
		resume();
	end
	http.request(url, nil, cb);
	return true;
end

-- Do POSH authentication
module:hook("s2s-check-certificate", function (event)
	local session, cert = event.session, event.cert;
	local log = session.log or module._log;
	if session.cert_identity_status == "valid" then
		log("debug", "Not trying POSH because certificate is already valid");
		return;
	end

	log("info", "Trying POSH authentication.");
	local wait, done = async.waiter();
	if posh_lookup(session, done) then
		wait();
	end
	local posh = session.posh;
	local jwk = posh and posh.jwk;
	local fingerprints = jwk and jwk.fingerprints;

	if type(fingerprints) ~= "table" then
		log("debug", "No POSH authentication data available");
		return;
	end

	local cert_der = pem2der(cert:pem());
	local cert_hashes = {};
	for i = 1, #hash_order do
		cert_hashes[i] = base64.encode(hash_funcs[i](cert_der));
	end
	for i = 1, #fingerprints do
		local fp = fingerprints[i];
		for j = 1, #hash_order do
			local hash = fp[hash_order[j]];
			if cert_hashes[j] == hash then
				session.cert_chain_status = "valid";
				session.cert_identity_status = "valid";
				log("debug", "POSH authentication succeeded!");
				return true;
			elseif hash then
				-- Don't try weaker hashes
				break;
			end
		end
	end

	log("debug", "POSH authentication failed!");
end);

function module.command(arg)
	if not arg[1] then
		print("Usage: mod_s2s_auth_posh /path/to/cert.pem")
		return 1;
	end
	local jwkset = { fingerprints = { }; expires = 86400; }

	for i, cert_file in ipairs(arg) do
		local cert, err = io.open(cert_file);
		if not cert then
			io.stderr:write(err, "\n");
			return 1;
		end
		local cert_pem = cert:read("*a");
		local cert_der, typ = pem2der(cert_pem);
		if typ == "CERTIFICATE" then
			jwkset.fingerprints[i] = { ["sha-256"] = base64.encode(hashes.sha256(cert_der)); };
		elseif typ then
			io.stderr:write(cert_file, " contained a ", typ:lower(), ", was expecting a certificate\n");
			return 1;
		else
			io.stderr:write(cert_file, " did not contain a certificate in PEM format\n");
			return 1;
		end
	end
	print(json.encode(jwkset));
	return 0;
end

