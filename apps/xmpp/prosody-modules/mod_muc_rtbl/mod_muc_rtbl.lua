local jid = require "util.jid";
local sha256 = require "util.hashes".sha256;
local st = require "util.stanza";

local url = require "socket.url";

-- Legacy config (single list only)
local rtbl_service_jid = module:get_option_string("muc_rtbl_jid");
local rtbl_node = module:get_option_string("muc_rtbl_node", "muc_bans_sha256");

-- Multi-list config
local rtbl_config = module:get_option_array("muc_rtbls", {
	rtbl_service_jid and rtbl_node and ("xmpp:"..rtbl_service_jid.."?;node="..rtbl_node) or nil;
});

if #rtbl_config == 0 then
	return error("No RTBLs configured");
end

local mod_rtbl = module:depends("rtbl");

local lists = {};

local function parse_xmpp_uri(uri)
	local parsed = url.parse(uri);
	if parsed.scheme and parsed.scheme ~= "xmpp" then
		return nil, "unexpected-scheme";
	end

	local parsed_query = {};
	for kv in (parsed.query or ""):gmatch("[^?;]+") do
		local k, v = kv:match("^([^=]+)=?(.*)$");
		parsed_query[k] = v;
	end

	return {
		jid = jid.prep(parsed.path);
		params = parsed_query;
	};
end

for _, rtbl_uri in ipairs(rtbl_config) do
	local uri = parse_xmpp_uri(rtbl_uri);
	module:log("debug", "Subscribing to %q node %q", uri.jid, uri.params.node);
	local rtbl = mod_rtbl.new_rtbl_subscription(uri.jid, uri.params.node or "muc_bans_sha256", {});
	table.insert(lists, rtbl);
end

local function update_occupant_hashes(occupant)
	local bare_hash, host_hash;
	if not occupant.mod_muc_rtbl_bare_hash then
		bare_hash = sha256(jid.bare(occupant.bare_jid), true);
		occupant.mod_muc_rtbl_bare_hash = bare_hash;
	else
		bare_hash = occupant.mod_muc_rtbl_bare_hash;
	end
	if not occupant.mod_muc_rtbl_host_hash then
		host_hash = sha256(jid.host(occupant.bare_jid), true);
		occupant.mod_muc_rtbl_host_hash = host_hash;
	else
		host_hash = occupant.mod_muc_rtbl_host_hash;
	end
	return bare_hash, host_hash;
end

local function is_banned_occupant(occupant)
	local bare_hash, host_hash = update_occupant_hashes(occupant);
	for _, list in ipairs(lists) do
		local items = list.items;
		if items[bare_hash] or items[host_hash] then
			return true;
		end
	end
end

module:hook("muc-occupant-pre-join", function (event)
	local from_bare = jid.bare(event.stanza.attr.from);

	local affiliation = event.room:get_affiliation(from_bare);
	if affiliation and affiliation ~= "none" then
		-- Skip check for affiliated users
		return;
	end

	if is_banned_occupant(event.occupant) then
		module:log("info", "Blocked user <%s> from room <%s> due to RTBL match", from_bare, event.stanza.attr.to);
		local error_reply = st.error_reply(event.stanza, "cancel", "forbidden", "You are banned from this service", event.room.jid);
		event.origin.send(error_reply);
		return true;
	end
end);

module:hook("muc-occupant-groupchat", function(event)
	local occupant = event.occupant;
	local affiliation = event.room:get_affiliation(occupant.bare_jid);
	if affiliation and affiliation ~= "none" then
		-- Skip check for affiliated users
		return;
	end

	if is_banned_occupant(occupant) then
		module:log("debug", "Blocked message from user <%s> to room <%s> due to RTBL match", event.stanza.attr.from, event.stanza.attr.to);
		local error_reply = st.error_reply(event.stanza, "cancel", "forbidden", "You are banned from this service", event.room.jid);
		event.origin.send(error_reply);
		return true;
	end
end);

module:hook("muc-private-message", function(event)
	local occupant = event.room:get_occupant_by_nick(event.stanza.attr.from);
	local affiliation = event.room:get_affiliation(occupant.bare_jid);
	if affiliation and affiliation ~= "none" then
		-- Skip check for affiliated users
		return;
	end

	if is_banned_occupant(occupant) then
		module:log("debug", "Blocked private message from user <%s> from room <%s> due to RTBL match", occupant.bare_jid, event.stanza.attr.to);
		local error_reply = st.error_reply(event.stanza, "cancel", "forbidden", "You are banned from this service", event.room.jid);
		event.origin.send(error_reply);
		return false; -- Don't route it
	end
end);

module.environment.lists = lists
