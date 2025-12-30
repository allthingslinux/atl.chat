local jid_bare = require "util.jid".bare;
local st = require "util.stanza";

local rooms = assert(module:depends"muc".rooms, "This module is not needed with Prosody >=0.11");

module:hook("presence/full", function (event)
	local stanza, origin = event.stanza, event.origin;
	if stanza.attr.type ~= nil then return end

	local muc_x = stanza:get_child("x", "http://jabber.org/protocol/muc");

	local room_jid = jid_bare(stanza.attr.to);
	local room = rooms[room_jid];
	if not room then
		if muc_x then
			-- Normal MUC creation
		else
			module:log("info", "GC 1.0 room creation from %s", stanza.attr.from);
			module:send(st.iq({type="get",id=module.name,from=module.host,to=stanza.attr.from}):query("jabber:iq:version"));
		end
		return;
	end
	local current_nick = room._jid_nick[stanza.attr.from];

	if current_nick then
		-- present
		if muc_x then
			module:log("info", "MUC desync with %s", stanza.attr.from);
			module:send(st.iq({type="get",id=module.name,from=module.host,to=stanza.attr.from}):query("jabber:iq:version"));
		else
			-- normal presence update
		end
	else
		-- joining
		if muc_x then
			-- normal join
		else
			module:log("info", "GC 1.0 join from %s", stanza.attr.from);
			module:send(st.iq({type="get",id=module.name,from=module.host,to=stanza.attr.from}):query("jabber:iq:version"));
		end
	end
end);

module:hook("iq-result/host/"..module.name, function (event)
	local stanza, origin = event.stanza, event.origin;
	local version = stanza:get_child("query", "jabber:iq:version");
	if not version then
		module:log("info", "%s replied with an invalid version reply: %s", stanza.attr.from, tostring(stanza));
		return true;
	end
	module:log("info", "%s is running: %s %s", stanza.attr.from, version:get_child_text("name"), version:get_child_text("version"));
end);

module:hook("iq-error/host/"..module.name, function (event)
	local stanza, origin = event.stanza, event.origin;
	module:log("info", "%s replied with an error: %s %s", stanza.attr.from, stanza:get_error());
	return true;
end);
