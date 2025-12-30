-- Copyright (C) 2016 Kim Alvefur
-- Copyright (C) 2017 Thilo Molitor
--

local filter_muc = module:get_option_boolean("csi_battery_saver_filter_muc", false);
local queue_size = module:get_option_number("csi_battery_saver_queue_size", 256);

module:depends"csi"
if filter_muc then module:depends"track_muc_joins"; end		-- only depend on this module if we actually use it
local s_match = string.match;
local s_sub = string.sub;
local jid = require "util.jid";
local new_queue = require "util.queue".new;
local datetime = require "util.datetime";
local st = require "util.stanza";

local xmlns_delay = "urn:xmpp:delay";

-- a log id for this module instance
local id = s_sub(require "util.hashes".sha256(datetime.datetime(), true), 1, 4);


-- Returns a forwarded message, and either "in" or "out" depending on the direction
-- Returns nil if the message is not a carbon
local function extract_carbon(stanza)
	local carbon = stanza:child_with_ns("urn:xmpp:carbons:2") or stanza:child_with_ns("urn:xmpp:carbons:1");
	if not carbon then return; end
	local direction = carbon.name == "sent" and "out" or "in";
	local forward = carbon:get_child("forwarded", "urn:xmpp:forward:0");
	local message = forward and forward:child_with_name("message") or nil;
	if not message then return; end
	return message, direction;
end

local function new_pump(session, output, ...)
	-- luacheck: ignore 212/self
	local q = new_queue(...);
	local flush = true;
	function q:pause()
		flush = false;
	end
	function q:resume()
		flush = true;
		return q:flush();
	end
	local push = q.push;
	function q:push(item)
		local ok = push(self, item);
		if not ok then
			session.log("debug", "mod_csi_battery_saver(%s): Queue full (%d items), forcing flush...", id, q:count());
			q:flush();
			output(item, self);
		elseif flush then
			return q:flush();
		end
		return true;
	end
	function q:flush(alternative_output)
		local out = alternative_output or output;
		local item = self:pop();
		while item do
			out(item, self);
			item = self:pop();
		end
		return true;
	end
	return q;
end

local function is_stamp_needed(stanza, session)
	local st_name = stanza and stanza.name or nil;
	if st_name == "presence" then
		return true;
	elseif st_name == "message" then
		if stanza:get_child("delay", xmlns_delay) then return false; end
		if stanza.attr.type == "chat" or stanza.attr.type == "groupchat" then return true; end
	end
	return false;
end

local function add_stamp(stanza, session)
	local bare_jid = jid.bare(session.full_jid or session.host);
	stanza = stanza:tag("delay", { xmlns = xmlns_delay, from = bare_jid, stamp = datetime.datetime()});
	return stanza;
end

local function is_important(stanza, session)
	-- some special handlings
	if stanza == " " then						-- whitespace keepalive
		return true;
	elseif type(stanza) == "string" then		-- raw data
		return true;
	elseif not st.is_stanza(stanza) then		-- this should probably never happen
		return true;
	end
	if stanza.attr.xmlns ~= nil then			-- nonzas (stream errors, stream management etc.)
		return true;
	end
	local st_name = stanza and stanza.name or nil;
	if not st_name then return true; end	-- nonzas are always important
	if st_name == "presence" then
		local st_type = stanza.attr.type;
		-- subscription requests are important
		if st_type == "subscribe" then return true; end
		-- muc status codes are important, too
		local muc_x = stanza:get_child("x", "http://jabber.org/protocol/muc#user")
		local muc_status = muc_x and muc_x:get_child("status") or nil
		if muc_status and muc_status.attr.code then return true; end
		return false;
	elseif st_name == "message" then
		-- unpack carbon copies
		local carbon, stanza_direction = extract_carbon(stanza);
		--session.log("debug", "mod_csi_battery_saver(%s): stanza_direction = %s, carbon = %s, stanza = %s", id, stanza_direction, carbon and "true" or "false", tostring(stanza));
		if carbon then stanza = carbon; end

		local st_type = stanza.attr.type;

		-- errors are always important
		if st_type == "error" then return true; end;

		-- headline message are always not important, with some exceptions
		if st_type == "headline" then
			-- allow headline pushes of mds updates (XEP-0490)
			if stanza:find("{http://jabber.org/protocol/pubsub#event}event/items@node") == "urn:xmpp:mds:displayed:0" then return true; end;
			return false
		end

		-- mediated muc invites
		if stanza:find("{http://jabber.org/protocol/muc#user}x/invite") then return true; end;
		if stanza:get_child("x", "jabber:x:conference") then return true; end;

		-- chat markers (XEP-0333) are important, too, because some clients use them to update their notifications
		if stanza:child_with_ns("urn:xmpp:chat-markers:0") then return true; end;

		-- XEP-0353: Jingle Message Initiation incoming call messages
		if stanza:child_with_ns("urn:xmpp:jingle-message:0") then return true; end
		if stanza:child_with_ns("urn:xmpp:jingle-message:1") then return true; end

		-- carbon copied outgoing messages are important (some clients update their notifications upon receiving those) --> don't return false here
		--if carbon and stanza_direction == "out" then return false; end

		-- We can't check for body contents in encrypted messages, so let's treat them as important
		-- Some clients don't even set a body or an empty body for encrypted messages

		-- check omemo https://xmpp.org/extensions/inbox/omemo.html
		if stanza:get_child("encrypted", "eu.siacs.conversations.axolotl") or stanza:get_child("encrypted", "urn:xmpp:omemo:0") then return true; end

		-- check xep27 pgp https://xmpp.org/extensions/xep-0027.html
		if stanza:get_child("x", "jabber:x:encrypted") then return true; end

		-- check xep373 pgp (OX) https://xmpp.org/extensions/xep-0373.html
		if stanza:get_child("openpgp", "urn:xmpp:openpgp:0") then return true; end

		-- check eme
		if stanza:get_child("encryption", "urn:xmpp:eme:0") then return true; end

		local body = stanza:get_child_text("body");
		if st_type == "groupchat" then
			if stanza:get_child_text("subject") then return true; end
			if body == nil or body == "" then return false; end
			-- body contains text, let's see if we want to process it further
			if not filter_muc then		-- default case
				local stanza_important = module:fire_event("csi-is-stanza-important", { stanza = stanza, session = session });
				if stanza_important ~= nil then return stanza_important; end
				return true;		-- deemed unknown/high priority by mod_csi_muc_priorities or some other module
			else
				if body:find(session.username, 1, true) then return true; end
				local rooms = session.rooms_joined;
				if not rooms then return false; end
				local room_nick = rooms[jid.bare(stanza_direction == "in" and stanza.attr.from or stanza.attr.to)];
				if room_nick and body:find(room_nick, 1, true) then return true; end
				return false;
			end
		end
		return body ~= nil and body ~= "";
	end
	return true;
end

module:hook("csi-client-inactive", function (event)
	local session = event.origin;
	if not session.resource then
		session.log("warn", "Ignoring csi if no resource is bound!");
		return;
	end
	if session.pump then
		session.log("debug", "mod_csi_battery_saver(%s): Client is inactive, buffering unimportant outgoing stanzas", id);
		session.pump:pause();
	else
		session.log("debug", "mod_csi_battery_saver(%s): Client is inactive the first time, initializing module for this session", id);
		local pump = new_pump(session, session.send, queue_size);
		pump:pause();
		session.pump = pump;
		session._pump_orig_send = session.send;
		function session.send(stanza)
			session.log("debug", "mod_csi_battery_saver(%s): Got outgoing stanza: <%s>", id, tostring(stanza.name or stanza));
			local important = is_important(stanza, session);
			-- clone stanzas before adding delay stamp and putting them into the queue
			if st.is_stanza(stanza) then stanza = st.clone(stanza); end
			-- add delay stamp to unimportant (buffered) stanzas that can/need be stamped
			if not important and is_stamp_needed(stanza, session) then stanza = add_stamp(stanza, session); end
			-- add stanza to outgoing queue and flush the buffer if needed
			pump:push(stanza);
			if important then
				session.log("debug", "mod_csi_battery_saver(%s): Encountered important stanza, flushing buffer: <%s>", id, tostring(stanza.name or stanza));
				pump:flush();
			end
			return true;
		end
	end
end);

module:hook("csi-client-active", function (event)
	local session = event.origin;
	if not session.resource then
		session.log("warn", "Ignoring csi if no resource is bound!");
		return;
	end
	if session.pump then
		session.log("debug", "mod_csi_battery_saver(%s): Client is active, resuming direct delivery", id);
		session.pump:resume();
	end
end);

-- clean up this session on hibernation end
-- but don't change resumed.send(), it is already overwritten with session.send() by the smacks module
module:hook("smacks-hibernation-end", function (event)
	local session = event.resumed;
	if session.pump then
		session.log("debug", "mod_csi_battery_saver(%s): Hibernation ended, flushing buffer and afterwards disabling for this session", id);
		session.pump:flush(session.send);		-- use the fresh session.send() introduced by the smacks resume
		-- don't reset session.send() because this is not the send previously overwritten by this module, but a fresh one
		-- session.send = session._pump_orig_send;
		session.pump = nil;
		session._pump_orig_send = nil;
	end
end, 1000);		-- high priority to prevent message reordering on resumption (we want to flush our buffers *first*)

function module.unload()
	module:log("info", "%s: Unloading module, flushing all buffers", id);
	local host_sessions = prosody.hosts[module.host].sessions;
	for _, user in pairs(host_sessions) do
		for _, session in pairs(user.sessions) do
			if session.pump then
				session.log("debug", "mod_csi_battery_saver(%s): Flushing buffer and restoring to original session.send()", id);
				session.pump:flush();
				session.send = session._pump_orig_send;
				session.pump = nil;
				session._pump_orig_send = nil;
			end
		end
	end
end

module:log("info", "%s: Successfully loaded module", id);
