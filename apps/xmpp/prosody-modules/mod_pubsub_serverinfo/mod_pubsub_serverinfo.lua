local http = require "net.http";
local json = require "util.json";
local st = require "util.stanza";
local new_id = require"util.id".medium;

local local_domain = module:get_host();
local service = module:get_option_string(module.name .. "_service");
local node = module:get_option_string(module.name .. "_node", "serverinfo");
local actor = module.host .. "/modules/" .. module.name;
local publication_interval = module:get_option_number(module.name .. "_publication_interval", 300);
local cache_ttl = module:get_option_number(module.name .. "_cache_ttl", 3600);
local public_providers_url = module:get_option_string(module.name.."_public_providers_url", "https://data.xmpp.net/providers/v2/providers-Ds.json");
local delete_node_on_unload = module:get_option_boolean(module.name.."_delete_node_on_unload", false);
local persist_items = module:get_option_boolean(module.name.."_persist_items", true);
local include_user_count = module:get_option_boolean(module.name.."_publish_user_count", false);

if not service and prosody.hosts["pubsub."..module.host] then
	service = "pubsub."..module.host;
end
if not service then
	module:log_status("warn", "No pubsub service specified - module not activated");
	return;
end

local metric_registry = require "core.statsmanager".get_metric_registry();
if include_user_count then
	module:depends("measure_active_users");
end

local xmlns_pubsub = "http://jabber.org/protocol/pubsub";

-- Needed to publish server-info-fields
module:depends("server_info");

function module.load()
	discover_node():next(
		function(exists)
			if not exists then create_node() end
		end
	):catch(
		function(error)
			module:log("warn", "Error prevented discovery or creation of pub/sub node at %s: %s", service, error)
		end
	)

	module:add_feature("urn:xmpp:serverinfo:0");

	module:add_item("server-info-fields", {
		{ name = "serverinfo-pubsub-node", type = "text-single", value = ("xmpp:%s?;node=%s"):format(service, node) };
	});

	if cache_ttl < publication_interval then
		module:log("warn", "It is recommended to have a cache interval higher than the publication interval");
	end

	cache_warm_up()
	module:add_timer(10, publish_serverinfo);
end

function module.unload()
	-- This removes all subscribers, which may or may not be desirable, depending on the reason for the unload.
	if delete_node_on_unload then
		delete_node();
	end
end

-- Returns a promise of a boolean
function discover_node()
	local request = st.iq({ type = "get", to = service, from = actor, id = new_id() })
		:tag("query", { xmlns = "http://jabber.org/protocol/disco#items" })

	module:log("debug", "Sending request to discover existence of pub/sub node '%s' at %s", node, service)
	return module:send_iq(request):next(
		function(response)
			if response.stanza == nil or response.stanza.attr.type ~= "result" then
				module:log("warn", "Unexpected response to service discovery items request at %s: %s", service, response.stanza)
				return false
			end

			local query = response.stanza:get_child("query", "http://jabber.org/protocol/disco#items")
			if query ~= nil then
				for item in query:childtags("item") do
					if item.attr.jid == service and item.attr.node == node then
						module:log("debug", "pub/sub node '%s' at %s does exist.", node, service)
						return true
					end
				end
			end
			module:log("debug", "pub/sub node '%s' at %s does not exist.", node, service)
			return false;
		end
	);
end

-- Returns a promise of a boolean
function create_node()
	local request = st.iq({ type = "set", to = service, from = actor, id = new_id() })
		:tag("pubsub", { xmlns = xmlns_pubsub })
			:tag("create", { node = node, xmlns = xmlns_pubsub }):up()
			:tag("configure", { xmlns = xmlns_pubsub })
				:tag("x", { xmlns = "jabber:x:data", type = "submit" })
					:tag("field", { var = "FORM_TYPE", type = "hidden"})
						:text_tag("value", "http://jabber.org/protocol/pubsub#node_config")
						:up()
					:tag("field", { var = "pubsub#max_items" })
						:text_tag("value", "1")
						:up()
					:tag("field", { var = "pubsub#persist_items" })
						:text_tag("value", persist_items and "1" or "0")

	module:log("debug", "Sending request to create pub/sub node '%s' at %s", node, service)
	return module:send_iq(request):next(
		function(response)
			if response.stanza == nil or response.stanza.attr.type ~= "result" then
				module:log("warn", "Unexpected response to pub/sub node '%s' creation request at %s: %s", node, service, response.stanza)
				return false
			else
				module:log("debug", "Successfully created pub/sub node '%s' at %s", node, service)
				return true
			end
		end
	)
end

-- Returns a promise of a boolean
function delete_node()
	local request = st.iq({ type = "set", to = service, from = actor, id = new_id() })
		:tag("pubsub", { xmlns = xmlns_pubsub })
			:tag("delete", { node = node, xmlns = xmlns_pubsub });

	module:log("debug", "Sending request to delete pub/sub node '%s' at %s", node, service)
	return module:send_iq(request):next(
		function(response)
			if response.stanza == nil or response.stanza.attr.type ~= "result" then
				module:log("warn", "Unexpected response to pub/sub node '%s' deletion request at %s: %s", node, service, response.stanza)
				return false
			else
				module:log("debug", "Successfully deleted pub/sub node '%s' at %s", node, service)
				return true
			end
		end
	)
end

function get_remote_domain_names()
	-- Iterate over s2s sessions, adding them to a multimap, where the key is the local domain name,
	-- mapped to a collection of remote domain names. De-duplicate all remote domain names by using
	-- them as an index in a table.
	local domains_by_host = {}
	for session, _ in pairs(prosody.incoming_s2s) do
		if session ~= nil and session.from_host ~= nil and local_domain == session.to_host then
			module:log("debug", "Local host '%s' has remote '%s' (inbound)", session.to_host, session.from_host);
			local sessions = domains_by_host[session.to_host]
			if sessions == nil then sessions = {} end; -- instantiate a new entry if none existed
			sessions[session.from_host] = true
			domains_by_host[session.to_host] = sessions
		end
	end

	-- At an earlier stage, the code iterated over all prosody.hosts, trying to generate one pubsub item for all local hosts. That turned out to be
	-- to noisy. Instead, this code now creates an item that includes the local vhost only. It is assumed that this module will also be loaded for
	-- other vhosts. Their data should then be published to distinct pub/sub services and nodes.

	-- for host, data in pairs(prosody.hosts) do
	local host = local_domain
	local data = prosody.hosts[host]
	if data ~= nil then
		local sessions = domains_by_host[host]
		if sessions == nil then sessions = {} end; -- instantiate a new entry if none existed
		if data.s2sout ~= nil then
			for _, session in pairs(data.s2sout) do
				if session.to_host ~= nil then
					module:log("debug", "Local host '%s' has remote '%s' (outbound)", host, session.to_host);
					sessions[session.to_host] = true
					domains_by_host[host] = sessions
				end
			end
		end

		-- When the instance of Prosody hosts more than one host, the other hosts can be thought of as having a 'permanent' s2s connection.
		for host_name, host_info in pairs(prosody.hosts) do
			if host ~= host_name and host_info.type ~= "component" then
				module:log("debug", "Local host '%s' has remote '%s' (vhost)", host, host_name);
				sessions[host_name] = true;
				domains_by_host[host] = sessions
			end
		end
	end

	return domains_by_host
end

local function get_gauge_metric(name)
	return (metric_registry.families[name].data:get(module.host) or {}).value;
end

function publish_serverinfo()
	module:log("debug", "Publishing server info...");
	local domains_by_host = get_remote_domain_names()

	-- Build the publication stanza.
	local request = st.iq({ type = "set", to = service, from = actor, id = new_id() })
		:tag("pubsub", { xmlns = xmlns_pubsub })
			:tag("publish", { node = node, xmlns = xmlns_pubsub })
				:tag("item", { id = "current", xmlns = xmlns_pubsub })
					:tag("serverinfo", { xmlns = "urn:xmpp:serverinfo:0" })

	request:tag("domain", { name = local_domain })
		:tag("federation")

	local remotes = domains_by_host[local_domain]

	if remotes ~= nil then
		for remote, _ in pairs(remotes) do
			-- include a domain name for remote domains, but only if they advertise support.
			if does_opt_in(remote) then
				request:tag("remote-domain", { name = remote }):up()
			else
				request:tag("remote-domain"):up()
			end
		end
	end

	request:up();

	if include_user_count then
		local mau = get_gauge_metric("prosody_mod_measure_active_users/active_users_30d");
		request:tag("users", { xmlns = "xmpp:prosody.im/protocol/serverinfo" });
		if mau then
			request:text_tag("active", ("%d"):format(mau));
		end
		request:up();
	end

	request:up()

	module:send_iq(request):next(
		function(response)
			if response.stanza == nil or response.stanza.attr.type ~= "result" then
				module:log("warn", "Unexpected response to item publication at pub/sub node '%s' on %s: %s", node, service, response.stanza)
				return false
			else
				module:log("debug", "Successfully published item on pub/sub node '%s' at %s", node, service)
				return true
			end
		end,
		function(error)
			module:log("warn", "Error prevented publication of item on pub/sub node at %s: %s", service, error)
		end
	)

	return publication_interval;
end

local opt_in_cache = {}

-- Public providers are already public, so we fetch the list of providers
-- registered on providers.xmpp.net so we don't have to disco them individually
local function update_public_providers()
	return http.request(public_providers_url)
		:next(function (response)
			assert(
				response.headers["content-type"] == "application/json",
				"invalid mimetype: "..tostring(response.headers["content-type"])
			);
			return json.decode(response.body);
		end)
		:next(function (public_server_domains)
			module:log("debug", "Retrieved list of %d public providers", #public_server_domains);
			for _, domain in ipairs(public_server_domains) do
				opt_in_cache[domain] = {
					opt_in = true;
					expires = os.time() + (86400 * 1.5);
				};
			end
		end, function (err)
			module:log("warn", "Failed to fetch/decode provider list: %s", err);
		end);
end

module:daily("update public provider list", update_public_providers);

function cache_warm_up()
	module:log("debug", "Warming up opt-in cache")

	update_public_providers():finally(function ()
		module:log("debug", "Querying known domains for opt-in cache...");
		local domains_by_host = get_remote_domain_names()
		local remotes = domains_by_host[local_domain]
		if remotes ~= nil then
			for remote in pairs(remotes) do
				does_opt_in(remote)
			end
		end
	end);
end

function does_opt_in(remoteDomain)

	-- try to read answer from cache.
	local cached_value = opt_in_cache[remoteDomain]
	local ttl = cached_value and os.difftime(cached_value.expires, os.time());
	if cached_value and ttl > (publication_interval + 60) then
		module:log("debug", "Opt-in status (from cache) for '%s': %s", remoteDomain, cached_value.opt_in)
		return cached_value.opt_in;
	end

	-- We don't have a cached value, or it is nearing expiration - refresh it now
	-- TODO worry about not having multiple requests in flight to the same domain.cached_value

	module:log("debug", "%s: performing disco/info to determine opt-in", remoteDomain)
	local discoRequest = st.iq({ type = "get", to = remoteDomain, from = actor, id = new_id() })
		:tag("query", { xmlns = "http://jabber.org/protocol/disco#info" })

	module:send_iq(discoRequest):next(
		function(response)
			if response.stanza ~= nil and response.stanza.attr.type == "result" then
				local query = response.stanza:get_child("query", "http://jabber.org/protocol/disco#info")
				if query ~= nil then
					for feature in query:childtags("feature") do
						--module:log("debug", "Disco/info feature for '%s': %s", remoteDomain, feature)
						if feature.attr.var == 'urn:xmpp:serverinfo:0' then
							module:log("debug", "Disco/info response included opt-in for '%s'", remoteDomain)
							opt_in_cache[remoteDomain] = {
								opt_in = true;
								expires = os.time() + cache_ttl;
							}
							return; -- prevent 'false' to be cached, down below.
						end
					end
				end
			end
			module:log("debug", "Disco/info response did not include opt-in for '%s'", remoteDomain)
			opt_in_cache[remoteDomain] = {
				opt_in = false;
				expires = os.time() + cache_ttl;
			}
		end,
		function(response)
			module:log("debug", "An error occurred while performing a disco/info request to determine opt-in for '%s'", remoteDomain, response)
			opt_in_cache[remoteDomain] = {
				opt_in = false;
				expires = os.time() + cache_ttl;
			}
		end
	);

	if ttl and ttl <= 0 then
		-- Cache entry expired, remove it and assume not opted in
		opt_in_cache[remoteDomain] = nil;
		return false;
	end

	return cached_value and cached_value.opt_in;
end
