-- Copyright (C) 2018 Minddistrict
--
-- This file is MIT/X11 licensed.
--

local host = module.host;
local log = module._log;
local new_sasl = require "util.sasl".new;
local usermanager = require "core.usermanager";
local verify_token = module:require "token_auth_utils".verify_token;

local provider = {};


function provider.test_password(username, password)
	log("debug", "Testing signed OTP for user %s at host %s", username, host);
	return verify_token(
		username,
		password,
		module:get_option_string("otp_seed"),
		module:get_option_string("token_secret"),
		log
	);
end

function provider.users()
	return function()
		return nil;
	end
end

function provider.set_password(username, password)
	return nil, "Changing passwords not supported";
end

function provider.user_exists(username)
	return true;
end

function provider.create_user(username, password)
	return nil, "User creation not supported";
end

function provider.delete_user(username)
	return nil , "User deletion not supported";
end

function provider.get_sasl_handler()
	local supported_mechanisms = {};
	supported_mechanisms["X-TOKEN"] = true;
	return new_sasl(host, {
		token = function(sasl, username, password, realm)
			return usermanager.test_password(username, realm, password), true;
		end,
        mechanisms = supported_mechanisms
	});
end

module:provides("auth", provider);
