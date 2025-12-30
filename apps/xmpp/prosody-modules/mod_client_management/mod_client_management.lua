local modulemanager = require "core.modulemanager";
local usermanager = require "core.usermanager";

local array = require "util.array";
local dt = require "util.datetime";
local id = require "util.id";
local it = require "util.iterators";
local jid = require "util.jid";
local st = require "util.stanza";

local strict = module:get_option_boolean("enforce_client_ids", false);

module:default_permission("prosody:registered", ":list-clients");
module:default_permission("prosody:registered", ":manage-clients");

local tokenauth = module:depends("tokenauth");
local mod_fast = module:depends("sasl2_fast");

local client_store = assert(module:open_store("clients", "keyval+"));
--[[{
	id = id;
	first_seen =
	last_seen =
	user_agent = {
		name =
		os =
	}
--}]]

local xmlns_sasl2 = "urn:xmpp:sasl:2";

local function get_user_agent(sasl_handler, token_info)
	local sasl_agent = sasl_handler and sasl_handler.user_agent;
	local token_agent = token_info and token_info.data and token_info.data.oauth2_client;
	if not (sasl_agent or token_agent) then return; end
	return {
		software = sasl_agent and sasl_agent.software or token_agent and token_agent.name or nil;
		software_id = token_agent and token_agent.id or nil;
		software_version = token_agent and token_agent.version or nil;
		uri = token_agent and token_agent.uri or nil;
		device = sasl_agent and sasl_agent.device or nil;
	};
end

module:hook("sasl2/c2s/success", function (event)
	local session = event.session;
	local username, client_id = session.username, session.client_id;
	local mechanism = session.sasl_handler.selected;
	local token_info = session.sasl_handler.token_info;
	local token_id = token_info and token_info.id or nil;

	local now = os.time();
	if client_id then -- SASL2, have client identifier
		local is_new_client;

		local client_state = client_store:get_key(username, client_id);
		if not client_state then
			is_new_client = true;
			client_state = {
				id = client_id;
				first_seen = now;
				user_agent = get_user_agent(session.sasl_handler, token_info);
				full_jid = nil;
				last_seen = nil;
				mechanisms = {};
			};
		end
		-- Update state
		client_state.full_jid = session.full_jid;
		client_state.last_seen = now;
		client_state.mechanisms[mechanism] = now;
		if session.sasl_handler.fast_auth then
			client_state.fast_auth = now;
		end
		if token_id then
			client_state.auth_token_id = token_id;
		end
		-- Store updated state
		client_store:set_key(username, client_id, client_state);

		if is_new_client then
			module:fire_event("client_management/new-client", { client = client_state; session = session });
		end
	end
end);

local function find_client_by_resource(username, resource)
	local full_jid = jid.join(username, module.host, resource);
	local clients = client_store:get(username);
	if not clients then return; end

	for _, client_state in pairs(clients) do
		if client_state.full_jid == full_jid then
			return client_state;
		end
	end
end

module:hook("resource-bind", function (event)
	local session = event.session;
	if session.client_id then return; end
	local is_new_client;
	local client_state = find_client_by_resource(event.session.username, event.session.resource);
	local now = os.time();
	if not client_state then
		is_new_client = true;
		client_state = {
			id = id.short();
			first_seen = now;
			user_agent = nil;
			full_jid = nil;
			last_seen = nil;
			mechanisms = {};
			legacy = true;
		};
	end

	-- Update state
	client_state.full_jid = session.full_jid;
	client_state.last_seen = now;

	local legacy_info = session.client_management_info;
	if legacy_info then
		client_state.mechanisms[legacy_info.mechanism] = now;
		if legacy_info.fast_auth then
			client_state.fast_auth = now;
		end

		local token_id = legacy_info.token_info and legacy_info.token_info.id;
		if token_id then
			client_state.auth_token_id = token_id;
		end
	else
		session.log("warn", "Missing client management info")
	end

	-- Store updated state
	client_store:set_key(session.username, client_state.id, client_state);

	if is_new_client then
		module:fire_event("client_management/new-client", { client = client_state; session = session });
	end
end);

if strict then
	module:hook_tag(xmlns_sasl2, "authenticate", function (session, auth)
		local user_agent = auth:get_child("user-agent");
		if not user_agent or not user_agent.attr.id then
			local failure = st.stanza("failure", { xmlns = xmlns_sasl2 })
				:tag("malformed-request", { xmlns = "urn:ietf:params:xml:ns:xmpp-sasl" }):up()
				:text_tag("text", "Client identifier required but not supplied");
			session.send(failure);
			return true;
		end
	end, 500);

	if modulemanager.get_modules_for_host(module.host):contains("saslauth") then
		module:log("error", "mod_saslauth is enabled, but enforce_client_ids is enabled and will prevent it from working");
	end

	module:hook("stanza/urn:ietf:params:xml:ns:xmpp-sasl:auth", function (event)
		-- Block legacy SASL, if for some reason it is being used (either mod_saslauth is loaded,
		-- or clients try it without advertisement)
		module:log("warn", "Blocking legacy SASL authentication because enforce_client_ids is enabled");
		local failure = st.stanza("failure", { xmlns = xmlns_sasl2 })
			:tag("malformed-request", { xmlns = "urn:ietf:params:xml:ns:xmpp-sasl" }):up()
			:text_tag("text", "Legacy SASL authentication is not available on this server");
		event.session.send(failure);
		return true;
	end);
else
	-- Legacy client compat code
	module:hook("authentication-success", function (event)
		local session = event.session;
		if session.client_id then return; end -- SASL2 client

		local sasl_handler = session.sasl_handler;
		session.client_management_info = {
			mechanism = sasl_handler.selected;
			token_info = sasl_handler.token_info;
			fast_auth = sasl_handler.fast_auth;
		};
	end);
end

local function is_password_mechanism(mech_name)
	if mech_name == "OAUTHBEARER" then return false; end
	if mech_name:match("^HT%-") then return false; end
	return true;
end

local function is_client_active(client)
	if not client.full_jid then
		return nil;
	end
	local username, host = jid.split(client.full_jid);
	local account_info = usermanager.get_account_info(username, host);
	local last_password_change = account_info and account_info.password_updated;

	local status = {};

	-- Check for an active token grant that has been previously used by this client
	if client.auth_token_id then
		local grant = tokenauth.get_grant_info(client.auth_token_id);
		if grant then
			status.grant = grant;
		end
	end

	-- Check for active FAST tokens
	if client.fast_auth then
		if mod_fast.is_client_fast(username, client.id, last_password_change) then
			status.fast = client.fast_auth;
		end
	end

	-- Client has access if any password-based SASL mechanisms have been used since last password change
	for mech, mech_last_used in pairs(client.mechanisms) do
		if is_password_mechanism(mech) and (not last_password_change or mech_last_used >= last_password_change) then
			status.password = mech_last_used;
		end
	end

	if prosody.full_sessions[client.full_jid] then
		status.connected = true;
	end

	if next(status) == nil then
		return nil;
	end
	return status;
end

-- Public API
--luacheck: ignore 131
function get_active_clients(username)
	local clients = client_store:get(username);
	local active_clients = {};
	local used_grants = {};

	-- Go through known clients, check whether they could possibly log in
	for client_id, client in pairs(clients or {}) do --luacheck: ignore 213/client_id
		local active = is_client_active(client);
		if active then
			client.type = "session";
			client.id = "client/"..client.id;
			client.active = active;
			table.insert(active_clients, client);
			if active.grant then
				used_grants[active.grant.id] = true;
			end
		end
	end

	-- Next, account for any grants that have been issued, but never actually logged in
	for grant_id, grant in pairs(tokenauth.get_user_grants(username) or {}) do
		if not used_grants[grant_id] then -- exclude grants already accounted for
			table.insert(active_clients, {
				id = "grant/"..grant_id;
				type = "access";
				first_seen = grant.created;
				last_seen = grant.accessed;
				expires = grant.expires;
				active = {
					grant = grant;
				};
				user_agent = get_user_agent(nil, grant);
			});
		end
	end

	table.sort(active_clients, function (a, b)
		if a.last_seen and b.last_seen then
			return a.last_seen < b.last_seen;
		elseif not (a.last_seen or b.last_seen) then
			if a.first_seen and b.first_seen then
				return a.first_seen < b.first_seen;
			end
		elseif b.last_seen then
			return true;
		elseif a.last_seen then
			return false;
		end
		return a.id < b.id;
	end);

	return active_clients;
end

local function user_agent_tostring(user_agent)
	if user_agent then
		if user_agent.software then
			if user_agent.software_version then
				return user_agent.software .. "/" .. user_agent.software_version;
			end
			return user_agent.software;
		end
	end
end

function revoke_client_access(username, client_selector)
	if client_selector then
		local c_type, c_id = client_selector:match("^(%w+)/(.+)$");
		if c_type == "client" then
			local client = client_store:get_key(username, c_id);
			if not client then
				return nil, "item-not-found";
			end
			local status = is_client_active(client);
			if status.connected then
				local ok, err = prosody.full_sessions[client.full_jid]:close();
				if not ok then return ok, err; end
			end
			if status.fast then
				local ok = mod_fast.revoke_fast_tokens(username, client.id);
				if not ok then return nil, "internal-server-error"; end
			end
			if status.grant then
				local ok = tokenauth.revoke_grant(username, status.grant.id);
				if not ok then return nil, "internal-server-error"; end
			end
			if status.password then
				return nil, "password-reset-required";
			end
			return true;
		elseif c_type == "grant" then
			local grant = tokenauth.get_grant_info(username, c_id);
			if not grant then
				return nil, "item-not-found";
			end
			local ok = tokenauth.revoke_grant(username, c_id);
			if not ok then return nil, "internal-server-error"; end
			return true;
		elseif c_type == "software" then
			local active_clients = get_active_clients(username);
			for _, client in ipairs(active_clients) do
				if client.user_agent and client.user_agent.software == c_id or user_agent_tostring(client.user_agent) == c_id then
					return revoke_client_access(username, client.id);
				end
			end
		end
	end

	return nil, "item-not-found";
end

-- Protocol

local xmlns_manage_clients = "xmpp:prosody.im/protocol/manage-clients";

module:hook("iq-get/self/xmpp:prosody.im/protocol/manage-clients:list", function (event)
	local origin, stanza = event.origin, event.stanza;

	if not module:may(":list-clients", event) then
		origin.send(st.error_reply(stanza, "auth", "forbidden"));
		return true;
	end

	local reply = st.reply(stanza)
		:tag("clients", { xmlns = xmlns_manage_clients });

	local active_clients = get_active_clients(event.origin.username);
	for _, client in ipairs(active_clients) do
		local auth_type = st.stanza("auth");
		if client.active then
			if client.active.password then
				auth_type:text_tag("password");
			end
			if client.active.grant then
				auth_type:text_tag("bearer-token");
			end
			if client.active.fast then
				auth_type:text_tag("fast");
			end
		end

		local user_agent = st.stanza("user-agent");
		if client.user_agent then
			if client.user_agent.software then
				user_agent:text_tag("software", client.user_agent.software, { id = client.user_agent.software_id; version = client.user_agent.software_version });
			end
			if client.user_agent.device then
				user_agent:text_tag("device", client.user_agent.device);
			end
			if client.user_agent.uri then
				user_agent:text_tag("uri", client.user_agent.uri);
			end
		end

		local connected = client.active and client.active.connected;
		reply:tag("client", { id = client.id, connected = connected and "true" or "false", type = client.type })
			:text_tag("first-seen", dt.datetime(client.first_seen))
			:text_tag("last-seen", dt.datetime(client.last_seen))
			:add_child(auth_type)
			:add_child(user_agent)
			:up();
	end
	reply:up();

	origin.send(reply);
	return true;
end);

local revocation_errors = require "util.error".init(module.name, xmlns_manage_clients, {
	["item-not-found"] = { "cancel", "item-not-found", "Client not found" };
	["internal-server-error"] = { "wait", "internal-server-error", "Unable to revoke client access" };
	["password-reset-required"] = { "cancel", "service-unavailable", "Password reset required", "password-reset-required" };
});

module:hook("iq-set/self/xmpp:prosody.im/protocol/manage-clients:revoke", function (event)
	local origin, stanza = event.origin, event.stanza;

	if not module:may(":manage-clients", event) then
		origin.send(st.error_reply(stanza, "auth", "forbidden"));
		return true;
	end

	local client_id = stanza.tags[1].attr.id;

	local ok, err = revocation_errors.coerce(revoke_client_access(origin.username, client_id));
	if not ok then
		origin.send(st.error_reply(stanza, err));
		return true;
	end

	origin.send(st.reply(stanza));
	return true;
end);


-- Command

module:add_item("shell-command", {
	section = "user";
	name = "clients";
	desc = "List a user's clients";
	args = {
		{ name = "jid"; type = "string" }
	};
	host_selector = "jid";
	handler = function(self, user_jid)
		local username = jid.split(user_jid);

		local clients = get_active_clients(username);
		if not clients or #clients == 0 then
			return true, "No clients associated with this account";
		end

		local function date_or_time(last_seen)
			return last_seen and os.date(math.abs(os.difftime(os.time(), last_seen)) >= 86400 and "%Y-%m-%d" or "%H:%M:%S", last_seen);
		end

		local date_or_time_width = math.max(#os.date("%Y-%m-%d"), #os.date("%H:%M:%S"));

		local colspec = {
			{ title = "ID"; key = "id"; width = "1p" };
			{
				title = "Software";
				key = "user_agent";
				width = "1p";
				mapper = user_agent_tostring;
			};
			{
				title = "First seen";
				key = "first_seen";
				width = date_or_time_width;
				align = "right";
				mapper = date_or_time;
			};
			{
				title = "Last seen";
				key = "last_seen";
				width = date_or_time_width;
				align = "right";
				mapper = date_or_time;
			};
			{
				title = "Expires";
				key = "active";
				width = date_or_time_width;
				align = "right";
				mapper = function(active, client)
					local grant = active and active.grant;
					local expires = client and client.expires;
					local tokens = grant and grant.tokens;
					if expires or not tokens then
						return date_or_time(expires);
					end

					for _, token in pairs(tokens) do
						if token.expires and (not expires or token.expires > expires) then
							expires = token.expires;
						end
					end
					return date_or_time(expires);
				end;
			};
			{
				title = "Authentication";
				key = "active";
				width = "2p";
				mapper = function(active)
					return array.collect(it.keys(active)):sort():concat(", ");
				end;
			};
		};

		local row = require "util.human.io".table(colspec, self.session.width);

		local print = self.session.print;
		print(row());
		print(string.rep("-", self.session.width));
		for _, client in ipairs(clients) do
			print(row(client));
		end
		print(string.rep("-", self.session.width));
		return true, ("%d clients"):format(#clients);
	end
});

module:add_item("shell-command", {
	section = "user";
	name = "revoke_client";
	desc = "Revoke access from a user's client";
	args = {
		{ name = "jid"; type = "string" };
		{ name = "selector"; type = "string" };
	};
	host_selector = "jid";
	handler = function(self, user_jid, selector) -- luacheck: ignore 212/self
		local username = jid.split(user_jid);

		local revoked, err = revocation_errors.coerce(revoke_client_access(username, selector));
		if not revoked then
			return false, err.text or err;
		end
		return true, "Client access revoked";
	end
});
