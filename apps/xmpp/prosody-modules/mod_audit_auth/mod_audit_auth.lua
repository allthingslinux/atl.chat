local cache = require "util.cache";
local jid = require "util.jid";
local st = require "util.stanza";

module:depends("audit");
-- luacheck: read globals module.audit

local only_passwords = module:get_option_boolean("audit_auth_passwords_only", true);
local cache_size = module:get_option_number("audit_auth_cache_size", 128);
local repeat_failure_timeout = module:get_option_number("audit_auth_repeat_failure_timeout");
local repeat_success_timeout = module:get_option_number("audit_auth_repeat_success_timeout");

local failure_cache = cache.new(cache_size);
module:hook("authentication-failure", function(event)
	local session = event.session;

	local username = session.sasl_handler.username;
	if repeat_failure_timeout then
		local cache_key = ("%s\0%s"):format(username, session.ip);
		local last_failure = failure_cache:get(cache_key);
		local now = os.time();
		if last_failure and (now - last_failure) > repeat_failure_timeout then
			return;
		end
		failure_cache:set(cache_key, now);
	end

	module:audit(jid.join(username, module.host), "authentication-failure", {
		session = session;
	});
end)

local success_cache = cache.new(cache_size);
module:hook("authentication-success", function(event)
	local session = event.session;
	if only_passwords and session.sasl_handler.fast then
		return;
	end

	local username = session.sasl_handler.username;
	if repeat_success_timeout then
		local cache_key = ("%s\0%s"):format(username, session.ip);
		local last_success = success_cache:get(cache_key);
		local now = os.time();
		if last_success and (now - last_success) > repeat_success_timeout then
			return;
		end
		success_cache:set(cache_key, now);
	end

	module:audit(jid.join(username, module.host), "authentication-success", {
		session = session;
	});
end)

module:hook("client_management/new-client", function (event)
	local session, client = event.session, event.client;

	local client_info = st.stanza("client", { id = client.id });

	if client.user_agent then
		local user_agent = st.stanza("user-agent", { xmlns = "urn:xmpp:sasl:2" })
		if client.user_agent.software then
			user_agent:text_tag("software", client.user_agent.software, { id = client.user_agent.software_id; version = client.user_agent.software_version });
		end
		if client.user_agent.device then
			user_agent:text_tag("device", client.user_agent.device);
		end
		if client.user_agent.uri then
			user_agent:text_tag("uri", client.user_agent.uri);
		end
		client_info:add_child(user_agent);
	end

	if client.legacy then
		client_info:text_tag("legacy");
	end

	module:audit(jid.join(session.username, module.host), "new-client", {
		session = session;
		custom = {
		};
	});
end);
