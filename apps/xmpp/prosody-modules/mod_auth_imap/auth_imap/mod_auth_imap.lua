-- IMAP authentication backend for Prosody
--
-- Copyright (C) 2011 FIMXE from hg annotate -u

local name = "IMAP SASL";
local log = require "util.logger".init("auth_imap");

local imap_host = module:get_option_string("imap_auth_host", "localhost");
local imap_port = module:get_option_number("imap_auth_port");

local imap_service_realm = module:get_option_string("imap_auth_realm", module:get_option("sasl_realm"));
local imap_service_name = module:get_option_string("imap_auth_service_name");
local append_host = module:get_option_boolean("auth_append_host");

local verify_certificate = module:get_option_boolean("auth_imap_verify_certificate", true);
local ssl_params = module:get_option("auth_imap_ssl", {
	mode = "client", protocol = "sslv23";
	capath = "/etc/ssl/certs";
	options = { "no_sslv2", "no_sslv3" };
	verify = verify_certificate and { "peer", "fail_if_no_peer_cert" } or nil;
	ciphers = "HIGH:!DSS:!aNULL@STRENGTH";
});

local new_imap_sasl = module:require "sasl_imap".new;

local new_sasl = function(realm)
	return new_imap_sasl(
		imap_service_realm or realm,
		imap_service_name or "xmpp",
		imap_host, imap_port,
		ssl_params, append_host
	);
end

do
	local s = new_sasl(module.host)
	assert(s, "Could not create a new SASL object");
	assert(s.mechanisms, "SASL object has no mechanims method");
	local m = {};
	for k in pairs(s:mechanisms()) do
		table.insert(m, k);
	end
	log("debug", "Mechanims found: %s", table.concat(m, ", "));
end

provider = {
	name = module.name:gsub("^auth_","");
};

function provider.test_password(username, password)
	return nil, "Legacy auth not supported with "..name;
end

function provider.get_password(username)
	return nil, "Passwords unavailable for "..name;
end

function provider.set_password(username, password)
	return nil, "Passwords unavailable for "..name;
end

function provider.user_exists(username)
	-- FIXME
	return true
end

function provider.create_user(username, password)
	return nil, "Account creation/modification not available with "..name;
end

function provider.get_sasl_handler()
	return new_sasl(module.host);
end

module:add_item("auth-provider", provider);

