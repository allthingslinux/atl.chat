local st = require"util.stanza";
local jid_split = require "util.jid".split;
local jid_bare = require "util.jid".bare;
local is_contact_subscribed = require "core.rostermanager".is_contact_subscribed;
local throttle = require "util.throttle";
local gettime = require "socket".gettime;

local max = module:get_option_number("unsolicited_messages_per_minute", 10);
local s2s_max = module:get_option_number("unsolicited_s2s_messages_per_minute");
local multiplier = module:get_option_number("throttle_unsolicited_burst", 1);

function check_subscribed(event)
	local stanza, origin = event.stanza, event.origin;
	local log = origin.log or module._log;
	if stanza.attr.type == "error" then return end

	local to_orig = stanza.attr.to;
	if to_orig == nil or to_orig == origin.full_jid then return end -- to self

	local to_bare = jid_bare(to_orig);
	local from_jid = jid_bare(stanza.attr.from);
	if to_bare == from_jid then return end -- to own resource

	-- Check if it's a message to a joined room
	local rooms = origin.rooms_joined;
	if rooms and rooms[to_bare] then
		return
	end

	-- Retrieve or create throttle object
	local lim = origin.throttle_unsolicited;
	if not lim then
		lim = throttle.create(max * multiplier, 60 * multiplier);
		origin.throttle_unsolicited = lim;
	end

	local to_user, to_host = jid_split(to_orig);
	if to_user and not is_contact_subscribed(to_user, to_host, from_jid) then
		log("debug", "[unsolicited] %s is not subscribed to %s@%s", from_jid, to_user, to_host);
		if not lim:poll(1) then
			log("warn", "[unsolicited] Sent too many messages to non-contacts, bouncing message");
			origin.firewall_mark_unsolicited = gettime();
			origin.send(st.error_reply(stanza, "cancel", "service-unavailable"));
			return true;
		end
	end
end

module:hook("pre-message/bare", check_subscribed, 200);
module:hook("pre-message/full", check_subscribed, 200);

local full_sessions = prosody.full_sessions;

-- Rooms and throttle creation will differ for s2s
function check_subscribed_s2s(event)
	local stanza, origin = event.stanza, event.origin;
	local log = origin.log or module._log;

	if origin.type ~= "s2sin" then return end

	local to_orig = stanza.attr.to;
	local from_orig = stanza.attr.from;
	local from_bare = jid_bare(from_orig);

	local target = full_sessions[to_orig];
	if target then
		local rooms = target.rooms_joined;
		if rooms and rooms[from_bare] then
			log("debug", "Message to joined room, no limit");
			return
		end
	end

	-- Retrieve or create throttle object
	local lim = origin.throttle_unsolicited;
	if not lim then
		log("debug", "New s2s throttle");
		lim = throttle.create(s2s_max * multiplier, 60 * multiplier);
		origin.throttle_unsolicited = lim;
	end

	return check_subscribed(event);
end

if s2s_max then
	module:hook("message/bare", check_subscribed_s2s, 200);
	module:hook("message/full", check_subscribed_s2s, 200);
end

module:depends("track_muc_joins");
