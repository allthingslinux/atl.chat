-- mod_support_contact.lua
--
-- Config options:
--   support_contact = "support@hostname"; -- a JID
--   support_contact_nick = "Support!"; -- roster nick
--   support_contact_group = "Users being supported!"; -- the roster group in the support contact's roster

local host = module:get_host();

local support_contact = module:get_option_string("support_contact", "support@"..host);
local support_contact_nick = module:get_option_string("support_contact_nick", "Support");
local support_contact_group = module:get_option_string("support_contact_group", "Users");

if not(support_contact and support_contact_nick) then return; end

local rostermanager = require "core.rostermanager";
local jid_split = require "util.jid".split;
local st = require "util.stanza";

module:hook("user-registered", function(event)
	module:log("debug", "Adding support contact");

	local groups = support_contact_group and {[support_contact_group] = true;} or {};

	local node, host = event.username, event.host;
	local jid = node and (node..'@'..host) or host;
	local roster;

	roster = rostermanager.load_roster(node, host);
	if hosts[host] then
		roster[support_contact] = {subscription = "both", name = support_contact_nick, groups = {}};
	else
		roster[support_contact] = {subscription = "from", ask = "subscribe", name = support_contact_nick, groups = {}};
	end
	rostermanager.save_roster(node, host, roster);

	node, host = jid_split(support_contact);

	if hosts[host] then
		roster = rostermanager.load_roster(node, host);
		roster[jid] = {subscription = "both", groups = groups};
		rostermanager.save_roster(node, host, roster);
		rostermanager.roster_push(node, host, jid);
	else
		module:send(st.presence({from=jid, to=support_contact, type="subscribe"}));
	end
end);
