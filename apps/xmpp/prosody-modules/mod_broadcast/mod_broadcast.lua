local is_admin = require "core.usermanager".is_admin;
local allowed_senders = module:get_option_set("broadcast_senders", {});
local from_address = module:get_option_string("broadcast_from");

local jid_bare = require "util.jid".bare;

function send_to_online(message)
	local c = 0;
	for hostname, host_session in pairs(hosts) do
		if host_session.sessions then
			for username in pairs(host_session.sessions) do
				c = c + 1;
				message.attr.to = username.."@"..hostname;
				module:send(message);
			end
		end
	end
	return c;
end

function send_message(event)
	local stanza = event.stanza;
	local from = stanza.attr.from;
	if is_admin(from) or allowed_senders:contains(jid_bare(from)) then
		if from_address then
			stanza = st.clone(stanza);
			stanza.attr.from = from_address;
		end
		local c = send_to_online(stanza);
		module:log("debug", "Broadcast stanza from %s to %d online users", from, c);
		return true;
	else
		module:log("warn", "Broadcasting is not allowed for %s", from);
	end
end

module:hook("message/bare", send_message);
