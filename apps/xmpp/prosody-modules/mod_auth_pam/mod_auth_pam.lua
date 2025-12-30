-- PAM authentication for Prosody
-- Copyright (C) 2013 Kim Alvefur
--
-- Requires https://github.com/devurandom/lua-pam
-- and LuaPosix

local posix = require "posix";
local pam = require "pam";
local new_sasl = require "util.sasl".new;

function user_exists(username)
	return not not posix.getpasswd(username);
end

function test_password(username, password)
	local h, err = pam.start("xmpp", username, {
		function (t)
			if #t == 1 and t[1][1] == pam.PROMPT_ECHO_OFF then
				return { { password, 0} };
			end
		end
	});
	if h and h:authenticate() and h:endx(pam.SUCCESS) then
		return user_exists(username), true;
	end
	return nil, true;
end

function get_sasl_handler()
	return new_sasl(module.host, {
		plain_test = function(sasl, ...)
			return test_password(...)
		end
	});
end

module:provides"auth";
