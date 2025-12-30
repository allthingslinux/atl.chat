-- Prosody IM
-- Copyright (C) 2008-2010 Matthew Wild
-- Copyright (C) 2008-2010 Waqas Hussain
--
-- This project is MIT/X11 licensed. Please see the
-- COPYING file in the source package for more information.
--

local datamanager = require "util.datamanager";
local storagemanager = require "core.storagemanager";
local log = require "util.logger".init("auth_internal_yubikey");
local type = type;
local error = error;
local ipairs = ipairs;
local hashes = require "util.hashes";
local jid = require "util.jid";
local jid_bare = require "util.jid".bare;
local config = require "core.configmanager";
local usermanager = require "core.usermanager";
local new_sasl = require "util.sasl".new;
local hosts = hosts;

local prosody = _G.prosody;

local yubikey = require "yubikey".new_authenticator({
	prefix_length = module:get_option_number("yubikey_prefix_length", 0);
	check_credentials = function (ret, state, data)
		local account = data.account;
		local yubikey_hash = hashes.sha1(ret.public_id..ret.private_id..(ret.password or ""), true);
		if yubikey_hash == account.yubikey_hash then
			return true;
		end
		return false, "invalid-otp";
	end;
	store_device_info = function (state, data)
		local new_account = {};
		for k, v in pairs(data.account) do
			new_account[k] = v;
		end
		new_account.yubikey_state = state;
		datamanager.store(data.username, data.host, "accounts", new_account);
	end;
});

local global_yubikey_key = module:get_option_string("yubikey_key");

local host = module.host;
local provider = {};
log("debug", "initializing default authentication provider for host '%s'", host);

function provider.test_password(username, password)
	log("debug", "test password '%s' for user %s at host %s", password, username, module.host);

	local account_info = datamanager.load(username, host, "accounts") or {};
	local yubikey_key = account_info.yubikey_key or global_yubikey_key;
	if account_info.yubikey_key then
		log("debug", "Authenticating Yubikey OTP for %s", username);
		local authed, err = yubikey:authenticate(password, account_info.yubikey_key, account_info.yubikey_state or {}, { account = account_info, username = username, host = host });
		if not authed then
			log("debug", "Failed to authenticate %s via OTP: %s", username, err);
			return authed, err;
		end
		return authed;
	elseif account_info.password and password == account_info.password then
		-- No yubikey configured for this user, treat as normal password
		log("debug", "No yubikey configured for %s, successful login using password auth", username);
		return true;
	else
		return nil, "Auth failed. Invalid username or password.";
	end
end

function provider.get_password(username)
	log("debug", "get_password for username '%s' at host '%s'", username, module.host);
	return (datamanager.load(username, host, "accounts") or {}).password;
end

function provider.set_password(username, password)
	local account = datamanager.load(username, host, "accounts");
	if account then
		account.password = password;
		return datamanager.store(username, host, "accounts", account);
	end
	return nil, "Account not available.";
end

function provider.user_exists(username)
	local account = datamanager.load(username, host, "accounts");
	if not account then
		log("debug", "account not found for username '%s' at host '%s'", username, module.host);
		return nil, "Auth failed. Invalid username";
	end
	return true;
end

function provider.create_user(username, password)
	return datamanager.store(username, host, "accounts", {password = password});
end

function provider.delete_user(username)
	return datamanager.store(username, host, "accounts", nil);
end

function provider.get_sasl_handler()
	local realm = module:get_option("sasl_realm") or module.host;
	local getpass_authentication_profile = {
		plain_test = function(sasl, username, password, realm)
			return usermanager.test_password(username, realm, password), true;
		end
	};
	return new_sasl(realm, getpass_authentication_profile);
end

module:provides("auth", provider);

function module.command(arg)
	local command = arg[1];
	table.remove(arg, 1);
	if command == "associate" then
		local user_jid = arg[1];
		if not user_jid or user_jid == "help" then
			prosodyctl.show_usage([[mod_auth_internal_yubikey associate JID]], [[Set the Yubikey details for a user]]);
			return 1;
		end

		local username, host = jid.prepped_split(user_jid);
		if not username or not host then
			print("Invalid JID: "..user_jid);
			return 1;
		end

		local password, public_id, private_id, key;

		for i=2,#arg do
			local k, v = arg[i]:match("^%-%-(%w+)=(.*)$");
			if not k then
				k, v = arg[i]:match("^%-(%w)(.*)$");
			end
			if k == "password" then
				password = v;
			elseif k == "fixed" then
				public_id = v;
			elseif k == "uid" then
				private_id = v;
			elseif k == "key" or k == "a" then
				key = v;
			end
		end

		if not password then
			print(":: Password ::");
			print("This is an optional password that should be always");
			print("entered during login *before* the yubikey password.");
			print("If the yubikey is lost/stolen, unless the attacker");
			print("knows this prefix, they cannot access the account.");
			print("");
			password = prosodyctl.read_password();
			if not password then
				print("Cancelled.");
				return 1;
			end
		end

		if not public_id then
			print(":: Public Yubikey ID ::");
			print("This is a fixed string of characters between 0 and 16");
			print("bytes long that the Yubikey prefixes to every token.");
			print("The ID should be entered in modhex encoding, meaning ");
			print("a string up to 32 characters. This *must* match");
			print("exactly the fixed string programmed into the yubikey.");
			print("");
			io.write("Enter fixed id (modhex): ");
			while true do
				public_id = io.read("*l");
				if #public_id > 32 then
					print("The fixed id must be 32 characters or less. Please try again.");
				elseif public_id:match("[^cbdefghijklnrtuv]") then
					print("The fixed id contains invalid characters. It must be entered in modhex encoding. Please try again.");
				else
					break;
				end
			end
		end

		if not private_id then
			print(":: Private Yubikey ID ::");
			print("This is a fixed secret UID programmed into the yubikey");
			print("during configuration. It must be entered in hex (not modhex)");
			print("encoding. It is always 6 bytes long, which is 12 characters");
			print("in hex encoding.");
			print("");
			while true do
				io.write("Enter private UID (hex): ");
				private_id = io.read("*l");
				if #private_id ~= 12 then
					print("The id length must be 12 characters in hex encoding. Please try again.");
				elseif private_id:match("%X") then
					print("The key contains invalid characters - it must be in hex encoding (not modhex). Please try again.");
				else
					break;
				end
			end
		end

		if not key then
			print(":: AES Encryption Key ::");
			print("This is the secret key that the Yubikey uses to encrypt the");
			print("generated tokens. It is 32 characters in hex encoding.");
			print("");
			while true do
				io.write("Enter AES key (hex): ");
				key = io.read("*l");
				if #key ~= 32 then
					print("The key length must be 32 characters in hex encoding. Please try again.");
				elseif key:match("%X") then
					print("The key contains invalid characters - it must be in hex encoding (not modhex). Please try again.");
				else
					break;
				end
			end
		end

		local hash = hashes.sha1(public_id..private_id..password, true);
		local account = {
			yubikey_hash = hash;
			yubikey_key = key;
		};
		storagemanager.initialize_host(host);
		local ok, err = datamanager.store(username, host, "accounts", account);
		if not ok then
			print("Error saving configuration:");
			print("", err);
			return 1;
		end
		print("Saved.");
		return 0;
	end
end
