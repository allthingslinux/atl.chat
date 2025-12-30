local jid_bare, jid_split = import("util.jid", "bare", "split");

-- luacheck: ignore 122
local user_sessions = prosody.hosts[module.host].sessions;

module:hook("csi-is-stanza-important", function (event)
	local stanza, session = event.stanza, event.session;
	if stanza.name == "message" then
		if stanza.attr.type == "groupchat" then
			local room_jid = jid_bare(stanza.attr.from);

			local username = session.username;
			local priorities = user_sessions[username].csi_muc_priorities;

			-- Look for mention
			local rooms = session.rooms_joined;
			if rooms then
				local body = stanza:get_child_text("body");
				if not body then return end
				local room_nick = rooms[room_jid];
				if room_nick then
					if body:find(room_nick, 1, true) then
						event.reason = "muc mention";
						return true;
					end
					-- Your own messages
					if stanza.attr.from == (room_jid .. "/" .. room_nick) then
						event.reason = "muc own message";
						return true;
					end
				end
			end

			-- No mentions found, check other logic:
			--			deflaultlow=f or nil	defaultlow=t
			--	in high prio	nil			nil
			--	in low prio	false			false
			--	not in either	nil			false
			--
			--	true	means:	important (always send immediately)
			--	nil	means:	normal (respect other mods for stuff like grace period/reactions/etc)
			--	false	means:	unimportant (delay sending)
			if priorities then
				local priority = priorities[room_jid];
				if priority == false then  -- low priority
					event.reason = "muc priority";
					return false;
				end
				if priorities[false] and priorities[false]["defaultlow"] and not priority then -- defaultlow is false or nil or not high priority
					event.reason = "muc user default low";
					return false;
				end
			end

			-- Standard importance and no mention, leave to other modules to decide for now
			return nil;
		end
	end
end);

module:depends("adhoc");

local dataform = require"util.dataforms";
local adhoc_inital_data = require "util.adhoc".new_initial_data_form;
local instructions = [[
These settings affect battery optimizations performed by the server
while your client has indicated that it is inactive.
]]

local priority_settings_form = dataform.new {
	title = "Prioritize addresses of group chats";
	instructions = instructions;
	{
		type = "hidden";
		name = "FORM_TYPE";
		value = "xmpp:modules.prosody.im/mod_"..module.name;
	};
	{
		type = "jid-multi";
		name = "important";
		label = "Higher priority";
		desc = "Group chats more important to you";
	};
	{
		type = "jid-multi";
		name = "unimportant";
		label = "Lower priority";
		desc = "E.g. large noisy public channels";
	};
	{
		type = "boolean";
		name = "defaultlow";
		label = "Default to lower priority";
		desc = "Mark all channels lower priority as default";
	};
}

local store = module:open_store();
module:hook("resource-bind", function (event)
	local username = event.session.username;
	user_sessions[username].csi_muc_priorities = store:get(username);
end);

local adhoc_command_handler = adhoc_inital_data(priority_settings_form, function (data)
	local username = jid_split(data.from);
	local prioritized_jids = user_sessions[username].csi_muc_priorities or store:get(username);
	local important = {};
	local unimportant = {};
	local defaultlow = false; -- Default to high priority
	if prioritized_jids then
		for jid, priority in pairs(prioritized_jids) do
			if jid then
				if priority then
					table.insert(important, jid);
				else
					table.insert(unimportant, jid);
				end
			end
		end
		table.sort(important);
		table.sort(unimportant);

		if prioritized_jids[false] then
			defaultlow = prioritized_jids[false]["defaultlow"];
		end
	end

	return {
		important = important;
		unimportant = unimportant;
		defaultlow = defaultlow
	};
end, function(fields, form_err, data)
	if form_err then
		return { status = "completed", error = { message = "Problem in submitted form" } };
	end
	local prioritized_jids = {};
	if fields.unimportant then
		for _, jid in ipairs(fields.unimportant) do
			prioritized_jids[jid] = false;
		end
	end
	if fields.important then
		for _, jid in ipairs(fields.important) do
			prioritized_jids[jid] = true;
		end
	end

	local misc_data = {defaultlow = fields.defaultlow};
	prioritized_jids[false] = misc_data;

	local username = jid_split(data.from);
	local ok, err = store:set(username, prioritized_jids);
	if ok then
		user_sessions[username].csi_muc_priorities = prioritized_jids;
		return { status = "completed", info = "Priorities updated" };
	else
		return { status = "completed", error = { message = "Error saving priorities: "..err } };
	end
end);

module:add_item("adhoc", module:require "adhoc".new("Configure group chat priorities",
	"xmpp:modules.prosody.im/mod_"..module.name, adhoc_command_handler, "local_user"));
