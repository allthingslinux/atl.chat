-- Prosody IM
-- Copyright (C) 2008-2010 Matthew Wild
-- Copyright (C) 2008-2010 Waqas Hussain
-- Copyright (C) 2018 Michel Le Bihan
--
-- This project is MIT/X11 licensed. Please see the
-- COPYING file in the source package for more information.
--
--% conflicts: muc_vcard

local st = require "util.stanza"
local jid_split = require "util.jid".split;
local base64 = require"util.encodings".base64;
local sha1 = require"util.hashes".sha1;

local mod_muc = module:depends"muc";

local vcards = module:open_store();

module:add_feature("vcard-temp");

local get_room_from_jid = rawget(mod_muc, "get_room_from_jid") or
	function (jid)
		local rooms = rawget(mod_muc, "rooms");
		return rooms[jid];
	end

local function get_photo_hash(room)
	local room_node = jid_split(room.jid);
	local vcard = st.deserialize(vcards:get(room_node));
	if vcard then
		local photo = vcard:get_child("PHOTO");

		if photo then
			local photo_b64 = photo:get_child_text("BINVAL");
			local photo_raw = photo_b64 and base64.decode(photo_b64);
			return sha1(photo_raw, true);
		end
	end

end

local function broadcast_presence(room, to)
	local photo_hash = get_photo_hash(room);
	local presence_vcard = st.presence({to = to, from = room.jid})
		:tag("x", { xmlns = "vcard-temp:x:update" })
			:tag("photo"):text(photo_hash):up();

	if to == nil then
		room:broadcast_message(presence_vcard);
	else
		module:send(presence_vcard);
	end
end

local function handle_vcard(event)
	local session, stanza = event.origin, event.stanza;

	local room_jid = stanza.attr.to;
	local room_node = jid_split(room_jid);
	local room = get_room_from_jid(room_jid);
	if not room then
		session.send(st.error_reply(stanza, "cancel", "item-not-found"))
		return true;
	end

	local from = stanza.attr.from;
	local from_affiliation = room:get_affiliation(from);

	if stanza.attr.type == "get" then
		local vCard;
		vCard = st.deserialize(vcards:get(room_node));

		if vCard then
			session.send(st.reply(stanza):add_child(vCard)); -- send vCard!
		else
			session.send(st.error_reply(stanza, "cancel", "item-not-found"));
		end
	else
		if from_affiliation == "owner" or (module.may and module:may("muc:automatic-ownership", from)) then
			if vcards:set(room_node, st.preserialize(stanza.tags[1])) then
				session.send(st.reply(stanza):tag("vCard", { xmlns = "vcard-temp" }));
				broadcast_presence(room, nil)

				room:broadcast_message(st.message({ from = room.jid, type = "groupchat" })
					:tag("x", { xmlns = "http://jabber.org/protocol/muc#user" })
						:tag("status", { code = "104" }));
			else
				-- TODO unable to write file, file may be locked, etc, what's the correct error?
				session.send(st.error_reply(stanza, "wait", "internal-server-error"));
			end
		else
			session.send(st.error_reply(stanza, "auth", "forbidden"));
		end
	end
	return true;
end


module:hook("iq/bare/vcard-temp:vCard", handle_vcard);
module:hook("iq/host/vcard-temp:vCard", handle_vcard);

module:hook("muc-disco#info", function(event)
	event.reply:tag("feature", { var = "vcard-temp" }):up();

	table.insert(event.form, {
			name = "muc#roominfo_avatarhash",
			type = "text-multi",
		});
	event.formdata["muc#roominfo_avatarhash"] = get_photo_hash(event.room);
end);

module:hook("muc-occupant-session-new", function(event)
	broadcast_presence(event.room, event.jid);
end)
