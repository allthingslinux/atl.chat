local ip = require "util.ip";
local jid_bare = require "util.jid".bare;
local jid_split = require "util.jid".split;
local set = require "util.set";
local sha256 = require "util.hashes".sha256;
local st = require"util.stanza";
local rm = require "core.rostermanager";
local full_sessions = prosody.full_sessions;

local user_exists = require "core.usermanager".user_exists;

local new_rtbl_subscription = module:require("rtbl").new_rtbl_subscription;
local trie = module:require("trie");

local spam_source_domains = set.new();
local spam_source_ips = trie.new();
local spam_source_jids = set.new();
local default_spam_action = module:get_option("anti_spam_default_action", "bounce");
local custom_spam_actions = module:get_option("anti_spam_actions", {});

local spam_actions = setmetatable({}, {
	__index = function (t, reason)
		local action = rawget(custom_spam_actions, reason) or default_spam_action;
		rawset(t, reason, action);
		return action;
	end;
});

local count_spam_blocked = module:metric("counter", "anti_spam_blocked", "stanzas", "Stanzas blocked as spam", {"reason"});

local hosts = prosody.hosts;

local reason_messages = {
	default = "Rejected as spam";
	["known-spam-source"] = "Rejected as spam. Your server is listed as a known source of spam. Please contact your server operator.";
};

function block_spam(event, reason, action)
	if not action then
		action = spam_actions[reason];
	end
	event.spam_reason = reason;
	event.spam_action = action;
	if module:fire_event("spam-blocked", event) == false then
		module:log("debug", "Spam allowed by another module");
		return;
	end

	count_spam_blocked:with_labels(reason):add(1);

	if action == "bounce" then
		module:log("debug", "Bouncing likely spam %s from %s (%s)", event.stanza.name, event.stanza.attr.from, reason);
		event.origin.send(st.error_reply(event.stanza, "cancel", "policy-violation", reason_messages[reason] or reason_messages.default));
	else
		module:log("debug", "Discarding likely spam %s from %s (%s)", event.stanza.name, event.stanza.attr.from, reason);
	end

	return true;
end

function is_from_stranger(from_jid, event)
	local stanza = event.stanza;
	local to_user, to_host, to_resource = jid_split(stanza.attr.to);

	if not to_user then return false; end

	local to_session = full_sessions[stanza.attr.to];
	if to_session then return false; end

	if not (
		rm.is_contact_subscribed(to_user, to_host, from_jid) or
		rm.is_user_subscribed(to_user, to_host, from_jid) or
		rm.is_contact_pending_out(to_user, to_host, from_jid) or
		rm.is_contact_preapproved(to_user, to_host, from_jid)
	) then
		local from_user, from_host = jid_split(from_jid);

		-- Allow all messages from your own jid
		if from_user == to_user and from_host == to_host then
			return false; -- Pass through
		end
		if to_resource and stanza.attr.type == "groupchat" then
			return false; -- Pass through group chat messages
		end
		if rm.is_contact_subscribed(to_user, to_host, from_host) then
			-- If you have the sending domain in your roster,
			-- allow through (probably a gateway)
			return false;
		end
		return true; -- Stranger danger
	end
end

function is_spammy_server(session)
	if spam_source_domains:contains(session.from_host) then
		return true;
	end
	local raw_ip = session.ip;
	local parsed_ip = raw_ip and ip.new_ip(session.ip);
	-- Not every session has an ip - for example, stanzas sent from a
	-- local host session
	if parsed_ip and spam_source_ips:contains_ip(parsed_ip) then
		return true;
	end
end

function is_spammy_sender(sender_jid)
	return spam_source_jids:contains(sha256(sender_jid, true));
end

local spammy_strings = module:get_option_array("anti_spam_block_strings");
local spammy_patterns = module:get_option_array("anti_spam_block_patterns");

function is_spammy_content(stanza)
	-- Only support message content
	if stanza.name ~= "message" then return; end
	if not (spammy_strings or spammy_patterns) then return; end

	local body = stanza:get_child_text("body");
	if not body then return; end

	if spammy_strings then
		for _, s in ipairs(spammy_strings) do
			if body:find(s, 1, true) then
				return true;
			end
		end
	end
	if spammy_patterns then
		for _, s in ipairs(spammy_patterns) do
			if body:find(s) then
				return true;
			end
		end
	end
end

-- Set up RTBLs

local anti_spam_services = module:get_option_array("anti_spam_services", {});

for _, rtbl_service_jid in ipairs(anti_spam_services) do
	new_rtbl_subscription(rtbl_service_jid, "spam_source_domains", {
		added = function (item)
			spam_source_domains:add(item);
		end;
		removed = function (item)
			spam_source_domains:remove(item);
		end;
	});
	new_rtbl_subscription(rtbl_service_jid, "spam_source_ips", {
		added = function (item)
			local subnet_ip, subnet_bits = ip.parse_cidr(item);
			if not subnet_ip then
				return;
			end
			spam_source_ips:add_subnet(subnet_ip, subnet_bits);
		end;
		removed = function (item)
			local subnet_ip, subnet_bits = ip.parse_cidr(item);
			if not subnet_ip then
				return;
			end
			spam_source_ips:remove_subnet(subnet_ip, subnet_bits);
		end;
	});
	new_rtbl_subscription(rtbl_service_jid, "spam_source_jids_sha256", {
		added = function (item)
			spam_source_jids:add(item);
		end;
		removed = function (item)
			spam_source_jids:remove(item);
		end;
	});
end

module:hook("message/bare", function (event)
	local to_user, to_host = jid_split(event.stanza.attr.to);

	if not hosts[to_host] then
		module:log("warn", "Skipping filtering of message to unknown host <%s>", to_host);
		return;
	end

	local from_bare = jid_bare(event.stanza.attr.from);
	if user_exists(to_user, to_host) then
		if not is_from_stranger(from_bare, event) then
			return;
		end
	end

	module:log("debug", "Processing message from stranger...");

	if is_spammy_server(event.origin) then
		return block_spam(event, "known-spam-source");
	end

	if is_spammy_sender(from_bare) then
		return block_spam(event, "known-spam-jid");
	end

	if is_spammy_content(event.stanza) then
		return block_spam(event, "spam-content");
	end

	module:log("debug", "Allowing message through");
end, 500);

module:hook("presence/bare", function (event)
	if event.stanza.attr.type ~= "subscribe" then
		return;
	end


	local to_user, to_host = jid_split(event.stanza.attr.to);
	local from_bare = jid_bare(event.stanza.attr.from);

	if user_exists(to_user, to_host) then
		if not is_from_stranger(from_bare, event) then
			return;
		end
	end

	module:log("debug", "Processing subscription request from stranger...");

	if is_spammy_server(event.origin) then
		return block_spam(event, "known-spam-source");
	end

	module:log("debug", "Not from known spam source server");

	if is_spammy_sender(jid_bare(event.stanza.attr.from)) then
		return block_spam(event, "known-spam-jid");
	end

	module:log("debug", "Not from known spam source JID");

	module:log("debug", "Allowing subscription request through");
end, 500);
