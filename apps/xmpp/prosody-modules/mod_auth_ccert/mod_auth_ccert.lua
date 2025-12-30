-- Copyright (C) 2013 Kim Alvefur
--
-- This file is MIT/X11 licensed.
--
-- luacheck: ignore 131/get_sasl_handler

local jid_compare = require "util.jid".compare;
local jid_split = require "util.jid".prepped_split;
local new_sasl = require "util.sasl".new;
local now = os.time;
local log = module._log;

local subject_alternative_name = "2.5.29.17";
local id_on_xmppAddr = "1.3.6.1.5.5.7.8.5";
local oid_emailAddress = "1.2.840.113549.1.9.1";

local cert_match = module:get_option("certificate_match", "xmppaddr");

local username_extractor = {};

function username_extractor.xmppaddr(cert, authz, session)
	local extensions = cert:extensions();
	local SANs = extensions[subject_alternative_name];
	local xmppAddrs = SANs and SANs[id_on_xmppAddr];

	if not xmppAddrs then
		(session.log or log)("warn", "Client certificate contains no xmppAddrs");
		return nil, false;
	end

	for i=1,#xmppAddrs do
		if authz == "" or jid_compare(authz, xmppAddrs[i]) then
			(session.log or log)("debug", "xmppAddrs[%d] %q matches authz %q", i, xmppAddrs[i], authz)
			local username, host = jid_split(xmppAddrs[i]);
			if host == module.host then
				return username, true
			end
		end
	end
end

function username_extractor.email(cert)
	local subject = cert:subject();
	for i=1,#subject do
		local ava = subject[i];
		if ava.oid == oid_emailAddress then
			local username, host = jid_split(ava.value);
			if host == module.host then
				return username, true
			end
		end
	end
end

local find_username = username_extractor[cert_match];
if not find_username then
	module:log("error", "certificate_match = %q is not supported");
	return
end


function get_sasl_handler(session)
	return new_sasl(module.host, {
		external = session.secure and function(authz)
			if not session.secure then
				-- getpeercertificate() on a TCP connection would be bad, abort!
				(session.log or log)("error", "How did you manage to select EXTERNAL without TLS?");
				return nil, false;
			end
			local sock = session.conn:socket();
			local cert = sock:getpeercertificate();
			if not cert then
				(session.log or log)("warn", "No certificate provided");
				return nil, false;
			end

			if not cert:validat(now()) then
				(session.log or log)("warn", "Client certificate expired")
				return nil, "expired";
			end

			local chain_valid, chain_errors = sock:getpeerverification();
			if not chain_valid then
				(session.log or log)("warn", "Invalid client certificate chain");
				for i, error in ipairs(chain_errors) do
					(session.log or log)("warn", "%d: %s", i, table.concat(error, ", "));
				end
				return nil, false;
			end

			return find_username(cert, authz, session);
		end
	});
end

module:provides "auth";
