local st = require "util.stanza";

local default_enable = module:get_option_boolean("muc_offline_delivery_default", false);

module:add_item("muc-registration-field", {
	name = "offline_delivery";
	var = "{http://tigase.org/protocol/muc}offline";
	type = "boolean";
	label = "Receive messages while not connected to the room";
	value = default_enable;
});

module:hook("muc-registration-submitted", function (event)
	local deliver_offline = event.submitted_data.offline_delivery;
	event.affiliation_data.offline_delivery = deliver_offline;
end);

module:hook("muc-add-history", function (event)
	module:log("debug", "Broadcasting message to offline occupants...");
	local sent = 0;
	local room = event.room;
	for jid, affiliation, data in room:each_affiliation() do --luacheck: ignore 213/affiliation
		local reserved_nickname = data and data.reserved_nickname;
		local user_setting = data and data.offline_delivery or nil;
		if reserved_nickname and (user_setting or (user_setting == nil and default_enable)) then
			local is_absent = not room:get_occupant_by_nick(room.jid.."/"..reserved_nickname);
			if is_absent then
				module:log("debug", "Forwarding message to offline member <%s>", jid);
				local msg = st.clone(event.stanza);
				msg.attr.to = jid;
				module:send(msg);
				sent = sent + 1;
			end
		end
	end
	if sent > 0 then
		module:log("debug", "Sent message to %d offline occupants", sent);
	end
end);
