local st = require "util.stanza";
local jid = require "util.jid";
local nodeprep = require "util.encodings".stringprep.nodeprep;

local unprepped_access_lists = module:get_option("muc_access_lists", {});
local access_lists = {};

-- Make sure all input is prepped
for unprepped_room_name, unprepped_list in pairs(unprepped_access_lists) do
	local prepped_room_name = nodeprep(unprepped_room_name);
	if not prepped_room_name then
		module:log("error", "Invalid room name: %s", unprepped_room_name);
	else
		local prepped_list = {};
		for _, unprepped_jid in ipairs(unprepped_list) do
			local prepped_jid = jid.prep(unprepped_jid);
			if not prepped_jid then
				module:log("error", "Invalid JID: %s", unprepped_jid);
			else
				prepped_list[prepped_jid] = true;
			end
		end
		access_lists[prepped_room_name] = prepped_list;
	end
end

local function is_restricted(room, who)
	local allowed = access_lists[room];

	if allowed == nil or allowed[who] or allowed[select(2, jid.split(who))] then
		return nil;
	end

	return "forbidden";
end

module:hook("presence/full", function(event)
	local stanza = event.stanza;

	if stanza.name == "presence" and stanza.attr.type == "unavailable" then   -- Leaving events get discarded
		return;
	end

	-- Get the room
	local room = jid.split(stanza.attr.to);
        if not room then return; end

	-- Get who has tried to join it
	local who = jid.bare(stanza.attr.from)

	-- Checking whether room is restricted
	local check_restricted = is_restricted(room, who)
	if check_restricted ~= nil then
		event.allowed = false;
		event.stanza.attr.type = 'error';
		return event.origin.send(st.error_reply(event.stanza, "cancel", "forbidden", "You're not allowed to enter this room: " .. check_restricted));
	end
end, 10);
