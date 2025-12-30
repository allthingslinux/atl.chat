local jid = require "util.jid";
local st = require "util.stanza";
local datetime = require "util.datetime";
local jid_resource = require "util.jid".resource;

local notify_unaffiliated_users = module:get_option("muc_mmn_notify_unaffiliated_users", false)

local muc_affiliation_store = module:open_store("config", "map");

local mmn_xmlns = "urn:xmpp:mmn:0";
local reference_xmlns = "urn:xmpp:reference:0";
local forwarded_xmlns = "urn:xmpp:forward:0";
local deplay_xmlns = "urn:xmpp:delay";


-- Returns a set of rooms the user is affiliated to
local function get_user_rooms(user_bare_jid)
	return muc_affiliation_store:get_all(user_bare_jid);
end

local function is_eligible(user_bare_jid, room)
	if notify_unaffiliated_users then return true; end

	local user_rooms, err = get_user_rooms(user_bare_jid);
	if not user_rooms then
		if err then
			return false, err;
		end
		return false;
	end

	local room_node = jid.node(room.jid)
	if user_rooms[room_node] then
		return true;
	end

	return false
end

-- Send a single notification for a room, updating data structures as needed
local function send_single_notification(user_bare_jid, room_jid, mention_stanza)
	local notification = st.message({ to = user_bare_jid, from = room_jid })
		:tag("mentions", { xmlns = mmn_xmlns })
		:tag("forwarded", {xmlns = forwarded_xmlns})
		:tag("delay", {xmlns = deplay_xmlns, stamp = datetime.datetime()}):up()
		:add_child(mention_stanza)
		:reset();
	module:log("debug", "Sending mention notification from %s to %s", room_jid, user_bare_jid);
	return module:send(notification);
end

local function notify_mentioned_users(room, client_mentions, mention_stanza)
	module:log("debug", "NOTIFYING FOR %s", room.jid)
	for mentioned_jid in pairs(client_mentions) do
		local user_bare_jid = mentioned_jid;
		if (string.match(mentioned_jid, room.jid)) then
			local nick = jid_resource(mentioned_jid);
			user_bare_jid = room:get_registered_jid(nick);
		end
		if is_eligible(user_bare_jid, room) then
			send_single_notification(user_bare_jid, room.jid, mention_stanza);
		end
	end
end

local function get_mentions(stanza)
	local has_mentions = false
	local client_mentions = {}

	for element in stanza:childtags("reference", reference_xmlns) do
		if element.attr.type == "mention" then
			local user_bare_jid = element.attr.uri:match("^xmpp:(.+)$");
			if user_bare_jid then
				client_mentions[user_bare_jid] = user_bare_jid;
				has_mentions = true
			end
		end
	end

	return has_mentions, client_mentions
end

module:hook("muc-broadcast-message", function (event)
	local room, stanza = event.room, event.stanza;
	local body = stanza:get_child_text("body")
	if not body or #body < 1 then return; end
	local correction = stanza:get_child("replace", "urn:xmpp:message-correct:0");
	if correction then return; end -- Do not notify on message corrections

	local has_mentions, client_mentions = get_mentions(stanza)
	if not has_mentions then return; end

	-- Notify any users that need to be notified
	notify_mentioned_users(room, client_mentions, stanza);
end, -1);
