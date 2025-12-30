-- Relay messages between rooms
-- By Kim Alvefur <zash@zash.se>

local host_session = prosody.hosts[module.host];
local st_msg = require "util.stanza".message;
local jid = require "util.jid";
local now = require "util.datetime".datetime;

local function get_room_from_jid(mod_muc, jid)
	if mod_muc.get_room_from_jid then
		return mod_muc.get_room_from_jid(jid);
	elseif mod_muc.rooms then
		return mod_muc.rooms[jid]; -- COMPAT 0.9, 0.10
	end
end

function check_message(data)
	local origin, stanza = data.origin, data.stanza;
	local mod_muc = host_session.muc;
	if not mod_muc then return; end

	local this_room = get_room_from_jid(mod_muc, stanza.attr.to);
	if not this_room then return; end -- no such room

	local from_room_jid = this_room._jid_nick[stanza.attr.from];
	if not from_room_jid then return; end -- no such nick

	local from_room, from_host, from_nick = jid.split(from_room_jid);

	local body = stanza:get_child("body");
	if not body then return; end -- No body, like topic changes
	body = body and body:get_text(); -- I feel like I want to do `or ""` there :/
	local target_room, message = body:match("^@([^:]+):(.*)");
	if not target_room or not message then return; end

	if target_room == from_room then return; end -- don't route to itself
	module:log("debug", "target room is %s", target_room);

	local bare_room = jid.join(target_room, from_host);
	local dest_room = get_room_from_jid(mod_muc, bare_room);
	if not dest_room then return; end -- TODO send a error
	module:log("info", "message from %s in %s to %s", from_nick, from_room, target_room);

	local sender = jid.join(target_room, module.host, from_room .. "/" .. from_nick);
	local forward_stanza = st_msg({from = sender, to = bare_room, type = "groupchat"}, message);
	forward_stanza:tag("delay", { xmlns = 'urn:xmpp:delay', from = from_room_jid, stamp = now() }):up();

	module:log("debug", "broadcasting message to target room");
	dest_room:broadcast_message(forward_stanza);
end

module:hook("message/bare", check_message);
