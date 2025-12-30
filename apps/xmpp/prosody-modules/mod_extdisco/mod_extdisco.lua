local st = require "util.stanza";

local services = module:get_option("external_services");

local xmlns_extdisco_1 = "urn:xmpp:extdisco:1";
local xmlns_extdisco_2 = "urn:xmpp:extdisco:2";

module:add_feature(xmlns_extdisco_1);
module:add_feature(xmlns_extdisco_2);

local function handle_services(event)
	local origin, stanza = event.origin, event.stanza;
	local service = stanza.tags[1];
	local service_type = service.attr.type;
	local reply = st.reply(stanza):tag("services", { xmlns = service.attr.xmlns });
	for host, service_info in pairs(services) do
		if not(service_type) or service_info.type == service_type then
			reply:tag("service", {
				host = host;
				port = service_info.port;
				transport = service_info.transport;
				type = service_info.type;
				username = service_info.username;
				password = service_info.password;
			}):up();
		end
	end
	origin.send(reply);
	return true;
end
module:hook("iq-get/host/"..xmlns_extdisco_1..":services", handle_services);
module:hook("iq-get/host/"..xmlns_extdisco_2..":services", handle_services);

local function handle_credentials(event)
	local origin, stanza = event.origin, event.stanza;
	local credentials = stanza.tags[1];
	local host = credentials.attr.host;
	if not host then
		origin.send(st.error_reply(stanza, "cancel", "bad-request", "No host specified"));
		return true;
	end
	local service_info = services[host];
	if not service_info then
		origin.send(st.error_reply(stanza, "cancel", "item-not-found", "No such service known"));
		return true;
	end
	local reply = st.reply(stanza)
		:tag("credentials", { xmlns = credentials.attr.xmlns })
			:tag("service", {
				host = host;
				username = service_info.username;
				password = service_info.password;
			}):up();
	origin.send(reply);
	return true;
end
module:hook("iq-get/host/"..xmlns_extdisco_1..":credentials", handle_credentials);
module:hook("iq-get/host/"..xmlns_extdisco_2..":credentials", handle_credentials);
