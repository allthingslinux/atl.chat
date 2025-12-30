local adhoc_new = module:require "adhoc".new;
local uuid_new = require "util.uuid".generate;
local jid_split = require "util.jid".split;
local jid_join = require "util.jid".join;
local http_formdecode = require "net.http".formdecode;
local usermanager = require "core.usermanager";
local rostermanager = require "core.rostermanager";
local tohtml = require "util.stanza".xml_escape
local nodeprep = require "util.encodings".stringprep.nodeprep;
local http_files = require "net.http.files";
local tostring = tostring;

local invite_storage = module:open_store();
local inviter_storage = module:open_store("inviter");

module:depends"adhoc";
module:depends"http";

local function apply_template(template, args)
	return
		template:gsub("{{([^}]*)}}", function (k)
			if args[k] then
				return tohtml(args[k])
			else
				return k
			end
		end)
end

function generate_page(event, token)
	local response = event.response;

	local tokens = invite_storage:get() or {};

	response.headers.content_type = "text/html; charset=utf-8";

	if not token or token == "" then
		local template = assert(module:load_resource("invite/invite_result.html")):read("*a");

		-- TODO maybe show a friendlier information page instead?
		return apply_template(template, { classes = "alert-danger", message = "No token given" })
	elseif not tokens[token] then
		local template = assert(module:load_resource("invite/invite_result.html")):read("*a");

		return apply_template(template, { classes = "alert-danger", message = "This invite has expired." })
	end

	local template = assert(module:load_resource("invite/invite.html")):read("*a");

	return apply_template(template, { user = jid_join(tokens[token], module.host), server = module.host, token = token });
end

function subscribe(user1, user2)
	local user1_jid = jid_join(user1, module.host);
	local user2_jid = jid_join(user2, module.host);

	rostermanager.set_contact_pending_out(user2, module.host, user1_jid);
	rostermanager.set_contact_pending_in(user1, module.host, user2_jid);
	rostermanager.subscribed(user1, module.host, user2_jid);
	rostermanager.process_inbound_subscription_approval(user2, module.host, user1_jid);
end

function handle_form(event)
	local request, response = event.request, event.response;
	local form_data = http_formdecode(request.body);
	local user, password, token = form_data["user"], form_data["password"], form_data["token"];
	local tokens = invite_storage:get() or {};

	local template = assert(module:load_resource("invite/invite_result.html")):read("*a");

	response.headers.content_type = "text/html; charset=utf-8";

	if not user or #user == 0 or not password or #password == 0 or not token then
		return apply_template(template, { classes = "alert-warning", message = "Please fill in all fields." })
	end

	if not tokens[token] then
		return apply_template(template, { classes = "alert-danger", message = "This invite has expired." })
	end

	-- Shamelessly copied from mod_register_web.
	local prepped_username = nodeprep(user);

	if not prepped_username or #prepped_username == 0 then
		return apply_template(template, { classes = "alert-warning", message = "This username contains invalid characters." })
	end

	if usermanager.user_exists(prepped_username, module.host) then
		return apply_template(template, { classes = "alert-warning", message = "This username is already in use." })
	end

	local registering = { username = prepped_username , host = module.host, allowed = true }

	module:fire_event("user-registering", registering);

	if not registering.allowed then
		return apply_template(template, { classes = "alert-danger", message = "Registration is not allowed." })
	end

	local ok, err = usermanager.create_user(prepped_username, password, module.host);

	if ok then
		subscribe(prepped_username, tokens[token]);
		subscribe(tokens[token], prepped_username);

		inviter_storage:set(prepped_username, { inviter = tokens[token] });

		rostermanager.roster_push(tokens[token], module.host, jid_join(prepped_username, module.host));

		tokens[token] = nil;

		invite_storage:set(nil, tokens);

		module:fire_event("user-registered", {
			username = prepped_username, host = module.host, source = "mod_invite", });

		return apply_template(template, { classes = "alert-success",
			message = "Your account has been created! You can now log in using an XMPP client." })
	else
		module:log("debug", "Registration failed: " .. tostring(err));

		return apply_template(template, { classes = "alert-danger", message = "An unknown error has occurred." })
	end
end

module:provides("http", {
	route = {
		["GET /bootstrap.min.css"] = http_files.serve(module:get_directory() .. "/invite/bootstrap.min.css");
		["GET /*"] = generate_page;
		POST = handle_form;
	};
});

function invite_command_handler(_, data)
	local uuid = uuid_new();

	local user, host = jid_split(data.from);

	if host ~= module.host then
		return { status = "completed", error = { message = "You are not allowed to invite users to this server." }};
	end

	local tokens = invite_storage:get() or {};

	tokens[uuid] = user;

	invite_storage:set(nil, tokens);

	return { info = module:http_url() .. "/" .. uuid, status = "completed" };
end

local adhoc_invite = adhoc_new("Invite user", "invite", invite_command_handler, "local_user")

module:add_item("adhoc", adhoc_invite);
