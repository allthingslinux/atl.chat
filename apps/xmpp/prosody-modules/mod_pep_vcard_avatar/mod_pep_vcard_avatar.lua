-- Prosody IM
-- Copyright (C) 2008-2014 Matthew Wild
-- Copyright (C) 2008-2014 Waqas Hussain
-- Copyright (C) 2014 Kim Alvefur
-- Copyright (c) 2018 Daniel Gultsch
--
-- This project is MIT/X11 licensed. Please see the
-- COPYING file in the source package for more information.
--

local st = require "util.stanza"
local jid = require "util.jid";
local base64 = require"util.encodings".base64;
local sha1 = require"util.hashes".sha1;

local mm = require "core.modulemanager";

-- COMPAT w/trunk
local pep_module_name = "pep";
if mm.get_modules_for_host then
	if mm.get_modules_for_host(module.host):contains("pep_simple") then
		pep_module_name = "pep_simple";
	end
end

local mod_pep = module:depends(pep_module_name);
local pep_data = mod_pep.module.save().data;

if not pep_data then
	module:log("error", "This module is not compatible with your version of mod_pep");
	if mm.get_modules_for_host then
		module:log("error", "Please use mod_pep_simple instead of mod_pep to continue using this module");
	end
	return false;
end

module:hook("account-disco-info", function (event)
	event.reply:tag("feature", { var = "urn:xmpp:pep-vcard-conversion:0" }):up();
end);

module:depends"vcard";
local vcard_storage = module:open_store("vcard");

local function get_vcard(username)
	local vcard, err = vcard_storage:get(username);
	if vcard then
		vcard = st.deserialize(vcard);
	end
	if not vcard then
		vcard = st.stanza("vCard", { xmlns = "vcard-temp" });
	end
	return vcard, err;
end

local function replace_tag(s, replacement)
	local once = false;
	s:maptags(function (tag)
		if tag.name == replacement.name and tag.attr.xmlns == replacement.attr.xmlns then
			if not once then
				once = true;
				return replacement;
			else
				return nil;
			end
		end
		return tag;
	end);
	if not once then
		s:add_child(replacement);
	end
end

local function set_vcard(username, vcard)
	if vcard then
		vcard = st.preserialize(st.clone(vcard));
	end
	return vcard_storage:set(username, vcard);
end

local function publish(session, node, id, item)
	return module:fire_event("pep-publish-item", {
		actor = true, user = jid.bare(session.full_jid), session = session, node = node, id = id, item = item;
	});
end

-- vCard -> PEP
local function update_pep(session, vcard)
	if not vcard then return end
	local nickname = vcard:get_child_text("NICKNAME");
	if nickname then
		publish(session, "http://jabber.org/protocol/nick", "current", st.stanza("item", {id="current"})
			:tag("nick", { xmlns="http://jabber.org/protocol/nick" }):text(nickname));
	end

	local photo = vcard:get_child("PHOTO");
	if photo then
		local photo_type = photo:get_child_text("TYPE");
		local photo_b64 = photo:get_child_text("BINVAL");
		local photo_raw = photo_b64 and base64.decode(photo_b64);
		if photo_raw and photo_type then -- Else invalid data or encoding
			local photo_hash = sha1(photo_raw, true);

			publish(session, "urn:xmpp:avatar:data", photo_hash, st.stanza("item", {id=photo_hash})
				:tag("data", { xmlns="urn:xmpp:avatar:data" }):text(photo_b64));
			publish(session, "urn:xmpp:avatar:metadata", photo_hash, st.stanza("item", {id=photo_hash})
				:tag("metadata", { xmlns="urn:xmpp:avatar:metadata" })
					:tag("info", { id = photo_hash, bytes = tostring(#photo_raw), type = photo_type,}));
		end
	end
end

local function handle_vcard(event)
	local session, stanza = event.origin, event.stanza;
	if not stanza.attr.to and stanza.attr.type == "set" then
		return update_pep(session, stanza:get_child("vCard", "vcard-temp"));
	end
end

module:hook("iq/bare/vcard-temp:vCard", handle_vcard, 1);

-- PEP Avatar -> vCard
local function on_publish_metadata(event)
	local username = event.session.username;
	local metadata = event.item:find("{urn:xmpp:avatar:metadata}metadata/info");
	if not metadata then
		module:log("error", "No info found");
		module:log("debug", event.item:top_tag());
		return;
	end
	module:log("debug", metadata:top_tag());
	local user_data = pep_data[username.."@"..module.host];
	local pep_photo = user_data["urn:xmpp:avatar:data"];
	pep_photo = pep_photo and pep_photo[1] == metadata.attr.id and pep_photo[2];
	if not pep_photo then
		module:log("error", "No photo found");
		return;
	end -- Publishing in the wrong order?
	local vcard = get_vcard(username);
	local new_photo = st.stanza("PHOTO", { xmlns = "vcard-temp" })
		:tag("TYPE"):text(metadata.attr.type):up()
		:tag("BINVAL"):text(pep_photo:get_child_text("data", "urn:xmpp:avatar:data"));

	replace_tag(vcard, new_photo);
	set_vcard(username, vcard);
end

-- PEP Nickname -> vCard
local function on_publish_nick(event)
	local username = event.session.username;
	local vcard = get_vcard(username);
	local new_nick = st.stanza("NICKNAME", { xmlns = "vcard-temp" })
		:text(event.item:get_child_text("nick", "http://jabber.org/protocol/nick"));
	replace_tag(vcard, new_nick);
	set_vcard(username, vcard);
end

local function on_publish(event)
	if event.actor == true then return end -- Not from a client
	local node = event.node;
	if node == "urn:xmpp:avatar:metadata" then
		return on_publish_metadata(event);
	elseif node == "http://jabber.org/protocol/nick" then
		return on_publish_nick(event);
	end
end

module:hook("pep-publish-item", on_publish, 1);

local function calculate_avatar_hash(username)
	local vcard = get_vcard(username)
	local photo = vcard and vcard:get_child("PHOTO")
	if photo then
		local photo_type = photo:get_child_text("TYPE");
		local photo_b64 = photo:get_child_text("BINVAL");
		local photo_raw = photo_b64 and base64.decode(photo_b64);
		if photo_raw and photo_type then
			return sha1(photo_raw, true);
		end
	end
	return ""
end

local function get_avatar_hash(username, host)
	local session = prosody.hosts[host] and prosody.hosts[host].sessions[username]
	if not session then
		return nil
	end
	if not session.avatar_hash then
		session.avatar_hash  = calculate_avatar_hash(username)
	end
	return session.avatar_hash
end

local function on_send_presence(event)
	local stanza, session = event.stanza, event.origin
	if stanza.attr.type then
		return
	end
	local hash = get_avatar_hash(session.username, session.host)
	if hash and hash ~= "" then
		local x_vcard_update = stanza:get_child("x","vcard-temp:x:update")
		if not x_vcard_update then
			x_vcard_update = st.stanza("x",{xmlns="vcard-temp:x:update"})
			stanza:add_child(x_vcard_update)
		end
		local photo = x_vcard_update:get_child("photo")
		if not photo then
			photo = st.stanza("photo")
			photo:text(hash)
			x_vcard_update:add_child(photo)
		end
	end
end

module:hook("pre-presence/full", on_send_presence)
module:hook("pre-presence/bare", on_send_presence)
module:hook("pre-presence/host", on_send_presence)
