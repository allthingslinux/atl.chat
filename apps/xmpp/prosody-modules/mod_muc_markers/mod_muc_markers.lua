-- Track messages received by users of the MUC

-- We rewrite the 'id' attribute of outgoing stanzas to match the stanza (archive) id
-- This module is therefore incompatible with the muc#stable_id feature
-- We rewrite the id because XEP-0333 doesn't tell clients explicitly which id to use
-- in marker reports. However it implies the 'id' attribute through examples, and this
-- is what some clients implement.
-- Notably Conversations will ack the origin-id instead. We need to update the XEP to
-- clarify the correct behaviour.

local set = require "util.set";
local st = require "util.stanza";

local xmlns_markers = "urn:xmpp:chat-markers:0";

local marker_order = { "received", "displayed", "acknowledged" };

-- Add reverse mapping
for priority, name in ipairs(marker_order) do
	marker_order[name] = priority;
end

local marker_element_name = module:get_option_string("muc_marker_type", "displayed");
local marker_summary_on_join = module:get_option_boolean("muc_marker_summary_on_join", true);
local rewrite_id_attribute = module:get_option_boolean("muc_marker_rewrite_id", false);

assert(marker_order[marker_element_name], "invalid marker name: "..marker_element_name);

local marker_element_names = set.new();

-- "displayed" implies "received", etc. so we'll add the
-- chosen marker and any "higher" ones to the set
for i = marker_order[marker_element_name], #marker_order do
	marker_element_names:add(marker_order[i]);
end

local muc_marker_map_store = module:open_store("muc_markers", "map");

local function get_stanza_id(stanza, by_jid)
	for tag in stanza:childtags("stanza-id", "urn:xmpp:sid:0") do
		if tag.attr.by == by_jid then
			return tag.attr.id;
		end
	end
	return nil;
end

module:hook("muc-broadcast-message", function (event)
	local stanza = event.stanza;

	local archive_id = get_stanza_id(stanza, event.room.jid);
	-- We are not interested in stanzas that didn't get archived
	if not archive_id then return; end

	if rewrite_id_attribute then
		-- Add stanza id as id attribute
		stanza.attr.id = archive_id;
	end

	-- Add markable element to request markers from clients
	stanza:tag("markable", { xmlns = xmlns_markers }):up();
end, -1);

module:hook("muc-occupant-groupchat", function (event)
	local marker = event.stanza:child_with_ns(xmlns_markers);
	if not marker or not marker_element_names:contains(marker.name) then
		return; -- No marker, or not one we are interested in
	end

	-- Store the id that the user has received to
	module:log("warn", "New marker for %s in %s: %s", event.occupant.bare_jid, event.room.jid, marker.attr.id);
	muc_marker_map_store:set(event.occupant.bare_jid, event.room.jid, marker.attr.id);

end);

module:hook("muc-message-is-historic", function (event)
	local marker = event.stanza:get_child(nil, xmlns_markers);

	if marker and marker.name ~= "markable" then
		-- Prevent stanza from reaching the archive (it's just noise)
		return false;
	end
end);

local function find_nickname(room, user_jid)
	-- Find their current nickname
	for nick, occupant in pairs(room._occupants) do
		if occupant.bare_jid == user_jid then
			return nick;
		end
	end
	-- Or if they're not here
	local nickname = room:get_affiliation_data(user_jid, "reserved_nickname");
	if nickname then return room.jid.."/"..nickname; end
end

-- Synthesize markers
if muc_marker_map_store.get_all then
module:hook("muc-occupant-session-new", function (event)
	if  not marker_summary_on_join then
		return;
	end
	local room, to = event.room, event.stanza.attr.from;
	local markers = muc_marker_map_store:get_all(room.jid);
	if not markers then return end
	for user_jid, id in pairs(markers) do
		local room_nick = find_nickname(room, user_jid);
		if room_nick then
			local recv_marker = st.message({ type = "groupchat", from = room_nick, to = to })
				:tag(marker_element_name, { xmlns = xmlns_markers, id = id });
			room:route_stanza(recv_marker);
		end
	end
end);
end

-- Public API
--luacheck: ignore 131

function get_user_read_marker(user_jid, room_jid)
	return muc_marker_map_store:get(user_jid, room_jid);
end

function is_markable(stanza)
	return not not stanza:get_child("markable", xmlns_markers);
end
