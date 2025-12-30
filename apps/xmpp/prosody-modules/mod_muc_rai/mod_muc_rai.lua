local cache = require "util.cache";
local jid = require "util.jid";
local st = require "util.stanza";

local max_subscribers = module:get_option_number("muc_rai_max_subscribers", 1024);

local muc_affiliation_store = module:open_store("config", "map");
local muc_archive = module:open_store("muc_log", "archive");

local xmlns_rai = "urn:xmpp:rai:0";

local muc_markers = module:depends("muc_markers");

-- subscriber_jid -> { [room_jid] = interested }
local subscribed_users = cache.new(max_subscribers, false);
-- room_jid -> { [user_jid] = interested }
local interested_users = {};
-- room_jid -> last_id
local room_activity_cache = cache.new(1024);

-- Send a single notification for a room, updating data structures as needed
local function send_single_notification(user_jid, room_jid)
	local notification = st.message({ to = user_jid, from = module.host })
		:tag("rai", { xmlns = xmlns_rai })
			:text_tag("activity", room_jid)
		:up();
	local interested_room_users = interested_users[room_jid];
	if interested_room_users then
		interested_room_users[user_jid] = nil;
	end
	local interested_rooms = subscribed_users:get(user_jid);
	if interested_rooms then
		interested_rooms[room_jid] = nil;
	end
	module:log("debug", "Sending notification from %s to %s", room_jid, user_jid);
	return module:send(notification);
end

local function subscribe_room(user_jid, room_jid)
	local interested_rooms = subscribed_users:get(user_jid);
	if not interested_rooms then
		return nil, "not-subscribed";
	end
	module:log("debug", "Subscribed %s to %s", user_jid, room_jid);
	interested_rooms[room_jid] = true;

	local interested_room_users = interested_users[room_jid];
	if not interested_room_users then
		interested_room_users = {};
		interested_users[room_jid] = interested_room_users;
	end
	interested_room_users[user_jid] = true;
	return true;
end

local function unsubscribe_room(user_jid, room_jid)
	local interested_rooms = subscribed_users:get(user_jid);
	if not interested_rooms then
		return nil, "not-subscribed";
	end
	interested_rooms[room_jid] = nil;

	local interested_room_users = interested_users[room_jid];
	if not interested_room_users then
		return true;
	end
	interested_room_users[user_jid] = nil;
	return true;
end

local function notify_interested_users(room_jid)
	module:log("warn", "NOTIFYING FOR %s", room_jid)
	local interested_room_users = interested_users[room_jid];
	if not interested_room_users then
		module:log("debug", "Nobody interested in %s", room_jid);
		return;
	end
	for user_jid in pairs(interested_room_users) do
		send_single_notification(user_jid, room_jid);
	end
	return true;
end

local function unsubscribe_user_from_all_rooms(user_jid)
	local interested_rooms = subscribed_users:get(user_jid);
	if not interested_rooms then
		return nil, "not-subscribed";
	end
	for room_jid in pairs(interested_rooms) do
		unsubscribe_room(user_jid, room_jid);
	end
	return true;
end

local function get_last_room_message_id(room_jid)
	local last_room_message_id = room_activity_cache:get(room_jid);
	if last_room_message_id then
		module:log("debug", "Last room message: %s (cached)", last_room_message_id);
		return last_room_message_id;
	end

	-- Load all the data!
	local query = {
		limit = 1;
		reverse = true;
		with = "message<groupchat";
	}
	local data, err = muc_archive:find(jid.node(room_jid), query);

	if not data then
		module:log("error", "Could not fetch history: %s", err);
		return nil;
	end

	local id = data();
	room_activity_cache:set(room_jid, id);
	module:log("debug", "Last room message: %s (queried)", id);
	return id;
end

local function update_room_activity(room_jid, last_id)
	room_activity_cache:set(room_jid, last_id);
end

local function get_last_user_read_id(user_jid, room_jid)
	return muc_markers.get_user_read_marker(jid.bare(user_jid), room_jid);
end

local function has_new_activity(room_jid, user_jid)
	local last_room_message_id = get_last_room_message_id(room_jid);
	local last_user_read_id = get_last_user_read_id(user_jid, room_jid);
	module:log("debug", "Checking activity in <%s> (%s) for <%s> (%s): %s",
		room_jid, last_room_message_id,
		user_jid, last_user_read_id,
		tostring(last_room_message_id ~= last_user_read_id)
	);
	return last_room_message_id ~= last_user_read_id;
end

-- Returns a set of rooms that a user is interested in
local function get_interested_rooms(user_jid)
	-- Use affiliation as an indication of interest, return
	-- all rooms a user is affiliated
	return muc_affiliation_store:get_all(jid.bare(user_jid));
end

local function is_subscribed(user_jid)
	return not not subscribed_users:get(user_jid);
end

-- Subscribes to all rooms that the user has an interest in
-- Returns a set of room JIDs that have already had activity (thus no subscription)
local function subscribe_all_rooms(user_jid)
	if is_subscribed(user_jid) then
		return nil;
	end

	-- Send activity notifications for all relevant rooms
	local interested_rooms, err = get_interested_rooms(user_jid);

	if not interested_rooms then
		if err then
			return nil, "internal-server-error";
		end
		interested_rooms = {};
	end

	if not subscribed_users:set(user_jid, {}) then
		module:log("warn", "Subscriber limit (%d) reached, rejecting subscription from %s", max_subscribers, user_jid);
		return nil, "resource-constraint";
	end

	local rooms_with_activity;
	for room_name in pairs(interested_rooms) do
		local room_jid = room_name.."@"..module.host;
		if has_new_activity(room_jid, user_jid) then
			-- There has already been activity, include this room
			-- in the response
			if not rooms_with_activity then
				rooms_with_activity = {};
			end
			rooms_with_activity[room_jid] = true;
		else
			-- Subscribe to any future activity
			subscribe_room(user_jid, room_jid);
		end
	end
	return rooms_with_activity;
end

module:hook("muc-occupant-pre-join", function(event)
	local room_jid, user_jid = event.room.jid, event.stanza.attr.from;
	local ok, _ = unsubscribe_room(user_jid, room_jid);
	if ok then
		module:log("debug", "Unsubscribed %s to %s Reason: muc-occupant-joined", user_jid, room_jid)
	end
end, -500);

module:hook("muc-occupant-pre-leave", function(event)
	local room_jid, user_jid = event.room.jid, event.stanza.attr.from;
	local ok, _ = subscribe_room(user_jid, room_jid);
	if ok then
		module:log("debug", "Subscribed %s to %s Reason: muc-occupant-left", user_jid, room_jid)
	end
end, -500);

module:hook("presence/host", function (event)
	local origin, stanza = event.origin, event.stanza;
	local user_jid = stanza.attr.from;

	if stanza.attr.type == "unavailable" then -- User going offline
		unsubscribe_user_from_all_rooms(user_jid);
		return true;
	end

	if not stanza:get_child("rai", xmlns_rai) then
		return; -- Ignore, no <rai/> tag
	end

	local rooms_with_activity, err = subscribe_all_rooms(user_jid);

	if not rooms_with_activity then
		if not err then
			module:log("debug", "No activity to notify");
			return true;
		else
			return origin.send(st.error_reply(stanza, "wait", "resource-constraint"));
		end
	end

	local reply = st.message({ to = stanza.attr.from, from = module.host })
		:tag("rai", { xmlns = xmlns_rai });
	for room_jid in pairs(rooms_with_activity) do
		reply:text_tag("activity", room_jid);
	end
	return origin.send(reply);
end);

module:hook("muc-broadcast-message", function (event)
	local room, stanza = event.room, event.stanza;
	local archive_id = stanza:get_child("stanza-id", "urn:xmpp:sid:0");
	if archive_id and archive_id.attr.id then
		-- Remember the id of the last message so we can compare it
		-- to the per-user marker (managed by mod_muc_markers)
		update_room_activity(room.jid, archive_id.attr.id);
		-- Notify any users that need to be notified
		notify_interested_users(room.jid);
	end
end, -1);
