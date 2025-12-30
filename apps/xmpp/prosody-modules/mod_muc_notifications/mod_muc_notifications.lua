-- mod_muc_notifications
--
-- Copyright (C) 2019 Marcos de Vera Piquero <marcos.devera@quobis.com>
--
-- This file is MIT/X11 licensed.
--
-- A module to notify non-present members of messages in a group chat
--

local id = require"util.id"
local st = require"util.stanza"

local use_invite = module:get_option_boolean("muc_notification_invite", false)

-- Given a stanza, compute if it qualifies as important (notifiable)
-- return true for message stanzas with non-empty body
-- Should probably use something similar to muc-message-is-historic event
local function is_important(stanza)
	local body = stanza:find("body#")
	return body and #body
end

local function handle_muc_message(event)
	-- event.room and event.stanza are available
	local room = event.room
	local stanza = event.stanza
	for jid, aff in pairs(room._affiliations) do
		if aff ~= "outcast" then
			local is_occupant = false
			for _, occupant in pairs(room._occupants) do
				if occupant.bare_jid == jid then
					is_occupant = true
					break
				end
			end
			if not is_occupant and is_important(stanza) then
				-- send notification to jid
				local attrs = {
					to = jid,
					id = id.short(),
					from = room.jid,
				}
				local not_attrs = {
					xmlns = "http://quobis.com/xmpp/muc#push",
					jid = room.jid,
				}
				local reason = "You have messages in group chat "..(room:get_name() or room.jid)
				local notification = st.message(attrs)
					:body(reason):up()
					:tag("notification", not_attrs):up()
					:tag("no-store", {xmlns = "urn:xmpp:hints"})
				local invite = st.message(attrs):tag("x", {xmlns = "http://jabber.org/protocol/muc#user"})
					:tag("invite", {from = stanza.attr.from})
					:tag("reason"):text(reason):up():up():up()
					:tag("notification", not_attrs):up()
					:tag("no-store", {xmlns = "urn:xmpp:hints"})
				module:log("debug", "notifying with %s", tostring(use_invite and invite or notification))
				module:send(use_invite and invite or notification)
				module:log("debug", "sent notification of MUC message %s", use_invite and invite or notification)
			end
		end
	end
end

module:hook("muc-broadcast-message", handle_muc_message)

module:log("debug", "Module loaded")
