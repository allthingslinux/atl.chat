local usermanager = require "core.usermanager";

local array = require "util.array";
local it = require "util.iterators";
local jid = require "util.jid";
local json = require "util.json";
local set = require "util.set";
local st = require "util.stanza";
local statsmanager = require "core.statsmanager";

module:depends("http");

local announce = module:depends("announce");
local invites = module:depends("invites");
local tokens = module:depends("tokenauth");
local mod_pep = module:depends("pep");
local mod_groups = module:depends("groups_internal");
local mod_account_activity = module:depends("account_activity");

local push_errors = module:shared("cloud_notify/push_errors");

local site_name = module:get_option_string("site_name", module.host);

local manual_stats_collection = module:context("*"):get_option("statistics_interval") == "manual";

local json_content_type = "application/json";

local www_authenticate_header = ("Bearer realm=%q"):format(module.host.."/"..module.name);

local xmlns_pubsub = "http://jabber.org/protocol/pubsub";
local xmlns_nick = "http://jabber.org/protocol/nick";

local deleted_users = module:open_store("accounts_cleanup");

local function check_credentials(request)
	local auth_type, auth_data = string.match(request.headers.authorization or "", "^(%S+)%s(.+)$");
	if not (auth_type and auth_data) then
		return false;
	end

	if auth_type == "Bearer" then
		return tokens.get_token_session(auth_data);
	end
	return nil;
end

module:default_permission("prosody:admin", ":access-admin-api");

function check_auth(routes)
	local function check_request_auth(event)
		local session = check_credentials(event.request);
		if not session then
			event.response.headers.authorization = www_authenticate_header;
			return false, 401;
		end
		-- FIXME this should probably live in mod_tokenauth or similar
		session.type = "c2s";
		session.full_jid = jid.join(session.username, session.host, session.resource);
		event.session = session;
		if not module:may(":access-admin-api", event) then
			return false, 403;
		end
		return true;
	end

	for route, handler in pairs(routes) do
		routes[route] = function (event, ...)
			local permit, code = check_request_auth(event);
			if not permit then
				return code;
			end
			return handler(event, ...);
		end;
	end
	return routes;
end

local function token_info_to_invite_info(token_info)
	local additional_data = token_info.additional_data;
	local groups = additional_data and additional_data.groups or nil;
	local roles = additional_data and additional_data.roles or nil;
	local source = additional_data and additional_data.source or nil;
	local note = additional_data and additional_data.note or nil;
	local reset = not not (additional_data and additional_data.allow_reset or nil);
	return {
		id = token_info.token;
		type = token_info.type;
		reusable = not not token_info.reusable;
		inviter = token_info.inviter;
		jid = token_info.jid;
		uri = token_info.uri;
		landing_page = token_info.landing_page;
		created_at = token_info.created_at;
		expires = token_info.expires;
		groups = groups;
		roles = roles;
		source = source;
		reset = reset;
		note = note;
	};
end

function list_invites(event)
	local invites_list = {};
	for token, invite in invites.pending_account_invites() do --luacheck: ignore 213/token
		table.insert(invites_list, token_info_to_invite_info(invite));
	end
	table.sort(invites_list, function (a, b)
		return a.created_at < b.created_at;
	end);

	event.response.headers["Content-Type"] = json_content_type;
	return json.encode_array(invites_list);
end

function get_invite_by_id(event, invite_id)
	local invite = invites.get_account_invite_info(invite_id);
	if not invite then
		return 404;
	end

	event.response.headers["Content-Type"] = json_content_type;
	return json.encode(token_info_to_invite_info(invite));
end

function create_invite_type(event, invite_type)
	local options;

	local request = event.request;
	if request.body and #request.body > 0 then
		if request.headers.content_type ~= json_content_type then
			module:log("warn", "Invalid content type");
			return 400;
		end
		options = json.decode(event.request.body);
		if not options then
			module:log("warn", "Invalid JSON");
			return 400;
		end
	else
		options = {};
	end

	local source = event.session.username .. "@" .. module.host .. "/admin_api";

	local invite;
	if invite_type == "reset" then
		if not options.username then
			return 400;
		end
		invite = invites.create_account_reset(options.username, options.ttl);
	elseif invite_type == "group" then
		if not options.groups then
			return 400;
		end
		invite = invites.create_group(options.groups, {
			source = source;
			roles = options.roles;
			note = options.note;
		}, options.ttl);
	elseif invite_type == "account" then
		invite = invites.create_account(options.username, {
			source = source;
			groups = options.groups;
			roles = options.roles;
			note = options.note;
		}, options.ttl);
	else
		return 400;
	end
	if not invite then
		return 500;
	end
	event.response.headers["Content-Type"] = json_content_type;
	return json.encode(token_info_to_invite_info(invite));
end

function delete_invite(event, invite_id) --luacheck: ignore 212/event
	if not invites.delete_account_invite(invite_id) then
		return 404;
	end
	return 200;
end

local function get_user_avatar_info(username)
	local pep_service = mod_pep.get_pep_service(username);
	local ok, _, avatar_item = pep_service:get_last_item("urn:xmpp:avatar:metadata", true);
	avatar_item = avatar_item and avatar_item:get_child("metadata", "urn:xmpp:avatar:metadata");
	if not ok or not avatar_item then return; end

	local avatar_info = {};

	for avatar in avatar_item:childtags("info") do
		table.insert(avatar_info, {
			bytes = tonumber(avatar.attr.bytes);
			hash = avatar.attr.id;
			type = avatar.attr.type;
			width = tonumber(avatar.attr.width);
			height = tonumber(avatar.attr.height);
		});
	end

	return avatar_info;
end

local function get_user_info(username)
	if not usermanager.user_exists(username, module.host) then
		return nil;
	end
	local display_name;
	do
		local pep_service = mod_pep.get_pep_service(username);
		local ok, _, nick_item = pep_service:get_last_item(xmlns_nick, true);
		if ok and nick_item then
			display_name = nick_item:get_child_text("nick", xmlns_nick);
		end
	end

	local primary_role, secondary_roles, legacy_roles;
	if usermanager.get_user_role then
		primary_role = usermanager.get_user_role(username, module.host);
		secondary_roles = array.collect(it.keys(usermanager.get_user_secondary_roles(username, module.host)));
	elseif usermanager.get_user_roles then -- COMPAT w/0.12
		legacy_roles = array();
		local roles_map = usermanager.get_user_roles(username, module.host);
		for role_name in pairs(roles_map) do
			legacy_roles:push(role_name);
		end
	end

	local enabled = true; -- Assume all enabled if on a version without is_enabled
	if usermanager.user_is_enabled then
		enabled = usermanager.user_is_enabled(username, module.host);
	end

	return {
		username = username;
		display_name = display_name;
		role = primary_role and primary_role.name or nil;
		secondary_roles = secondary_roles;
		roles = legacy_roles; -- COMPAT w/0.12
		enabled = enabled;
		last_active = mod_account_activity.get_last_active(username);
		deletion_request = not enabled and deleted_users:get(username) or nil;
		avatar_info = get_user_avatar_info(username);
	};
end

local function get_session_debug_info(session)
	local info = {
		full_jid = session.full_jid;
		ip = session.ip;
		since = math.floor(session.conntime);
		status = {
			connected = not not session.conn;
			hibernating = not not session.hibernating;
		};
		features = {
			carbons = not not session.want_carbons;
			encrypted = not not session.secure;
			acks = not not session.smacks;
			resumption = not not session.resumption_token;
			mobile_optimization = not not session.csi_counter;
			push_notifications = not not session.push_identifier;
			history = not not session.mam_requested;
		};
		queues = {};
	};
	-- CSI
	if session.state then
		info.status.active = session.state == "active";
		info.queues.held_stanzas = session.csi_counter or 0;
	end
	-- Smacks queue
	if session.last_requested_h and session.last_acknowledged_stanza then
		info.queues.awaiting_acks = session.last_requested_h - session.last_acknowledged_stanza;
	elseif session.outgoing_stanza_queue then
		-- New mod_smacks
		info.queues.awaiting_acks = session.outgoing_stanza_queue:count_unacked();
	end
	if session.push_identifier then
		info.push_info = {
			id = session.push_identifier;
			wakeup_push_sent = session.first_hibernated_push;
		};
	end
	return info;
end

local function get_user_omemo_info(username)
	local everything_valid = true;
	local any_device = false;
	local omemo_status = {};
	local omemo_devices;
	local pep_service = mod_pep.get_pep_service(username);
	if pep_service and pep_service.nodes then
		local ok, _, device_list = pep_service:get_last_item("eu.siacs.conversations.axolotl.devicelist", true);
		if ok and device_list then
			device_list = device_list:get_child("list", "eu.siacs.conversations.axolotl");
		end
		if device_list then
			omemo_devices = {};
			for device_entry in device_list:childtags("device") do
				any_device = true;
				local device_info = {};
				local device_id = tonumber(device_entry.attr.id or "");
				if device_id then
					device_info.id = device_id;
					local bundle_id = ("eu.siacs.conversations.axolotl.bundles:%d"):format(device_id);
					local have_bundle, _, bundle = pep_service:get_last_item(bundle_id, true);
					if have_bundle and bundle and bundle:get_child("bundle", "eu.siacs.conversations.axolotl") then
						device_info.have_bundle = true;
						local config_ok, bundle_config = pep_service:get_node_config(bundle_id, true);
						if config_ok and bundle_config then
							device_info.bundle_config = bundle_config;
							if bundle_config.max_items == 1
							and bundle_config.access_model == "open"
							and bundle_config.persist_items == true
							and bundle_config.publish_model == "publishers" then
								device_info.valid = true;
							end
						end
					end
				end
				if device_info.valid == nil then
					device_info.valid = false;
					everything_valid = false;
				end
				table.insert(omemo_devices, device_info);
			end

			local config_ok, list_config = pep_service:get_node_config("eu.siacs.conversations.axolotl.devicelist", true);
			if config_ok and list_config then
				omemo_status.config = list_config;
				if list_config.max_items == 1
				and list_config.access_model == "open"
				and list_config.persist_items == true
				and list_config.publish_model == "publishers" then
					omemo_status.config_valid = true;
				end
			end
			if omemo_status.config_valid == nil then
				omemo_status.config_valid = false;
				everything_valid = false;
			end
		end
	end
	omemo_status.valid = everything_valid and any_device;
	return {
		status = omemo_status;
		devices = omemo_devices;
	};
end

local function get_user_debug_info(username)
	local debug_info = {
		time = os.time();
	};
	-- Online sessions
	do
		local user_sessions = prosody.hosts[module.host].sessions[username];
		if user_sessions then
			user_sessions = user_sessions.sessions
		end
		local sessions = {};
		if user_sessions then
			for _, session in pairs(user_sessions) do
				table.insert(sessions, get_session_debug_info(session));
			end
		end
		debug_info.sessions = sessions;
	end
	-- Push registrations
	do
		local store = module:open_store("cloud_notify");
		local services = store:get(username);
		local push_registrations = {};
		if services then
			for identifier, push_info in pairs(services) do
				push_registrations[identifier] = {
					since = push_info.timestamp;
					service = push_info.jid;
					node = push_info.node;
					error_count = push_errors[identifier] or 0;
					client_id = push_info.client_id;
					encryption = not not push_info.encryption;
				};
			end
		end
		debug_info.push_registrations = push_registrations;
	end
	-- OMEMO
	debug_info.omemo = get_user_omemo_info(username);

	return debug_info;
end

function list_users(event)
	local user_list = {};
	for username in usermanager.users(module.host) do
		table.insert(user_list, get_user_info(username));
	end

	event.response.headers["Content-Type"] = json_content_type;
	return json.encode_array(user_list);
end

function get_user_by_name(event, username)
	local property
	do
		local name, sub_path = username:match("^([^/]+)/(%w+)$");
		if name then
			username = name;
			property = sub_path;
		end
	end

	if property == "groups" then
		event.response.headers["Content-Type"] = json_content_type;
		return json.encode(mod_groups.get_user_groups(username));
	elseif property == "debug" then
		event.response.headers["Content-Type"] = json_content_type;
		return json.encode(get_user_debug_info(username));
	end

	local user_info = get_user_info(username);
	if not user_info then
		return 404;
	end

	event.response.headers["Content-Type"] = json_content_type;
	return json.encode(user_info);
end

local user_attribute_writers = {
	enabled = function (username, enabled)
		local ok, err;
		if enabled == true then
			ok, err = usermanager.enable_user(username, module.host);
		elseif enabled == false then
			ok, err = usermanager.disable_user(username, module.host);
		else
			ok, err = nil, "Invalid value provided for 'enabled'";
		end
		if not ok then
			module:log("error", "Unable to %s user '%s': %s", enabled and "enable" or "disable", username, err);
			return nil, err;
		end
		return true;
	end;
};
local writable_user_attributes = set.new(array.collect(it.keys(user_attribute_writers)));

function patch_user(event, username)
	if not username then return; end

	local current_user = get_user_info(username);
	if not current_user then return 404; end

	local request = event.request;
	if request.headers.content_type ~= json_content_type
	or (not request.body or #request.body == 0) then
		return 400;
	end
	local new_user = json.decode(event.request.body);
	if not new_user then
		return 400;
	end

	local updated_attributes = set.new(array.collect(it.keys(new_user)));
	if not (updated_attributes - writable_user_attributes):empty() then
		module:log("warn", "Unable to service PATCH user request, unsupported attributes: %s", (updated_attributes - writable_user_attributes));
		return 400;
	end

	if new_user.enabled ~= nil and new_user.enabled ~= current_user.enabled then
		if not user_attribute_writers.enabled(username, new_user.enabled) then
			return 500;
		end
	end

	return 200;
end

function update_user(event, username)
	if not username then
		return 400;
	end

	local request = event.request;
	if request.headers.content_type ~= json_content_type
	or (not request.body or #request.body == 0) then
		return 400;
	end
	local new_user = json.decode(event.request.body);
	if not new_user then
		return 400;
	end

	if new_user.username and new_user.username ~= username then
		return 400;
	end

	if new_user.display_name then
		local pep_service = mod_pep.get_pep_service(username);
		-- TODO: publish
		local nick_item = st.stanza("item", { xmlns = xmlns_pubsub, id = "current" })
			:text_tag("nick", new_user.display_name, { xmlns = xmlns_nick });
		pep_service:publish(xmlns_nick, true, "current", nick_item, {
			access_model = "open";
			_defaults_only = true;
		});
	end

	if new_user.role then
		if not usermanager.set_user_role then
			return 500, "feature-not-implemented";
		end
		if not usermanager.set_user_role(username, module.host, new_user.role) then
			module:log("error", "failed to set role %s for %s", new_user.role, username);
			return 500;
		end
	end

	if new_user.roles then -- COMPAT w/0.12
		if not usermanager.set_user_roles then
			return 500, "feature-not-implemented"
		end

		local backend_roles = {};
		for _, role in ipairs(new_user.roles) do
			backend_roles[role] = true;
		end
		local user_jid = username.."@"..module.host;
		if not usermanager.set_user_roles(username, module.host, backend_roles) then
			module:log("error", "failed to set roles %q for %s", backend_roles, user_jid)
			return 500
		end
	end

	if new_user.enabled ~= nil then
		if not user_attribute_writers.enabled(username, new_user.enabled) then
			return 500;
		end
	end

	return 200;
end

function delete_user(event, username) --luacheck: ignore 212/event
	if not usermanager.delete_user(username, module.host) then
		return 404;
	end
	return 200;
end

function list_groups(event)
	local group_list = {};
	for group_id in mod_groups.groups() do
		local group_info = mod_groups.get_info(group_id);
		table.insert(group_list, {
			id = group_id;
			name = group_info.name;
			members = mod_groups.get_members(group_id);
			chats = mod_groups.get_group_chats(group_id);
		});
	end

	event.response.headers["Content-Type"] = json_content_type;
	return json.encode_array(group_list);
end

function get_group_by_id(event, group_id)
	local group = mod_groups.get_info(group_id);
	if not group then
		return 404;
	end

	event.response.headers["Content-Type"] = json_content_type;

	return json.encode({
		id = group_id;
		name = group.name;
		members = mod_groups.get_members(group_id);
		chats = mod_groups.get_group_chats(group_id);
	});
end

function create_group(event)
	local request = event.request;
	if request.headers.content_type ~= json_content_type
	or (not request.body or #request.body == 0) then
		return 400;
	end
	local group = json.decode(event.request.body);
	if not group then
		return 400;
	end

	if not group.name then
		module:log("warn", "Group missing name property");
		return 400;
	end

	local create_muc = group.create_muc and true or false;

	local group_id = mod_groups.create(
		{
			name = group.name;
		},
		create_muc
	);
	if not group_id then
		return 500;
	end

	event.response.headers["Content-Type"] = json_content_type;

	local info = mod_groups.get_info(group_id);
	return json.encode({
		id = group_id;
		name = info.name;
		members = {};
		chats = {};
	});
end

function update_group(event, group) --luacheck: ignore 212/event
	-- Add member
	do
		local group_id, member_name = group:match("^([^/]+)/members/([^/]+)$");
		if group_id and member_name then
			if not mod_groups.add_member(group_id, member_name) then
				return 500;
			end
			return 204;
		end
	end

	local group_id = group:match("^([^/]+)$")
	if not group_id then return 404; end

	local request = event.request;
	if request.headers.content_type ~= json_content_type or (not request.body or #request.body == 0) then
		return 400;
	end

	local update = json.decode(event.request.body);
	if not update then
		return 400;
	end

	local group_info = mod_groups.get_info(group_id);
	if not group_info then
		return 404;
	end

	if update.name then
		group_info["name"] = update.name;
	end
	if not mod_groups.set_info(group_id, group_info) then
		return 500;
	end
	return 204;
end

function extend_group(event, subpath)
	-- Add group chat
	local group_id = subpath:match("^([^/]+)/chats$");
	if group_id then
		local muc_params = json.decode(event.request.body);
		if not muc_params then
			return 400;
		end
		local muc = mod_groups.add_group_chat(group_id, muc_params.name);
		if not muc then
			return 500;
		end
		return json.encode(muc);
	end

	return 404;
end

function delete_group(event, subpath) --luacheck: ignore 212/event
	-- Check if this is a membership deletion and handle it
	local group_id, sub_resource_type, sub_resource_id = subpath:match("^([^/]+)/([^/]+)/([^/]+)$");
	if group_id then
		-- Operation is on a sub-resource
		if sub_resource_type == "members" then
			if mod_groups.remove_member(group_id, sub_resource_id) then
				return 204;
			else
				return 500;
			end
		elseif sub_resource_type == "chats" then
			if mod_groups.remove_group_chat(group_id, sub_resource_id) then
				return 204;
			else
				return 500;
			end
		else
			return 404;
		end
	else
		-- Action refers to the group
		group_id = subpath;
	end

	if not group_id then
		return 400;
	end

	if not mod_groups.exists(group_id) then
		return 404;
	end

	if not mod_groups.delete(group_id) then
		return 500;
	end
	return 204;
end

local function get_server_info(event)
	event.response.headers["Content-Type"] = json_content_type;
	return json.encode({
		site_name = site_name;
		version = prosody.version;
	});
end

local function maybe_export_plain_gauge(mf)
	if mf == nil then
		return nil
	end
	return mf.data.value
end

local function maybe_export_plain_counter(mf)
	if mf == nil then
		return nil
	end
	return {
		since = mf.data._created,
		value = mf.data.value,
	}
end

local function maybe_export_summed_gauge(mf)
	if mf == nil then
		return nil
	end
	local sum = 0;
	for _, metric in mf:iter_metrics() do
		sum = sum + metric.value;
	end
	return (sum == sum) and sum or nil; -- Filter out nan
end

local function get_server_metrics(event)
	event.response.headers["Content-Type"] = json_content_type;
	local result = {};
	if manual_stats_collection then
		statsmanager.collect();
	end
	local families = statsmanager.get_metric_registry():get_metric_families();
	result.memory = maybe_export_plain_gauge(families.process_resident_memory_bytes);
	result.cpu = maybe_export_plain_counter(families.process_cpu_seconds);
	result.c2s = maybe_export_summed_gauge(families["prosody_mod_c2s/connections"])
	result.uploads = maybe_export_summed_gauge(families["prosody_mod_http_file_share/total_storage_bytes"]);
	result.users = {
		active_1d = maybe_export_summed_gauge(families["prosody_mod_measure_active_users/active_users_1d"]);
		active_7d = maybe_export_summed_gauge(families["prosody_mod_measure_active_users/active_users_7d"]);
		active_30d = maybe_export_summed_gauge(families["prosody_mod_measure_active_users/active_users_30d"]);
	};
	return json.encode(result);
end

local function post_server_announcement(event)
	local request = event.request;
	if request.headers.content_type ~= json_content_type
	or (not request.body or #request.body == 0) then
		return 400;
	end
	local body = json.decode(event.request.body);
	if not body then
		return 400;
	end

	if type(body.recipients) ~= "table" and body.recipients ~= "online" and body.recipients ~= "all" then
		return 400;
	end

	if not body.body or #body.body == 0 then
		return 400;
	end

	local message = st.message():tag("body"):text(body.body):up();
	local host = module.host
	message.attr.from = host
	if body.recipients == "online" then
		announce.send_to_online(message, host);
	elseif body.recipients == "all" then
		if announce.send_to_all then
			announce.send_to_all(message, host);
		else -- COMPAT w/ 0.12 and trunk before e22609460975
			for username in usermanager.users(host) do
				message.attr.to = username .. "@" .. host
				module:send(st.clone(message))
			end
		end
	else
		for _, addr in ipairs(body.recipients) do
			message.attr.to = addr
			module:send(message)
		end
	end

	return 201;
end

module:provides("http", {
	route = check_auth {
		["GET /invites"] = list_invites;
		["GET /invites/*"] = get_invite_by_id;
		["POST /invites/*"] = create_invite_type;
		["DELETE /invites/*"] = delete_invite;

		["GET /users"] = list_users;
		["GET /users/*"] = get_user_by_name;
		["PUT /users/*"] = update_user;
		["PATCH /users/*"] = patch_user;
		["DELETE /users/*"] = delete_user;

		["GET /groups"] = list_groups;
		["GET /groups/*"] = get_group_by_id;
		["POST /groups"] = create_group;
		["POST /groups/*"] = extend_group;
		["PUT /groups/*"] = update_group;
		["DELETE /groups/*"] = delete_group;

		["GET /server/info"] = get_server_info;

		["GET /server/metrics"] = get_server_metrics;
		["POST /server/announcement"] = post_server_announcement;
	};
});
