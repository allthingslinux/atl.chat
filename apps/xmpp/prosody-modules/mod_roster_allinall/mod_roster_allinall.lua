local rostermanager = require"core.rostermanager";
local jid_join = require"util.jid".join;
local host = module.host;
local sessions = prosody.hosts[host].sessions;

-- Make a *one-way* subscription. User will see when contact is online,
-- contact will not see when user is online.
local function subscribe(user, contact)
	local user_jid, contact_jid = jid_join(user, host), jid_join(contact, host);

	-- Update user's roster to say subscription request is pending...
	rostermanager.set_contact_pending_out(user, host, contact_jid);
	-- Update contact's roster to say subscription request is pending...
	rostermanager.set_contact_pending_in(contact, host, user_jid);
	-- Update contact's roster to say subscription request approved...
	rostermanager.subscribed(contact, host, user_jid);
	-- Update user's roster to say subscription request approved...
	rostermanager.process_inbound_subscription_approval(user, host, contact_jid);

	-- Push updates to both rosters
	rostermanager.roster_push(user, host, contact_jid);
	rostermanager.roster_push(contact, host, user_jid);
end


module:hook("resource-bind", function(event)
	local session = event.session;
	local user = session.username;
	local user_jid = jid_join(user, host);
	for contact in pairs(sessions) do
		if contact ~= user then
			local contact_jid = jid_join(contact, host);
			if not rostermanager.is_contact_subscribed(user, host, contact_jid) then
				subscribe(contact, user);
			end
			if not rostermanager.is_contact_subscribed(contact, host, user_jid) then
				subscribe(user, contact);
			end
		end
	end
end);

