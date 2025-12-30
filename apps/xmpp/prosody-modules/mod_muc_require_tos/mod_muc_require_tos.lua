local jid = require "util.jid";
local id = require "util.id";
local st = require "util.stanza";

local quick_response_ns = "urn:xmpp:tmp:quick-response";
local welcome_message = module:get_option_string("tos_welcome_message");
local yes_message = module:get_option_string("tos_yes_message");
local no_message = module:get_option_string("tos_no_message");

module:hook("muc-occupant-session-new", function(event)
	local origin = event.origin;
	local room = event.room;
	local occupant = event.occupant;
	local nick = occupant.nick;
	module:log("debug", "%s joined %s (%s)", nick, room, origin);
	if occupant.role == "visitor" then
		local message = st.message({
			type = "groupchat",
			to = occupant.nick,
			from = room.jid,
			id = id.medium(),
			["xml:lang"] = "en",
		}, welcome_message)
			:tag("response", { xmlns = quick_response_ns, value = "yes", label = "I accept." }):up()
			:tag("response", { xmlns = quick_response_ns, value = "no", label = "I decline." }):up();
		origin.send(message);
	end
end, 19);

module:hook("muc-occupant-groupchat", function(event)
	local occupant = event.occupant;
	if occupant == nil or occupant.role ~= "visitor" then
		return;
	end
	local origin = event.origin;
	local room = event.room;
	local stanza = event.stanza;
	-- Namespace must be nil instead of "jabber:client" here.
	local body = stanza:get_child_text("body", nil);
	module:log("debug", "%s replied %s", occupant.nick, body);
	if body == "yes" then
		room:set_affiliation(true, occupant.bare_jid, "member", "Agreed to the TOS.");
		origin.send(st.reply(stanza):body(yes_message, { ["xml:lang"] = "en" }));
	elseif body == "no" then
		origin.send(st.reply(stanza):body(no_message, { ["xml:lang"] = "en" }));
		room:set_role(true, occupant.nick, "none", "Declined the TOS.");
	end
end, 51); -- Priority must be > 50, <forbidden/> is sent at this priority.
