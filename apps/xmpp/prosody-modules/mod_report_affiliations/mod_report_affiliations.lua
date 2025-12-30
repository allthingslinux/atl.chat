local dt = require "util.datetime";
local jid = require "util.jid";
local st = require "util.stanza";

local rm = require "core.rostermanager";
local um = require "core.usermanager";

local traits = module:require("traits");

local xmlns_aff = "urn:xmpp:raa:0";

local is_host_anonymous = module:get_option_string("authentication") == "anonymous";

local trusted_servers = module:get_option_inherited_set("report_affiliations_trusted_servers", {});

local roles = {
	-- These affiliations are defined by XEP-0489, and we map a set of Prosody roles to each one
	admin = module:get_option_set("report_affiliations_admin_roles", { "prosody:admin", "prosody:operator" });
	member = module:get_option_set("report_affiliations_member_roles", { "prosody:member" });
	registered = module:get_option_set("report_affiliations_registered", { "prosody:user", "prosody:registered" });
	guest = module:get_option_set("report_affiliations_anonymous", { "prosody:guest" });
};

-- Map of role to affiliation
local role_affs = {
	-- [role (e.g. "prosody:guest")] = affiliation ("admin"|"member"|"registered"|"guest");
};

--Build the role->affiliation map based on the config
for aff, aff_roles in pairs(roles) do
	for role in aff_roles do
		role_affs[role] = aff;
	end
end

local account_details_store = module:open_store("account_details");
local lastlog2_store = module:open_store("lastlog2");

module:add_feature(xmlns_aff);
module:add_feature(xmlns_aff.."#embed-presence-sub");
module:add_feature(xmlns_aff.."#embed-presence-directed");

local function get_registered_timestamp(username)
	if um.get_account_info then
		local ts = um.get_account_info(username, module.host);
		if ts then return ts.created; end
	end

	local account_details = account_details_store:get(username);
	if account_details and account_details.registered then
		return account_details.registered;
	end

	local lastlog2 = lastlog2_store:get(username);
	if lastlog2 and lastlog2.registered then
		return lastlog2.registered.timestamp;
	end

	return nil;
end

local function get_trust_score(username)
	return math.floor(100 * (1 - traits.get_probability_bad(username)));
end


local function get_account_type(username)
	if is_host_anonymous then
		return "anonymous";
	end

	if not um.get_user_role then
		return "registered"; -- COMPAT w/0.12
	end

	local user_role = um.get_user_role(username, module.host);

	return role_affs[user_role] or "registered";
end

function get_info_element(username)
	local account_type = get_account_type(username);

	local since, trust;

	if account_type == "registered" then
		since = get_registered_timestamp(username);
		trust = get_trust_score(username);
	end

	return st.stanza("info", {
		affiliation = account_type;
		since = since and dt.datetime(since - (since%86400)) or nil;
		trust = ("%d"):format(trust);
		xmlns = xmlns_aff;
	});
end

-- Outgoing presence

local function embed_in_outgoing_presence(pres_type)
	return function (event)
		local origin, stanza = event.origin, event.stanza;

		stanza:remove_children("info", xmlns_aff);

		-- Unavailable presence is pretty harmless, and blocking it may cause
		-- weird issues.
		if (pres_type == "bare" and stanza.attr.type == "unavailable")
		or (pres_type == "full" and stanza.attr.type ~= nil) then
			return;
		end

		-- Only attach info to stanzas sent to "strangers" (users that have not
		-- approved us to see their presence)
		if rm.is_user_subscribed(origin.username, origin.host, stanza.attr.to) then
			return;
		end

		local info = get_info_element(origin.username);
		if not info then return; end

		stanza:add_direct_child(info);
	end;
end

module:hook("pre-presence/bare", embed_in_outgoing_presence("bare"));
module:hook("pre-presence/full", embed_in_outgoing_presence("full"));

-- Handle direct queries

local function should_permit_query(from_jid, to_username) --luacheck: ignore 212/to_username
	local from_node, from_host = jid.split(from_jid);
	if from_node then
		return false;
	end

	-- Who should we respond to?
	-- Only respond to domains
	-- Does user have a JID with this domain in directed presence? (doesn't work with bare JIDs)
	-- Does this user have a JID with domain in pending subscription requests?

	if trusted_servers:contains(from_host) then
		return true;
	end

	return false;
end

module:hook("iq-get/bare/urn:xmpp:raa:0:query", function (event)
	local origin, stanza = event.origin, event.stanza;
	local username = jid.node(stanza.attr.to);

	if not should_permit_query(stanza.attr.from, username) then
		origin.send(st.error_reply(stanza, "auth", "forbidden"));
		return true;
	end

	local info = get_info_element(username);

	local reply = st.reply(stanza)
		:add_child(info);
	origin.send(reply);

	return true;
end);
