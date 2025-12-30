local jid_split = require "util.jid".split;

local st = require "util.stanza";

local mod_groups = module:depends("groups_internal")
local mod_pep = module:depends("pep")

local XMLNS_BM2 = "urn:xmpp:bookmarks:1";
local XMLNS_XEP0060 = "http://jabber.org/protocol/pubsub";

local default_options = {
	["persist_items"] = true;
	["max_items"] = "max";
	["send_last_published_item"] = "never";
	["access_model"] = "whitelist";
};

local function get_current_bookmarks(jid, service)
	local ok, items = service:get_items(XMLNS_BM2, jid)
	if not ok then
		if items == "item-not-found" then
			return {}, nil;
		else
			return nil, items;
		end
	end
	return items or {};
end

local function update_bookmark(jid, service, room, bookmark)
	local ok, err = service:publish(XMLNS_BM2, jid, room, bookmark, default_options);
	if ok then
		module:log("debug", "found existing matching bookmark, updated")
	else
		module:log("error", "failed to update bookmarks: %s", err)
	end
end

local function find_matching_bookmark(storage, room)
	return storage[room];
end

local function inject_bookmark(jid, room, autojoin, name)
	module:log("debug", "Injecting bookmark for %s into %s", room, jid);
	local pep_service = mod_pep.get_pep_service(jid_split(jid))

	local current, err = get_current_bookmarks(jid, pep_service);
	if err then
		module:log("error", "Could not retrieve existing bookmarks for %s: %s", jid, err);
		return;
	end
	local found = find_matching_bookmark(current, room)
	if found then
		local existing = found:get_child("conference", XMLNS_BM2);
		if autojoin ~= nil then
			existing.attr.autojoin = autojoin and "true" or "false"
		end
		if name ~= nil then
			-- do not change already configured names
			if not existing.attr.name then
				existing.attr.name = name
			end
		end
	else
		module:log("debug", "no existing bookmark found, adding new")
		found = st.stanza("item", { xmlns = XMLNS_XEP0060; id = room })
			:tag("conference", { xmlns = XMLNS_BM2; name = name; autojoin = autojoin and "true" or "false"; })
	end

	update_bookmark(jid, pep_service, room, found)
end

local function remove_bookmark(jid, room)
	local pep_service = mod_pep.get_pep_service(jid_split(jid))

	return pep_service:retract(XMLNS_BM2, jid, room, st.stanza("retract", { id = room }));
end

local function handle_user_added(event)
	local group_info = event.group_info;

	local jid = event.user .. "@" .. event.host

	if group_info.muc_jid then
		inject_bookmark(jid, group_info.muc_jid, true, group_info.name);
	elseif group_info.mucs then
		for _, chat in ipairs(mod_groups.get_group_chats(event.id)) do
			if not chat.deleted then
				inject_bookmark(jid, chat.jid, true, chat.name);
			end
		end
	else
		module:log("debug", "ignoring user added event on group %s because it has no MUCs", event.id)
	end
end

local function handle_user_removed(event)
	-- Removing the bookmark is fine as the user just lost any privilege to
	-- be in the MUC (as group MUCs are members-only).
	local group_info = event.group_info;
	local jid = event.user .. "@" .. event.host

	if group_info.muc_jid then
		remove_bookmark(jid, event.group_info.muc_jid);
	elseif group_info.mucs then
		for _, muc_jid in ipairs(group_info.mucs) do
			remove_bookmark(jid, muc_jid);
		end
	else
		module:log("debug", "ignoring user removed event on group %s because it has no MUC", event.id)
	end
end

module:hook("group-user-added", handle_user_added)
module:hook("group-user-removed", handle_user_removed)


local function handle_muc_added(event)
	-- Add MUC to all members' bookmarks
	module:log("info", "Adding new group chat to all member bookmarks...");
	local muc_jid, muc_name = event.muc.jid, event.muc.name;
	for member_username in pairs(mod_groups.get_members(event.group_id)) do
		local member_jid = member_username .. "@" .. module.host;
		inject_bookmark(member_jid, muc_jid, true, muc_name);
	end
end

local function handle_muc_removed(event)
	-- Remove MUC from all members' bookmarks
	local muc_jid = event.muc.jid;
	for member_username in ipairs(mod_groups.get_members(event.group_id)) do
		local member_jid = member_username .. "@" .. module.host;
		remove_bookmark(member_jid, muc_jid);
	end
end

module:hook("group-chat-added", handle_muc_added)
module:hook("group-chat-removed", handle_muc_removed)
