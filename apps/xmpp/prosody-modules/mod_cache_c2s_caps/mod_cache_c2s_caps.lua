local st_iq = require "util.stanza".iq;
local uuid_gen = require "util.uuid".generate;
local calculate_hash = require "util.caps".calculate_hash;

-- Map of jid..node, to avoid querying the same client multiple times for the same value.
local in_flight_iqs = {}

-- Some clients (*ahem* poezio…) don’t include the @node in their result iq.
local iq_node_map = {}

assert(module.send_iq, "This module is not compatible with this version of Prosody.");

local function iq_result_handler(event)
	local origin, stanza = event.origin, event.stanza;

	local query = stanza:get_child("query", "http://jabber.org/protocol/disco#info");
	if not query then
		origin.log("debug", "Wrong iq payload in disco#info result: %s", stanza);
		origin.caps_cache = nil;
		return;
	end

	local from = stanza.attr.from;
	local id = stanza.attr.id;
	local node_string = query.attr.node;
	local node_query = iq_node_map[from..id];
	if node_string == nil then
		node_string = node_query;
		query.attr.node = node_query;
	end
	iq_node_map[from..id] = nil;

	if node_string ~= node_query then
		origin.log("debug", "Wrong node for our disco#info query, expected %s, received %s", node_string, node_query);
		origin.caps_cache = nil;
		return;
	end

	local node, ver = node_query:match("([^#]+)#([^#]+)");
	local hash = calculate_hash(query)
	if ver ~= hash then
		origin.log("debug", "Wrong hash for disco#info: %s ~= %s", ver, hash);
		origin.caps_cache = nil;
		return;
	end

	origin.caps_cache = query;
	origin.log("info", "Stored caps %s", ver);
	module:fire_event("c2s-capabilities-changed", { origin = origin });
	return true;
end

local function iq_error_handler(err)
	local origin = err.context.origin;
	if origin ~= nil then
		origin.caps_cache = nil;
		module:fire_event("c2s-capabilities-changed", { origin = origin });
	end
end

local function presence_stanza_handler(event)
	local origin, stanza = event.origin, event.stanza;

	local from = stanza.attr.from;
	if stanza.attr.to ~= nil then
		return;
	end

	local caps = stanza:get_child("c", "http://jabber.org/protocol/caps");
	if caps == nil then
		origin.log("debug", "Presence from %s without caps received, skipping", from);
		return;
	end

	local hash = caps.attr.hash;
	local node = caps.attr.node;
	local ver = caps.attr.ver;
	if not hash or not node or not ver then
		return;
	end
	if hash ~= "sha-1" then
		origin.log("warn", "Presence from %s with non-SHA-1 caps : %s", from, hash);
		return;
	end

	local node_query = node.."#"..ver;
	if (origin.caps_cache and origin.caps_cache.attr.node == node_query) or in_flight_iqs[from..node_query] ~= nil then
		origin.log("debug", "Already requested these caps, skipping");
		return;
	end

	origin.log("debug", "Presence from %s with SHA-1 caps %s, querying disco#info", from, node_query);

	local id = uuid_gen();
	iq_node_map[from..id] = node_query
	local iq = st_iq({ type = "get", from = module.host, to = from, id = id })
		:tag("query", { xmlns = "http://jabber.org/protocol/disco#info", node = node_query });
	in_flight_iqs[from..node_query] = true;
	module:send_iq(iq, origin)
		:next(iq_result_handler, iq_error_handler)
		:finally(function () in_flight_iqs[from..node_query] = nil; end)
end

-- Handle only non-directed presences for now.
module:hook("pre-presence/bare", presence_stanza_handler);
