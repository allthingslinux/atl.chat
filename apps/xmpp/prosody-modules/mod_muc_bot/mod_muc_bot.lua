local st = require "util.stanza";
local jid = require "util.jid";

local bots = module:get_option_set("known_bots", {});

module:hook("muc-occupant-groupchat", function(event)
	if event.occupant then return end -- skip messages from actual occupants
	local room = event.room;

	if bots:contains(jid.bare(event.from)) or bots:contains(jid.host(event.from)) then

		local nick = room:get_registered_nick(jid);

		if not nick then
			-- Allow bot to specify its own nick, but we're appending '[bot]' to it.
			-- FIXME HATS!!!
			nick = event.stanza:get_child_text("nick", "http://jabber.org/protocol/nick");
			nick = (nick or jid.bare(event.from)) .. "[bot]";
		end

		local virtual_occupant_jid = jid.prep(room.jid .. "/" .. nick, true);
		if not virtual_occupant_jid then
			module:send(st.error_reply(event.stanza, "modify", "jid-malformed", "Nickname must pass strict validation", room.jid));
			return true;
		end

		local occupant = room:new_occupant(jid.bare(event.from), virtual_occupant_jid);
		local join = st.presence({from = event.from; to = virtual_occupant_jid});
		local dest_x = st.stanza("x", {xmlns = "http://jabber.org/protocol/muc#user"});
		occupant:set_session(event.from, join, true);
		room:save_occupant(occupant);
		room:publicise_occupant_status(occupant, dest_x);
		-- Inject virtual occupant to trick all the other hooks on this event that
		-- this is an actual legitimate participant.
		event.occupant = occupant;

	end
end, 66);

module:hook("muc-occupant-pre-join", function(event)
	local room = event.room;
	local nick = jid.resource(event.occupant.nick);
	if nick:sub(-5, -1) == "[bot]" then
		event.origin.send(st.error_reply(event.stanza, "modify", "policy-violation", "Only known bots may use the [bot] suffix", room.jid));
		return true;
	end
end, 3);

module:hook("muc-occupant-pre-change", function(event)
	local room = event.room;
	local nick = jid.resource(event.dest_occupant.nick);
	if nick:sub(-5, -1) == "[bot]" then
		event.origin.send(st.error_reply(event.stanza, "modify", "policy-violation", "Only known bots may use the [bot] suffix", room.jid));
		return true;
	end
end, 3);

if not module:get_option_boolean("bots_get_messages", true) then
	module:hook("muc-broadcast-message", function (event)
		event.room:broadcast(event.stanza, function (nick, occupant)
			if nick:sub(-5, -1) == "[bot]" or bots:contains(occupant.bare_jid) or bots:contains(jid.host(occupant.bare_jid)) then
				return false;
			else
				return true;
			end
		end);
		return true;
	end, -100);
end

if module:get_option_boolean("ignore_bot_errors", true) then
	module:hook("message/full", function (event)
		local stanza = event.stanza;
		if stanza.attr.type == "error" then
			if bots:contains(jid.bare(stanza.attr.from)) or bots:contains(jid.host(stanza.attr.from)) then
				module:log("debug", "Ignoring error from known bot");
				return true;
			end
		end
	end, 1);
end

assert(string.sub("foo[bot]", -5, -1) == "[bot]", "substring indicies, how do they work?");
