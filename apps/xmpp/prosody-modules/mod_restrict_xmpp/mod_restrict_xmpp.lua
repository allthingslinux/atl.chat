local array = require "util.array";
local it = require "util.iterators";
local set = require "util.set";
local st = require "util.stanza";

local normal_user_role = "prosody:registered";
local limited_user_role = "prosody:guest";

local features = require "core.features";

-- COMPAT
if not features.available:contains("split-user-roles") then
	normal_user_role = "prosody:user";
	limited_user_role = "prosody:restricted";
end

module:default_permission(normal_user_role, "xmpp:federate");
module:hook("route/remote", function (event)
	if not module:may("xmpp:federate", event) then
		if event.stanza.attr.type ~= "result" and event.stanza.attr.type ~= "error" then
			module:log("warn", "Access denied: xmpp:federate for %s -> %s", event.stanza.attr.from, event.stanza.attr.to);
			local reply = st.error_reply(event.stanza, "auth", "forbidden");
			event.origin.send(reply);
		end
		return true;
	end
end);

local iq_namespaces = {
	["jabber:iq:roster"] = "contacts";
	["jabber:iq:private"] = "storage";

	["vcard-temp"] = "profile";
	["urn:xmpp:mam:0"] = "history";
	["urn:xmpp:mam:1"] = "history";
	["urn:xmpp:mam:2"] = "history";

	["urn:xmpp:carbons:0"] = "carbons";
	["urn:xmpp:carbons:1"] = "carbons";
	["urn:xmpp:carbons:2"] = "carbons";

	["urn:xmpp:blocking"] = "blocklist";

	["http://jabber.org/protocol/pubsub"] = "pep";
	["http://jabber.org/protocol/disco#info"] = "disco";
};

local legacy_storage_nodes = {
	["storage:bookmarks"] = "bookmarks";
	["storage:rosternotes"] = "contacts";
	["roster:delimiter"] = "contacts";
	["storage:metacontacts"] = "contacts";
};

local pep_nodes = {
	["storage:bookmarks"] = "bookmarks";
	["urn:xmpp:bookmarks:1"] = "bookmarks";

	["urn:xmpp:vcard4"] = "profile";
	["urn:xmpp:avatar:data"] = "profile";
	["urn:xmpp:avatar:metadata"] = "profile";
	["http://jabber.org/protocol/nick"] = "profile";

	["eu.siacs.conversations.axolotl.devicelist"] = "omemo";
	["urn:xmpp:omemo:1:devices"] = "omemo";
	["urn:xmpp:omemo:1:bundles"] = "omemo";
	["urn:xmpp:omemo:2:devices"] = "omemo";
	["urn:xmpp:omemo:2:bundles"] = "omemo";
};

module:hook("pre-iq/bare", function (event)
	if not event.to_self then return; end
	local origin, stanza = event.origin, event.stanza;

	local typ = stanza.attr.type;
	if typ ~= "set" and typ ~= "get" then return; end
	local action = typ == "get" and "read" or "write";

	local payload = stanza.tags[1];
	local ns = payload and payload.attr.xmlns;
	if ns == "urn:xmpp:ping" then return end
	local proto = iq_namespaces[ns];
	if proto == "pep" then
		local pubsub = payload:get_child("pubsub", "http://jabber.org/protocol/pubsub");
		local node = pubsub and #pubsub.tags == 1 and pubsub.tags[1].attr.node or nil;
		proto = pep_nodes[node] or "pep";
		if proto == "pep" and node and node:match("^eu%.siacs%.conversations%.axolotl%.bundles%.%d+$") then
			proto = "omemo"; -- COMPAT w/ original OMEMO
		end
	elseif proto == "storage" then
		local data = payload.tags[1];
		proto = data and legacy_storage_nodes[data.attr.xmlns] or "legacy-storage";
	elseif proto == "carbons" then
		-- This allows access to live messages
		proto, action = "messages", "read";
	elseif proto == "history" then
		action = "read";
	end
	local permission_name = "xmpp:account:"..(proto and (proto..":") or "")..action;
	if not module:may(permission_name, event) then
		module:log("warn", "Access denied: %s ({%s}%s) for %s", permission_name, ns, payload.name, origin.full_jid or origin.id);
		origin.send(st.error_reply(stanza, "auth", "forbidden", "You do not have permission to make this request ("..permission_name..")"));
		return true;
	end
end);

--module:default_permission("prosody:restricted", "xmpp:account:read");
--module:default_permission("prosody:restricted", "xmpp:account:write");
module:default_permission(limited_user_role, "xmpp:account:messages:read");
module:default_permission(limited_user_role, "xmpp:account:messages:write");
for _, property_list in ipairs({ iq_namespaces, legacy_storage_nodes, pep_nodes }) do
	for account_property in set.new(array.collect(it.values(property_list))) do
		module:default_permission(limited_user_role, "xmpp:account:"..account_property..":read");
		module:default_permission(limited_user_role, "xmpp:account:"..account_property..":write");
	end
end

module:default_permission(limited_user_role, "xmpp:account:presence:write");
module:hook("pre-presence/bare", function (event)
	if not event.to_self then return; end
	local stanza = event.stanza;
	if not module:may("xmpp:account:presence:write", event) then
		module:log("warn", "Access denied: xmpp:account:presence:write for %s", event.origin.full_jid or event.origin.id);
		event.origin.send(st.error_reply(stanza, "auth", "forbidden", "You do not have permission to send account presence"));
		return true;
	end
	local priority = stanza:get_child_text("priority");
	if priority ~= "-1" then
		if not module:may("xmpp:account:messages:read", event) then
			module:log("warn", "Access denied: xmpp:account:messages:read for %s", event.origin.full_jid or event.origin.id);
			event.origin.send(st.error_reply(stanza, "auth", "forbidden", "You do not have permission to receive messages (use presence priority -1)"));
			return true;
		end
	end
end);
