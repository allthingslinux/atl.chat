-- Dovecot authentication backend for Prosody
--
-- Copyright (C) 2010-2011 Waqas Hussain
-- Copyright (C) 2011 Kim Alvefur
--

local name = "Dovecot SASL";
local log = require "util.logger".init("auth_dovecot");

local socket_path = module:get_option_string("dovecot_auth_socket", "/var/run/dovecot/auth-login");
local socket_host = module:get_option_string("dovecot_auth_host", "127.0.0.1");
local socket_port = module:get_option_string("dovecot_auth_port");

local service_realm = module:get_option("realm");
local service_name = module:get_option("service_name");
local append_host = module:get_option_boolean("auth_append_host");
--assert(not append_host, "auth_append_host does not work");
local validate_domain = module:get_option_boolean("validate_append_host");
local handle_appended = module:get_option_string("handle_appended");
local util_sasl_new = require "util.sasl".new;

local new_dovecot_sasl = module:require "sasl_dovecot".new;

local new_sasl = function(realm)
	return new_dovecot_sasl(
		service_realm or realm,
		service_name or "xmpp",

		socket_port and { socket_host, socket_port } or socket_path,

		{ --config
			handle_domain = handle_appended or
				(append_host and "split" or "escape"),
			validate_domain = validate_domain,
		}
	);
end

do
	local s, err = new_sasl(module.host)
	if not s then
		log("error", "%s", tostring(err));
	end
	assert(s, "Could not create a new SASL object");
	assert(s.mechanisms, "SASL object has no mechanims method");
	local m, _m = {}, s:mechanisms();
	assert(not append_host or _m.PLAIN, "auth_append_host requires PLAIN, but it is unavailable");
	for k in pairs(_m) do
		table.insert(m, k);
	end
	log("debug", "Mechanims found: %s", table.concat(m, ", "));
end

provider = {};

function provider.test_password(username, password)
	return new_sasl(module.host):plain_test(username, password);
end

function provider.get_password(username)
	return nil, "Passwords unavailable for "..name;
end

function provider.set_password(username, password)
	return nil, "Passwords unavailable for "..name;
end

function provider.user_exists(username)
	return true -- FIXME
--[[ This, sadly, doesn't work.
	local user_test = new_sasl(module.host);
	user_test:select("PLAIN");
	user_test:process(("\0%s\0"):format(username));
	return user_test.username == username;
--]]
end

function provider.create_user(username, password)
	return nil, "Account creation/modification not available with "..name;
end

function provider.get_sasl_handler()
	return new_sasl(module.host);
end

if append_host then
	function provider.test_password(username, password)
		return new_sasl(module.host):plain_test(username .. "@".. (service_realm or module.host), password) == "success";
	end

	function provider.get_sasl_handler()
		return util_sasl_new(module.host, {
			plain_test = function(sasl, username, password, realm)
				return provider.test_password(username, password), true
			end;
		});
	end
end

module:provides("auth", provider);

