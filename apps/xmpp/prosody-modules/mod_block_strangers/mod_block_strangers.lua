
local st = require"util.stanza";
local jid_split = require "util.jid".split;
local jid_bare = require "util.jid".bare;
local is_contact_subscribed = require "core.rostermanager".is_contact_subscribed;
local full_sessions = prosody.full_sessions;

local function has_directed_presence(user, jid)
	local session = full_sessions[user];
	if session then
		local directed = session.directed;
		if directed then
			return directed[jid];
		end
	end
end

function check_subscribed(event)
	local stanza = event.stanza;
	local to_user, to_host, to_resource = jid_split(stanza.attr.to);
	local from_jid = jid_bare(stanza.attr.from);
	if to_user and not has_directed_presence(stanza.attr.to, from_jid) and not is_contact_subscribed(to_user, to_host, from_jid) then
		-- Allow all messages from your own jid
		if from_jid == to_user.."@"..to_host then
			return nil; -- Pass through
		end
		if to_resource and stanza.attr.type == "groupchat"
		or stanza.name == "iq" and (stanza.attr.type == "result" or stanza.attr.type == "error") then
			return nil; -- Pass through
		end
		if stanza.name == "iq" and ( stanza.attr.type == "get" or stanza.attr.type == "set" ) then
			event.origin.send(st.error_reply(stanza, "cancel", "service-unavailable"));
		end
		return true; -- Drop stanza
	end
end

module:hook("message/bare", check_subscribed, 200);
module:hook("message/full", check_subscribed, 200);
module:hook("iq/full", check_subscribed, 200);
