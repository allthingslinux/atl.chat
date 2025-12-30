-- mod_minimix
--
-- Rewrite MUC stanzas suich that the account / bare JID joins rooms instead of clients / full JIDs
--
local jid_split, jid_join, jid_node, jid_bare = import("util.jid", "split", "join", "node", "bare");
local st = require "util.stanza";
local mt = require "util.multitable";

local users = prosody.hosts[module.host].sessions;

local data = mt.new();

-- FIXME You can join but you can never leave.

module:hook("pre-presence/full", function (event)
	local origin, stanza = event.origin, event.stanza;

	local room_node, room_host, nickname = jid_split(stanza.attr.to);
	local room_jid = jid_join(room_node, room_host);
	local username = origin.username;

	if stanza.attr.type == nil and stanza:get_child("x", "http://jabber.org/protocol/muc") then
		module:log("debug", "Joining %s as %s", room_jid, nickname);

		-- TODO Should this be kept track of before the *initial* join has been confirmed or?
		if origin.joined_rooms then
			origin.joined_rooms[room_jid] = nickname;
		else
			origin.joined_rooms = { [room_jid] = nickname };
		end

		if data:get(username, room_jid, "subject") then
			module:log("debug", "Already joined to %s as %s", room_jid, nickname);
			local presences = data:get(username, room_jid, "presence");
			if presences then
				-- Joined but no presence? Weird
				for _, pres in pairs(presences) do
					pres = st.clone(pres);
					pres.attr.to = origin.full_jid;
					origin.send(pres);
				end
			end
			-- FIXME should send ones own presence last
			local subject = data:get(username, room_jid, "subject");
			if subject then
				origin.send(st.clone(subject));
			end
			-- Send on-join stanzas from local state, somehow
			-- Maybe tell them their nickname was changed if it doesn't match the account one
			return true;
		end

		local account_join = st.clone(stanza);
		account_join.attr.from = jid_join(origin.username, origin.host);
		module:send(account_join);

		data:set(username, room_jid, "joined", nickname);

		return true;
	elseif stanza.attr.type == "unavailable" then
		if origin.joined_rooms and origin.joined_rooms[room_jid] then
			origin.joined_rooms[room_jid] = nil;
		end
		origin.send(st.reply(stanza));
		return true;
	elseif stanza.attr.type == nil and origin.joined_rooms and origin.joined_rooms[room_jid] then
		return true; -- Suppress these
	end
end);

module:hook("pre-message/bare", function (event)
	local origin, stanza = event.origin, event.stanza;
	local username = origin.username;
	local room_jid = jid_bare(stanza.attr.to);

	module:log("info", "%s", stanza)
	if origin.joined_rooms and origin.joined_rooms[room_jid] then
		local from_account = st.clone(stanza);
		from_account.attr.from = jid_join(username, origin.host);
		module:log("debug", "Sending:\n%s\nInstead of:\n%s", from_account, stanza);
		module:send(from_account, origin);
		return true;
	end
end);

local function handle_to_bare_jid(event)
	local stanza = event.stanza;
	local username = jid_node(stanza.attr.to);
	local room_jid = jid_bare(stanza.attr.from);

	if data:get(username, room_jid) then
		module:log("debug", "handle_to_bare_jid %q, %s", room_jid, stanza);
		-- Broadcast to clients

		if stanza.name == "message" and stanza.attr.type == "groupchat"
			and not stanza:get_child("body") and stanza:get_child("subject") then
			data:set(username, room_jid, "subject", st.clone(stanza));
		elseif stanza.name == "presence" then
			if stanza.attr.type == nil then
				data:set(username, room_jid, "presence", stanza.attr.from, st.clone(stanza));
			elseif stanza.attr.type == "unavailable" then
				data:set(username, room_jid, "presence", stanza.attr.from, nil);
			end
		end

		if users[username] then
			module:log("debug", "%s has sessions", username);
			for _, session in pairs(users[username].sessions) do
				module:log("debug", "Session: %s", jid_join(session.username, session.host, session.resource));
				if session.joined_rooms and session.joined_rooms[room_jid] then
					module:log("debug", "Is joined");
					local s = st.clone(stanza);
					s.attr.to = session.full_jid;
					session.send(s);
				else
					module:log("debug", "session.joined_rooms = %s", session.joined_rooms);
				end
			end
		end

		return true;
	end
end

module:hook("presence/bare", handle_to_bare_jid);
module:hook("message/bare", handle_to_bare_jid);
