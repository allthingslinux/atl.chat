local st = require"util.stanza";
local jid_split = require "util.jid".split;
local jid_bare = require "util.jid".bare;
local is_contact_subscribed = require "core.rostermanager".is_contact_subscribed;
local uuid_generate = require "util.uuid".generate;
local set = require "util.set";

local recently_queried = set.new();

local version_id = uuid_generate();
local disco_id = uuid_generate();

module:hook("iq-result/host/" .. version_id, function (event)
	module:log("info", "Stranger <%s> version: %s", event.stanza.attr.from, event.stanza);
	return true;
end);

module:hook("iq-result/host/" .. disco_id, function (event)
	module:log("info", "Stranger <%s> disco: %s", event.stanza.attr.from, event.stanza);
	return true;
end);

function check_subscribed(event)
	local stanza = event.stanza;
	local local_user_jid = stanza.attr.to;
	local to_user, to_host, to_resource = jid_split(local_user_jid);
	local stranger_jid = stanza.attr.from;

	if recently_queried:contains(stranger_jid) then
		module:log("debug", "Not re-poking <%s>", stranger_jid);
		return nil;
	end

	local from_jid = jid_bare(stranger_jid);

	if to_user and not is_contact_subscribed(to_user, to_host, from_jid) then
		if to_resource and stanza.attr.type == "groupchat" then
			return nil;
		end

		recently_queried:add(stranger_jid);

		module:send(st.iq({ type = "get", to = stranger_jid, from = to_host, id = version_id }):query("jabber:iq:version"));

		module:send(st.iq({ type = "get", to = stranger_jid, from = to_host, id = disco_id }):query("http://jabber.org/protocol/disco#info"));
	end

	return nil;
end

module:hook("message/bare", check_subscribed, 225);
module:hook("message/full", check_subscribed, 225);
-- Not hooking iqs, as that could turn into infinite loops!
