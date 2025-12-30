--
-- mod_saslauth_muc
--   This module implements http://xmpp.org/extensions/inbox/remote-auth.html for Prosody's MUC component
--
-- In your config:
--   Component "conference.example.com" "muc"
--       modules_enabled = { "saslauth_muc" };
--
--

local timeout = 60; -- SASL timeout in seconds

-- various imports
local new_sasl = require "util.sasl".new;
local st = require "util.stanza";
local timer = require "util.timer";

local jid_bare = require "util.jid".bare;
local jid_prep = require "util.jid".prep;
local base64 = require "util.encodings".base64;

local hosts = hosts;
local module = module;
local pairs, next = pairs, next;
local os_time = os.time;

local muc_password = module:require("muc/password");

-- SASL sessions management
local _rooms = {}; -- SASL data
local function get_handler_for(room, jid) return _rooms[room] and _rooms[room][jid]; end
local function remove_handler_for(room, jid) if _rooms[room] then _rooms[room][jid] = nil; end end
local function create_handler_for(room_jid, jid)
	_rooms[room_jid] = _rooms[room_jid] or {};
	_rooms[room_jid][jid] = new_sasl(module.host, { plain = function(sasl, username, realm)
		local muc = hosts[module.host].modules.muc;
		local room = muc and muc.get_room_from_jid(room_jid);
		local password = room and muc_password.get(room);
		local ret = password and true or nil;
		return password or "", ret;
	end });
	_rooms[room_jid][jid].timeout = os_time() + timeout;
	return _rooms[room_jid][jid];
end

-- Timer to clear SASL sessions
timer.add_task(timeout, function(now)
	for room, handlers in pairs(_rooms) do
		for jid, handler in pairs(handlers) do
			if handler.timeout <= now then handlers[jid] = nil; end
		end
		if next(handlers) == nil then _rooms[room] = nil; end
	end
	return timeout;
end);
function module.unload()
	timeout = nil; -- stop timer on unload
end

-- Stanza handlers
-- Don't allow anyone to join room unless they provide the password
module:hook("muc-occupant-pre-join", function(event)
	local room, stanza = event.room, event.stanza;
	local room_password = muc_password.get(room);
	if room_password then -- room has a password
		local x = stanza:get_child("x", "http://jabber.org/protocol/muc");
		local password = x and x:get_child_text("password", "http://jabber.org/protocol/muc");
		if not password then -- no password sent
			local sasl_handler = get_handler_for(jid_bare(stanza.attr.to), stanza.attr.from);
			if x and sasl_handler and sasl_handler.authorized then -- if already passed SASL
				x:reset():tag("password", { xmlns = "http://jabber.org/protocol/muc" }):text(room_password);
			else
				event.origin.send(st.error_reply(stanza, "auth", "not-authorized")
					:tag("sasl-required", { xmlns = "urn:xmpp:errors" }));
				return true;
			end
		end
	end
end, -18);

module:hook("iq-get/bare/urn:ietf:params:xml:ns:xmpp-sasl:mechanisms", function(event)
	local origin, stanza = event.origin, event.stanza;

	local reply = st.reply(stanza):tag("mechanisms", { xmlns='urn:ietf:params:xml:ns:xmpp-sasl' });
	for mechanism in pairs(create_handler_for(stanza.attr.to, true):mechanisms()) do
		reply:tag("mechanism"):text(mechanism):up();
	end
	origin.send(reply:up());
	return true;
end);

local function build_reply(stanza, status, ret, err_msg)
	local reply = st.stanza(status, {xmlns = "urn:ietf:params:xml:ns:xmpp-sasl"});
	if status == "challenge" then
		reply:text(base64.encode(ret or ""));
	elseif status == "failure" then
		reply:tag(ret):up();
		if err_msg then reply:tag("text"):text(err_msg); end
	elseif status == "success" then
		reply:text(base64.encode(ret or ""));
	else
		module:log("error", "Unknown sasl status: %s", status);
	end
	return st.reply(stanza):add_child(reply);
end
local function handle_status(stanza, status)
	if status == "failure" then
		remove_handler_for(stanza.attr.to, stanza.attr.from);
	elseif status == "success" then
		get_handler_for(stanza.attr.to, stanza.attr.from).authorized = true;
	end
end
local function sasl_process_cdata(session, stanza)
	local text = stanza.tags[1][1];
	if text then
		text = base64.decode(text);
		if not text then
			remove_handler_for(stanza.attr.to, stanza.attr.from);
			session.send(build_reply(stanza, "failure", "incorrect-encoding"));
			return true;
		end
	end
	local status, ret, err_msg = get_handler_for(stanza.attr.to, stanza.attr.from):process(text);
	handle_status(stanza, status);
	local s = build_reply(stanza, status, ret, err_msg);
	session.send(s);
	return true;
end

module:hook("iq-set/bare/urn:ietf:params:xml:ns:xmpp-sasl:auth", function(event)
	local session, stanza = event.origin, event.stanza;

	if not create_handler_for(stanza.attr.to, stanza.attr.from):select(stanza.tags[1].attr.mechanism) then
		remove_handler_for(stanza.attr.to, stanza.attr.from);
		session.send(build_reply(stanza, "failure", "invalid-mechanism"));
		return true;
	end
	return sasl_process_cdata(session, stanza);
end);
module:hook("iq-set/bare/urn:ietf:params:xml:ns:xmpp-sasl:response", function(event)
	local session, stanza = event.origin, event.stanza;
	if not get_handler_for(stanza.attr.to, stanza.attr.from) then
		session.send(build_reply(stanza, "failure", "not-authorized", "Out of order SASL element"));
		return true;
	end
	return sasl_process_cdata(session, event.stanza);
end);
module:hook("iq-set/bare/urn:ietf:params:xml:ns:xmpp-sasl:abort", function(event)
	local session, stanza = event.origin, event.stanza;
	remove_handler_for(stanza.attr.to, stanza.attr.from);
	session.send(build_reply(stanza, "failure", "aborted"));
	return true;
end);
