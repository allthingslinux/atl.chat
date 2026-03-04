-- mod_pep_open_avatars: Auto-set PEP avatar node access_model to "open"
--
-- By default, PEP nodes use access_model="presence" which blocks anonymous
-- HTTP access. mod_http_pep_avatar requires "open" access to serve avatars.
-- This module hooks avatar publishes and auto-configures the nodes so users
-- don't have to manually change their PEP node settings.
--
-- Two mechanisms:
--   1. Hook future publishes (pep-publish-item) — instant for new avatars
--   2. Hook user session start (resource-bind) — migrate existing nodes
--
-- Affected nodes:
--   urn:xmpp:avatar:metadata  (XEP-0084)
--   urn:xmpp:avatar:data      (XEP-0084)

local mod_pep = module:depends("pep");

local avatar_nodes = {
	"urn:xmpp:avatar:metadata";
	"urn:xmpp:avatar:data";
};

local avatar_nodes_set = {};
for _, node in ipairs(avatar_nodes) do
	avatar_nodes_set[node] = true;
end

--- Fix a single PEP node's access_model to "open" if needed.
local function fix_node_access(service, node, username)
	local ok, node_config = service:get_node_config(node, true);
	if not ok or not node_config then return; end

	if node_config.access_model ~= "open" then
		node_config.access_model = "open";
		local set_ok, err = service:set_node_config(node, true, node_config);
		if set_ok then
			module:log("info", "Migrated %s access_model to 'open' for %s", node, username or "unknown");
		else
			module:log("warn", "Failed to migrate %s access_model to 'open' for %s: %s", node, username or "unknown", tostring(err));
		end
	end
end

-- 1. Hook future publishes: fix access_model immediately on avatar publish
module:hook("pep-publish-item", function(event)
	if not avatar_nodes_set[event.node] then return; end
	if not event.service then return; end
	fix_node_access(event.service, event.node, event.actor);
end, -1); -- Low priority: run after normal PEP processing

-- 2. Hook user login: migrate existing avatar nodes that still have "presence" access
module:hook("resource-bind", function(event)
	local session = event.session;
	if not session or not session.username then return; end

	local username = session.username;
	local pep_service = mod_pep.get_pep_service(username);
	if not pep_service then return; end

	for _, node in ipairs(avatar_nodes) do
		-- Check if the node exists before trying to fix it
		local ok = pep_service:get_node_config(node, true);
		if ok then
			fix_node_access(pep_service, node, username);
		end
	end
end, -1);

module:log("info", "mod_pep_open_avatars loaded — avatar PEP nodes will be auto-set to open access");
