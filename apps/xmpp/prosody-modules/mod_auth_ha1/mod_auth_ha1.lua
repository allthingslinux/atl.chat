-- Prosody IM
-- Copyright (C) 2014 Matthew Wild
--
-- This project is MIT/X11 licensed. Please see the
-- COPYING file in the source package for more information.
--

local usermanager = require "core.usermanager";
local new_sasl = require "util.sasl".new;

local nodeprep = require "util.encodings".stringprep.nodeprep;
local nameprep = require "util.encodings".stringprep.nameprep;
local md5 = require "util.hashes".md5;

local host = module.host;

local auth_filename = module:get_option_string("auth_ha1_file", "auth.txt");
local auth_data = {};

function reload_auth_data()
	local f, err = io.open(auth_filename);
	if not f then
		module:log("error", "Failed to read from auth file: %s", err);
		return;
	end
	auth_data = {};
	local line_number, imported_count, not_authorized_count = 0, 0, 0;
	for line in f:lines() do
		line_number = line_number + 1;
		local username, hash, realm, state = line:match("^([^:]+):(%x+):([^:]+):(.+)$");
		if not username then
			if line:sub(1,1) ~= "#" then
				module:log("error", "Unable to parse line %d of auth file, skipping", line_number);
			end
		else
			username, realm = nodeprep(username), nameprep(realm);
			if not username then
				module:log("error", "Invalid username on line %d of auth file, skipping", line_number);
			elseif not realm then
				module:log("error", "Invalid hostname/realm on line %d of auth file, skipping", line_number);
			elseif state ~= "authorized" then
				not_authorized_count = not_authorized_count + 1;
			elseif realm == host then
				auth_data[username] = hash;
				imported_count = imported_count + 1;
			end
		end
	end
	f:close();
	module:log("debug", "Loaded %d accounts from auth file (%d authorized)", imported_count, imported_count-not_authorized_count);
end

function module.load()
	reload_auth_data();
end

module:hook_global("config-reloaded", reload_auth_data);

-- define auth provider
local provider = {};

function provider.test_password(username, password)
	module:log("debug", "test password for user %s at host %s, %s", username, host, password);

	local test_hash = md5(username..":"..host..":"..password, true);

	if test_hash == auth_data[username] then
		return true;
	else
		return nil, "Auth failed. Invalid username or password.";
	end
end

function provider.set_password(username, password)
	return nil, "Changing passwords not supported";
end

function provider.user_exists(username)
	if not auth_data[username] then
		module:log("debug", "account not found for username '%s' at host '%s'", username, host);
		return nil, "Auth failed. Invalid username";
	end
	return true;
end

function provider.create_user(username, password)
	return nil, "User creation not supported";
end

function provider.delete_user(username)
	return nil , "User deletion not supported";
end

function provider.get_sasl_handler()
	return new_sasl(host, {
		plain_test = function(sasl, username, password, realm)
			return usermanager.test_password(username, realm, password), true;
		end
	});
end

module:provides("auth", provider);

