local id = require "util.id";
local json = require "util.json";
local usermanager = require "core.usermanager";
local nodeprep = require "util.encodings".stringprep.nodeprep;

local site_name = module:get_option_string("site_name", module.host);

local json_content_type = "application/json";

module:depends("http");

local invites = module:depends("invites");

function get_invite_info(event, invite_token)
	if not invite_token or #invite_token == 0 then
		return 404;
	end
	local invite = invites.get(invite_token);
	if not invite then
		return 404;
	end

	event.response.headers["Content-Type"] = json_content_type;
	return json.encode({
		site_name = site_name;
		token = invite.token;
		domain = module.host;
		uri = invite.uri;
		type = invite.type;
		jid = invite.jid;
		inviter = invite.inviter;
		reset = invite.additional_data and invite.additional_data.allow_reset or nil;
	});
end

function register_with_invite(event)
	local request, response = event.request, event.response;

	if not request.body or #request.body == 0
	or request.headers.content_type ~= json_content_type then
		module:log("warn", "Invalid payload");
		return 400;
	end

	local register_data = json.decode(event.request.body);
	if not register_data then
		module:log("warn", "Invalid JSON");
		return 400;
	end

	local user, password, token = register_data.username, register_data.password, register_data.token;

	local invite = invites.get(token);
	if not invite then
		return 404;
	end

	response.headers["Content-Type"] = json_content_type;

	if not user or #user == 0 or not password or #password == 0 or not token then
		module:log("warn", "Invalid data");
		return 400;
	end

	-- Shamelessly copied from mod_register_web.
	local prepped_username = nodeprep(user);

	if not prepped_username or #prepped_username == 0 then
		return 400;
	end

	local reset_for = invite.additional_data and invite.additional_data.allow_reset or nil;
	if reset_for ~= nil then
		module:log("debug", "handling password reset invite for %s", reset_for)
		if reset_for ~= prepped_username then
			return 403; -- Attempt to use reset invite for incorrect user
		end
		local ok, err = usermanager.set_password(prepped_username, password, module.host);
		if not ok then
			module:log("error", "Unable to reset password for %s@%s: %s", prepped_username, module.host, err);
			return 500;
		end
		module:fire_event("user-password-reset", user);
	elseif usermanager.user_exists(prepped_username, module.host) then
		return 409; -- Conflict
	else
		local registering = {
			validated_invite = invite;
			username = prepped_username;
			host = module.host;
			ip = request.ip;
			allowed = true;
		};

		module:fire_event("user-registering", registering);

		if not registering.allowed then
			return 403;
		end

		local ok, err = usermanager.create_user(prepped_username, password, module.host);

		if not ok then
			local err_id = id.short();
			module:log("warn", "Registration failed (%s): %s", err_id, tostring(err));
			return 500;
		end

		module:fire_event("user-registered", {
			username = prepped_username;
			host = module.host;
			source = "mod_"..module.name;
			validated_invite = invite;
			ip = request.ip;
		});
	end

	return json.encode({
		jid = prepped_username .. "@" .. module.host;
	});
end

module:provides("http", {
	default_path = "register_api";
	route = {
		["GET /invite/*"] = get_invite_info;
		["POST /register"] = register_with_invite;
	};
});
