module:depends("adhoc");
local adhoc_new = module:require("adhoc").new;
local hats_api = module:depends("muc_hats_api");

local dataforms_new = require "util.dataforms".new;
local adhoc_simple = require "util.adhoc".new_simple_form;

local function generate_error_message(errors)
	local errmsg = {};
	for name, err in pairs(errors) do
		errmsg[#errmsg + 1] = name .. ": " .. err;
	end
	return { status = "completed", error = { message = table.concat(errmsg, "\n") } };
end

local add_hat_form_layout = dataforms_new {
	title = "Add a hat";
	instructions = "Assign a hat to a room member";

	{ name = "user",  type = "jid-single",  label = "User JID", required = true };
	{ name = "room",  type = "jid-single",  label = "Room JID", required = true };
	{ name = "title", type = "text-single", label = "Hat title" };
	{ name = "uri",   type = "text-single", label = "Hat URI",  required = true };
};

local add_hat_handler = adhoc_simple(add_hat_form_layout, function (fields, errs)
	if errs then
		return generate_error_message(errs);
	end

	local ok, err_cond, err_text = hats_api.add_user_hat(fields.user, fields.room, fields.uri, {
		active = true;
		required = true;
		title = fields.title;
	});

	return {
		status = "completed";
		info = ok and "The hat has been added successfully" or ("There was an error adding the hat: "..(err_text or err_cond));
	};

end);

local remove_hat_form_layout = dataforms_new {
	title = "Remove a hat";
	instructions = "Remove a hat from a room member";

	{ name = "user",  type = "jid-single",  label = "User JID", required = true };
	{ name = "room",  type = "jid-single",  label = "Room JID", required = true };
	{ name = "uri",   type = "text-single", label = "Hat URI",  required = true };
};

local remove_hat_handler = adhoc_simple(remove_hat_form_layout, function (fields, errs)
	if errs then
		return generate_error_message(errs);
	end

	local ok, err_cond, err_text = hats_api.remove_user_hat(fields.user, fields.room, fields.uri);

	return {
		status = "completed";
		info = ok and "The hat has been removed successfully" or ("There was an error removing the hat: "..(err_text or err_cond));
	};

end);

local add_hat_desc = adhoc_new("Add hat to a user", "http://prosody.im/protocol/hats#add", add_hat_handler, "admin");
local remove_hat_desc = adhoc_new("Remove hat from a user", "http://prosody.im/protocol/hats#remove", remove_hat_handler, "admin");

module:provides("adhoc", add_hat_desc);
module:provides("adhoc", remove_hat_desc);
