local jid_split = require "util.jid".split;
local st = require "util.stanza";
local datamanager = require"util.datamanager";

local xmlns_blocking = "urn:xmpp:blocking";

module:add_feature("urn:xmpp:blocking");

-- Add JID to default privacy list
function add_blocked_jid(username, host, jid)
	local privacy_lists = datamanager.load(username, host, "privacy") or {lists = {}};
	local default_list_name = privacy_lists.default;
	if not privacy_lists.lists then
		privacy_lists.lists = {}
	end
	if not default_list_name then
		default_list_name = "blocklist";
		privacy_lists.default = default_list_name;
	end
	local default_list = privacy_lists.lists[default_list_name];
	if not default_list then
		default_list = { name = default_list_name, items = {} };
		privacy_lists.lists[default_list_name] = default_list;
	end
	local items = default_list.items;
	local order = items[1] and items[1].order or 0; -- Must come first
	for i=1,#items do -- order must be unique
		local item = items[i];
		item.order = item.order + 1;
		if item.type == "jid" and item.action == "deny" and item.value == jid then
			return false;
		end
	end
	table.insert(items, 1, { type = "jid"
		, action = "deny"
		, value = jid
		, message = false
		, ["presence-out"] = false
		, ["presence-in"] = false
		, iq = false
		, order = order
	});
	datamanager.store(username, host, "privacy", privacy_lists);
	return true;
end

-- Remove JID from default privacy list
function remove_blocked_jid(username, host, jid)
	local privacy_lists = datamanager.load(username, host, "privacy") or {};
	local default_list_name = privacy_lists.default;
	if not default_list_name then return; end
	local default_list = privacy_lists.lists[default_list_name];
	if not default_list then return; end
	local items = default_list.items;
	local item, removed = nil, false;
	for i=1,#items do -- order must be unique
		item = items[i];
		if item.type == "jid" and item.action == "deny" and item.value == jid then
			table.remove(items, i);
			removed = true;
			break;
		end
	end
	if removed then
		datamanager.store(username, host, "privacy", privacy_lists);
	end
	return removed;
end

function remove_all_blocked_jids(username, host)
	local privacy_lists = datamanager.load(username, host, "privacy") or {};
	local default_list_name = privacy_lists.default;
	if not default_list_name then return; end
	local default_list = privacy_lists.lists[default_list_name];
	if not default_list then return; end
	local items = default_list.items;
	local item;
	for i=#items,1,-1 do -- order must be unique
		item = items[i];
		if item.type == "jid" and item.action == "deny" then
			table.remove(items, i);
		end
	end
	datamanager.store(username, host, "privacy", privacy_lists);
	return true;
end

function get_blocked_jids(username, host)
	-- Return array of blocked JIDs in default privacy list
	local privacy_lists = datamanager.load(username, host, "privacy") or {};
	local default_list_name = privacy_lists.default;
	if not default_list_name then return {}; end
	local default_list = privacy_lists.lists[default_list_name];
	if not default_list then return {}; end
	local items = default_list.items;
	local item;
	local jid_list = {};
	for i=1,#items do -- order must be unique
		item = items[i];
		if item.type == "jid" and item.action == "deny" then
			jid_list[#jid_list+1] = item.value;
		end
	end
	return jid_list;
end

local function send_push_iqs(username, host, command_type, jids)
	local bare_jid = username.."@"..host;

	local stanza_content = st.stanza(command_type, { xmlns = xmlns_blocking });
	for _, jid in ipairs(jids) do
		stanza_content:tag("item", { jid = jid }):up();
	end

	for resource, session in pairs(prosody.bare_sessions[bare_jid].sessions) do
		local iq_push_stanza = st.iq({ type = "set", to = bare_jid.."/"..resource, id = "blocking-push" });
		iq_push_stanza:add_child(stanza_content);
		session.send(iq_push_stanza);
	end
end

function handle_blocking_command(event)
	local session, stanza = event.origin, event.stanza;

	local username, host = jid_split(stanza.attr.from);
	if stanza.attr.type == "set" then
		if stanza.tags[1].name == "block" then
			local block = stanza.tags[1];
			local block_jid_list = {};
			for item in block:childtags() do
				block_jid_list[#block_jid_list+1] = item.attr.jid;
			end
			if #block_jid_list == 0 then
				session.send(st.error_reply(stanza, "modify", "bad-request"));
			else
				for _, jid in ipairs(block_jid_list) do
					add_blocked_jid(username, host, jid);
				end
				session.send(st.reply(stanza));
				send_push_iqs(username, host, "block", block_jid_list);
			end
			return true;
		elseif stanza.tags[1].name == "unblock" then
			local unblock = stanza.tags[1];
			local unblock_jid_list = {};
			for item in unblock:childtags() do
				unblock_jid_list[#unblock_jid_list+1] = item.attr.jid;
			end
			if #unblock_jid_list == 0 then
				remove_all_blocked_jids(username, host);
			else
				for _, jid_to_unblock in ipairs(unblock_jid_list) do
					remove_blocked_jid(username, host, jid_to_unblock);
				end
			end
			session.send(st.reply(stanza));
			send_push_iqs(username, host, "unblock", unblock_jid_list);
			return true;
		end
	elseif stanza.attr.type == "get" and stanza.tags[1].name == "blocklist" then
		local reply = st.reply(stanza):tag("blocklist", { xmlns = xmlns_blocking });
		local blocked_jids = get_blocked_jids(username, host);
		for _, jid in ipairs(blocked_jids) do
			reply:tag("item", { jid = jid }):up();
		end
		session.send(reply);
		return true;
	end
end

module:hook("iq/self/urn:xmpp:blocking:blocklist", handle_blocking_command);
module:hook("iq/self/urn:xmpp:blocking:block", handle_blocking_command);
module:hook("iq/self/urn:xmpp:blocking:unblock", handle_blocking_command);
