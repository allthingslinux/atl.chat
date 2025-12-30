local rostermanager = require "core.rostermanager";
local jid = require "util.jid";
local st = require "util.stanza";
local core_post_stanza = prosody.core_post_stanza;

local function handle_inbound_subscription_request(origin, stanza)
	local to_bare, from_bare = jid.bare(stanza.attr.to), jid.bare(stanza.attr.from);
	local node, host = jid.split(to_bare);
	stanza.attr.from, stanza.attr.to = from_bare, to_bare;
	module:log("info", "Auto-accepting inbound subscription request from %s to %s", tostring(from_bare), tostring(to_bare));

	if not rostermanager.is_contact_subscribed(node, host, from_bare) then
		core_post_stanza(hosts[host], st.presence({from=to_bare, to=from_bare, type="unavailable"}), true); -- acknowledging receipt
		module:log("debug", "receipt acknowledged");
		if rostermanager.set_contact_pending_in(node, host, from_bare) then
			module:log("debug", "set pending in");
			if rostermanager.subscribed(node, host, from_bare) then
				module:log("debug", "set subscribed");
				rostermanager.roster_push(node, host, to_bare);
				module:log("debug", "pushed roster item");
				local subscribed_stanza = st.reply(stanza);
				subscribed_stanza.attr.type = "subscribed";
				core_post_stanza(hosts[host], subscribed_stanza);
				module:log("debug", "sent subscribed");
				hosts[host].modules.presence.send_presence_of_available_resources(node, host, to_bare, origin);
				module:log("debug", "sent available presence of all resources");
				-- Add return subscription from user to contact
				local subscribe_stanza = st.reply(stanza);
				subscribe_stanza.attr.type = "subscribe";
				if rostermanager.set_contact_pending_out(node, host, from_bare) then
					rostermanager.roster_push(node, host, from_bare);
				end
				core_post_stanza(hosts[host], subscribe_stanza);
				return true;
			end
		end
	end
	module:log("warn", "Failed to auto-accept subscription request from %s to %s", tostring(from_bare), tostring(to_bare));
end

module:hook("presence/bare", function (event)
	local stanza = event.stanza;
	if stanza.attr.type == "subscribe" then
		handle_inbound_subscription_request(event.origin, stanza);
		return true;
	end
end, 0.1);
