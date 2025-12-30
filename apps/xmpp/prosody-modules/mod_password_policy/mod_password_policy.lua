-- Password policy enforcement for Prosody
--
-- Copyright (C) 2012 Waqas Hussain
--
--
-- Configuration:
--    password_policy = {
--        length = 8;
--    }


local it = require "util.iterators";
local set = require "util.set";
local st = require "util.stanza";

local options = module:get_option("password_policy");

options = options or {};
options.length = options.length or 8;
if options.exclude_username == nil then
	options.exclude_username = true;
end

local builtin_policies = set.new({ "length", "exclude_username" });
local extra_policies = set.new(it.to_array(it.keys(options))) - builtin_policies;

local extra_policy_handlers = {};

module:handle_items("password-policy-provider", function (event)
	-- Password policy handler added
	local item = event.item;
	module:log("error", "Adding password policy handler '%s'", item.name);
	extra_policy_handlers[item.name] = item.check_password;
end, function (event)
	-- Password policy handler removed
	local item = event.item;
	extra_policy_handlers[item.name] = nil;
end);

function check_password(password, additional_info)
	if not password or password == "" then
		return nil, "No password provided", "no-password";
	end

	if #password < options.length then
		return nil, ("Password is too short (minimum %d characters)"):format(options.length), "length";
	end

	if additional_info then
		local username = additional_info.username;
		if username and password:lower():find(username:lower(), 1, true) then
			return nil, "Password must not include your username", "username";
		end
	end

	for policy in extra_policies do
		local handler = extra_policy_handlers[policy];
		if not handler then
			module:log("error", "No policy handler found for '%s' (typo, or module not loaded?)", policy);
			return nil, "Internal error while verifying password", "internal";
		end
		local ok, reason_text, reason_name = handler(password, options[policy], additional_info);
		if ok ~= true then
			return nil, reason_text or ("Password failed %s check"):format(policy), reason_name or policy;
		end
	end

	return true;
end

function get_policy() --luacheck: ignore 131/get_policy
	return options;
end

function handler(event)
	local origin, stanza = event.origin, event.stanza;

	if stanza.attr.type == "set" then
		local query = stanza.tags[1];

		local passwords = {};

		local dataform = query:get_child("x", "jabber:x:data");
		if dataform then
			for _,tag in ipairs(dataform.tags) do
				if tag.attr.var == "password" then
					table.insert(passwords, tag:get_child_text("value"));
				end
			end
		end

		table.insert(passwords, query:get_child_text("password"));

		local additional_info = {
			username = origin.username;
		};

		for _,password in ipairs(passwords) do
			if password then
				local pw_ok, pw_err, pw_failed_policy = check_password(password, additional_info);
				if not pw_ok then
					module:log("debug", "Password failed check against '%s' policy", pw_failed_policy);
					origin.send(st.error_reply(stanza, "modify", "not-acceptable", pw_err));
					return true;
				end
			end
		end
	end
end

module:hook("iq/self/jabber:iq:register:query", handler, 10);
module:hook("iq/host/jabber:iq:register:query", handler, 10);
module:hook("stanza/iq/jabber:iq:register:query", handler, 10);
