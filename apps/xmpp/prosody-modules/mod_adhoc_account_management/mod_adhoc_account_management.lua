local dataforms_new = require "util.dataforms".new;
local usermanager_set_password = require "core.usermanager".set_password;
local usermanager_test_password = require "core.usermanager".test_password;
local jid_split = require"util.jid".split;
local close_others = module:get_option_boolean("close_sessions_on_password_change", true)
local require_confirm = module:get_option_boolean("require_confirm_password", true)
local require_current = module:get_option_boolean("require_current_password", true)

local change_password_layout = {
	title = "Changing Your Password";
	instructions = "Fill out this form to change a your password.";

	{
		-- This is meta
		name = "FORM_TYPE",
		type = "hidden",
		-- Reuses form type from XEP 77
		value = "jabber:iq:register:changepassword",
	};
	{
		name = "password",
		type = "text-private",
		required = true,
		label = "New Password",
	};
};
if require_confirm then
	table.insert(change_password_layout, {
		name = "password-confirm",
		type = "text-private",
		required = true,
		label = "Confirm new password",
	});
end
if require_current then
	table.insert(change_password_layout, 2, {
		name = "password-current",
		type = "text-private",
		required = true,
		label = "Current password",
	});
end
change_password_layout = dataforms_new(change_password_layout);

function change_password_command_handler(self, data, state)
	if not state then -- New session, send the form
		return { status = "executing", actions  = { "complete" }, form = change_password_layout }, true;
	end

	if data.action == "cancel" then
		return { status = "canceled" };
	end

	-- Who are we talking to?
	local username, hostname = jid_split(data.from);
	if not username or hostname ~= module.host then
		return { status = "error", error = { type = "cancel",
			condition = "forbidden", message = "Invalid user or hostname." } };
	end

	-- Extract data from the form
	local fields = change_password_layout:data(data.form);

	-- Validate
	if require_current then
		if not fields["password-current"] or #fields["password-current"] == 0 then
			return { status = "error", error = { type = "modify",
				condition = "bad-request", message = "Please enter your current password" } };
		elseif not usermanager_test_password(username, hostname, fields["password-current"]) then
			return { status = "error", error = { type = "modify",
				condition = "bad-request", message = "Your current password was incorrect" } };
		end
	end

	if require_confirm and fields["password-confirm"] ~= fields["password"] then
		return { status = "error", error = { type = "modify",
			condition = "bad-request", message = "New password didn't match the confirmation" } };
	end

	if not fields.password or #fields.password == 0 then
		return { status = "error", error = { type = "modify",
			condition = "bad-request", message = "Please enter a new password" } };
	end

	-- All is good, so change password.
	module:log("debug", "About to usermanager.set_password(%q, password, %q)", username, hostname);
	local ok, err = usermanager_set_password(username, fields.password, hostname);
	if ok then
		if close_others then
			for _, sess in pairs(hosts[hostname].sessions[username].sessions) do
				if sess.full_jid ~= data.from then
					sess:close{ condition = "reset", text = "Password changed" }
				end
			end
		end
		return { status = "completed", info = "Password successfully changed" };
	else
		module:log("warn", "%s@%s could not change password: %s", username, hostname, tostring(err));
		return { status = "error", error = { type = "cancel",
			condition = "internal-server-error", message = "Could not save new password: "..tostring(err) } };
	end
end

-- Feature requests? What could fit under account management?

-- COMPAT w/0.11 (uses "user" instead of "any")
local permission = pcall(require, "core.features") and "any" or "user";

local adhoc_new = module:require "adhoc".new;
local adhoc_passwd = adhoc_new("Change Password", "passwd", change_password_command_handler, permission);
module:add_item ("adhoc", adhoc_passwd);
