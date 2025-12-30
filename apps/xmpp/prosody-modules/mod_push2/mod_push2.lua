local os_time = os.time;
local st = require"util.stanza";
local jid = require"util.jid";
local hashes = require"util.hashes";
local random = require"util.random";
local watchdog = require "util.watchdog";
local uuid = require "util.uuid";
local base64 = require "util.encodings".base64;
local crypto = require "util.crypto";
local jwt = require "util.jwt";

pcall(function() module:depends("track_muc_joins") end)

local xmlns_push = "urn:xmpp:push2:0";

-- configuration
local contact_uri = module:get_option_string("contact_uri", "xmpp:" .. module.host)
local extended_hibernation_timeout = module:get_option_number("push_max_hibernation_timeout", 72*3600)  -- use same timeout like ejabberd
local hibernate_past_first_push = module:get_option_boolean("hibernate_past_first_push", true)

local host_sessions = prosody.hosts[module.host].sessions
local push2_registrations = module:open_store("push2_registrations", "keyval")

if _VERSION:match("5%.1") or _VERSION:match("5%.2") then
	module:log("warn", "This module may behave incorrectly on Lua before 5.3. It is recommended to upgrade to a newer Lua version.")
end

local function account_dico_info(event)
	(event.reply or event.stanza):tag("feature", {var=xmlns_push}):up()
end
module:hook("account-disco-info", account_dico_info);

local function parse_match(matchel)
		local match = { match = matchel.attr.profile, chats = {} }

		for chatel in matchel:childtags("filter") do
			local chat = {}
			if chatel:get_child("mention") then
				chat.mention = true
			end
			if chatel:get_child("reply") then
				chat.reply = true
			end
			match.chats[chatel.attr.jid] = chat
		end

		match.grace = matchel:get_child_text("grace")
		if match.grace then match.grace = tonumber(match.grace) end

		local send = matchel:get_child("send", "urn:xmpp:push2:send:notify-only:0")
		if send then
			match.send = send.attr.xmlns
			return match
		end

		send = matchel:get_child("send", "urn:xmpp:push2:send:sce+rfc8291+rfc8292:0")
		if send then
			match.send = send.attr.xmlns
			match.ua_public = send:get_child_text("ua-public")
			match.auth_secret = send:get_child_text("auth-secret")
			match.jwt_alg = send:get_child_text("jwt-alg")
			match.jwt_key = send:get_child_text("jwt-key")
			match.jwt_claims = {}
			for claim in send:childtags("jwt-claim") do
				match.jwt_claims[claim.attr.name] = claim:get_text()
			end
			return match
		end

		return nil
end

local function push_enable(event)
	local origin, stanza = event.origin, event.stanza;
	local enable = stanza.tags[1];
	origin.log("debug", "Attempting to enable push notifications")
	-- MUST contain a jid of the push service being enabled
	local service_jid = enable:get_child_text("service")
	-- MUST contain a string to identify the client fo the push service
	local client = enable:get_child_text("client")
	if not service_jid then
		origin.log("debug", "Push notification enable request missing service")
		origin.send(st.error_reply(stanza, "modify", "bad-request", "Missing service"))
		return true
	end
	if not client then
		origin.log("debug", "Push notification enable request missing client")
		origin.send(st.error_reply(stanza, "modify", "bad-request", "Missing client"))
		return true
	end
	if service_jid == stanza.attr.from then
		origin.log("debug", "Push notification enable request service JID identical to our own")
		origin.send(st.error_reply(stanza, "modify", "bad-request", "JID must be different from ours"))
		return true
	end
	local matches = {}
	for matchel in enable:childtags("match") do
		local match = parse_match(matchel)
		if match then
			matches[#matches + 1] = match
		end
	end
	-- Tie registration to client, via client_id with sasl2 or else fallback to resource
	local registration_id = origin.client_id or origin.resource
	local push_registration = {
		service = service_jid;
		client = client;
		timestamp = os_time();
		matches = matches;
	};
	-- TODO: can we move to keyval+ on trunk?
	local registrations = push2_registrations:get(origin.username) or {}
	registrations[registration_id] = push_registration
	if not push2_registrations:set(origin.username, registrations) then
		origin.send(st.error_reply(stanza, "wait", "internal-server-error"));
	else
		origin.push_registration_id = registration_id
		origin.push_registration = push_registration
		origin.first_hibernated_push = nil
		origin.log("info", "Push notifications enabled for %s (%s)", tostring(stanza.attr.from), tostring(service_jid))
		origin.send(st.reply(stanza))
	end
	return true
end
module:hook("iq-set/self/"..xmlns_push..":enable", push_enable)

local function push_disable(event)
	local origin, stanza = event.origin, event.stanza;
	local enable = stanza.tags[1];
	origin.log("debug", "Attempting to disable push notifications")
	-- Tie registration to client, via client_id with sasl2 or else fallback to resource
	local registration_id = origin.client_id or origin.resource
	-- TODO: can we move to keyval+ on trunk?
	local registrations = push2_registrations:get(origin.username) or {}
	registrations[registration_id] = nil
	if not push2_registrations:set(origin.username, registrations) then
		origin.send(st.error_reply(stanza, "wait", "internal-server-error"));
	else
		origin.push_registration_id = nil
		origin.push_registration = nil
		origin.first_hibernated_push = nil
		origin.log("info", "Push notifications disabled for %s (%s)", tostring(stanza.attr.from), registration_id)
		origin.send(st.reply(stanza))
	end
	return true
end
module:hook("iq-set/self/"..xmlns_push..":disable", push_disable)

-- urgent stanzas should be delivered without delay
local function is_voip(stanza)
	if stanza.name == "message" then
		if stanza:get_child("propose", "urn:xmpp:jingle-message:0") then
			return true, "jingle call"
		end

		if stanza:get_child("retract", "urn:xmpp:jingle-message:0") then
			return true, "jingle call retract"
		end
	end
end

local function has_body(stanza)
	-- We can't check for body contents in encrypted messages, so let's treat them as important
	-- Some clients don't even set a body or an empty body for encrypted messages

	-- check omemo https://xmpp.org/extensions/inbox/omemo.html
	if stanza:get_child("encrypted", "eu.siacs.conversations.axolotl") or stanza:get_child("encrypted", "urn:xmpp:omemo:0") then return true; end

	-- check xep27 pgp https://xmpp.org/extensions/xep-0027.html
	if stanza:get_child("x", "jabber:x:encrypted") then return true; end

	-- check xep373 pgp (OX) https://xmpp.org/extensions/xep-0373.html
	if stanza:get_child("openpgp", "urn:xmpp:openpgp:0") then return true; end

	local body = stanza:get_child_text("body");

	return body ~= nil and body ~= ""
end

-- is this push a high priority one
local function is_important(stanza, session)
	local is_voip_stanza, urgent_reason = is_voip(stanza)
	if is_voip_stanza then return true; end

	local st_name = stanza and stanza.name or nil
	if not st_name then return false; end -- nonzas are never important here
	if st_name == "presence" then
		return false; -- same for presences
	elseif st_name == "message" then
		-- unpack carbon copied message stanzas
		local carbon = stanza:find("{urn:xmpp:carbons:2}/{urn:xmpp:forward:0}/{jabber:client}message")
		local stanza_direction = carbon and stanza:child_with_name("sent") and "out" or "in"
		if carbon then stanza = carbon; end
		local st_type = stanza.attr.type

		-- headline message are always not important
		if st_type == "headline" then return false; end

		-- carbon copied outgoing messages are not important
		if carbon and stanza_direction == "out" then return false; end

		-- groupchat reflections are not important here
		if st_type == "groupchat" and session and session.rooms_joined then
			local muc = jid.bare(stanza.attr.from)
			local from_nick = jid.resource(stanza.attr.from)
			if from_nick == session.rooms_joined[muc] then
				return false
			end
		end

		-- edits are not imporatnt
		if stanza:get_child("replace", "urn:xmpp:message-correct:0") then
			return false
		end

		-- empty bodies are not important
		return has_body(stanza)
	end
	return false;		-- this stanza wasn't one of the above cases --> it is not important, too
end

local function add_sce_rfc8291(match, stanza, push_notification_payload)
	local max_data_size = 2847 -- https://github.com/web-push-libs/web-push-php/issues/108
	local stanza_clone = st.clone(stanza)
	stanza_clone.attr.xmlns = "jabber:client"
	local envelope = st.stanza("envelope", { xmlns = "urn:xmpp:sce:1" })
		:tag("content")
		:tag("forwarded", { xmlns = "urn:xmpp:forward:0" })
		:add_child(stanza_clone)
		:up():up():up()
	local envelope_bytes = tostring(envelope)
	if string.len(envelope_bytes) > max_data_size then
		-- If stanza is too big, remove extra elements
		stanza_clone:maptags(function(el)
			if el.attr.xmlns == nil or
				el.attr.xmlns == "jabber:client" or
				el.attr.xmlns == "jabber:x:oob" or
				(el.attr.xmlns == "urn:xmpp:sid:0" and el.name == "stanza-id") or
				el.attr.xmlns == "eu.siacs.conversations.axolotl" or
				el.attr.xmlns == "urn:xmpp:omemo:0" or
				el.attr.xmlns == "jabber:x:encrypted" or
				el.attr.xmlns == "urn:xmpp:openpgp:0" or
				el.attr.xmlns == "urn:xmpp:sce:1" or
				el.attr.xmlns == "urn:xmpp:jingle-message:0" or
				el.attr.xmlns == "jabber:x:conference"
			then
				return el
			else
				return nil
			end
		end)
		envelope_bytes = tostring(envelope)
	end
	if string.len(envelope_bytes) > max_data_size then
		local body = stanza:get_child_text("body")
		if body and string.len(body) > 50 then
			stanza_clone:maptags(function(el)
				if el.name == "body" then
					return nil
				else
					return el
				end
			end)

			body = string.gsub(string.gsub("\n" .. body, "\n>[^\n]*", ""), "^%s", "")
			stanza_clone:body(body:sub(1, utf8.offset(body, 50)) .. "…")
			envelope_bytes = tostring(envelope)
		end
	end
	if string.len(envelope_bytes) > max_data_size then
		-- If still too big, get aggressive
		stanza_clone:maptags(function(el)
			if el.name == "body" or
				(el.attr.xmlns == "urn:xmpp:sid:0" and el.name == "stanza-id") or
				el.attr.xmlns == "urn:xmpp:jingle-message:0" or
				el.attr.xmlns == "jabber:x:conference"
			then
				return el
			else
				return nil
			end
		end)
		envelope_bytes = tostring(envelope)
	end
	local padding_size = math.min(150, max_data_size/3 - string.len(envelope_bytes))
	if padding_size > 0 then
		envelope:text_tag("rpad", base64.encode(random.bytes(padding_size)))
		envelope_bytes = tostring(envelope)
	end

	local p256dh_raw = base64.decode(match.ua_public .. "==")
	local p256dh = crypto.import_public_ec_raw(p256dh_raw, "prime256v1")
	local one_time_key = crypto.generate_p256_keypair()
	local one_time_key_public = one_time_key:public_raw()
	local info = "WebPush: info\0" .. p256dh_raw .. one_time_key_public
	local auth_secret = base64.decode(match.auth_secret .. "==")
	local salt = random.bytes(16)
	local shared_secret = one_time_key:derive(p256dh)
	local ikm = hashes.hkdf_hmac_sha256(32, shared_secret, auth_secret, info)
	local key = hashes.hkdf_hmac_sha256(16, ikm, salt, "Content-Encoding: aes128gcm\0")
	local nonce = hashes.hkdf_hmac_sha256(12, ikm, salt, "Content-Encoding: nonce\0")
	local header = salt .. "\0\0\16\0" .. string.char(string.len(one_time_key_public)) .. one_time_key_public
	local encrypted = crypto.aes_128_gcm_encrypt(key, nonce, envelope_bytes .. "\2")

	push_notification_payload
		:tag("encrypted", { xmlns = "urn:xmpp:sce:rfc8291:0" })
		:text_tag("payload", base64.encode(header .. encrypted))
		:up()
end

local function add_rfc8292(match, stanza, push_notification_payload)
	if not match.jwt_alg then return; end
	local key = match.jwt_key
	if match.jwt_alg ~= "HS256" then
		-- keypairs are in PKCS#8 PEM format without header/footer
		key = "-----BEGIN PRIVATE KEY-----\n"..key.."\n-----END PRIVATE KEY-----"
	end

	local public_key = crypto.import_private_pem(key):public_raw()
	local signer = jwt.new_signer(match.jwt_alg, key)
	local payload = {}
	for k, v in pairs(match.jwt_claims or {}) do
		payload[k] = v
	end
	payload.sub = contact_uri
	push_notification_payload:text_tag("jwt", signer(payload), { key = base64.encode(public_key) })
end

local function handle_notify_request(stanza, node, user_push_services, session, log_push_decline)
	local pushes = 0;
	if not #user_push_services then return pushes end

	local notify_push_services = {};
	if is_important(stanza, session) then
		notify_push_services = user_push_services
	else
		for identifier, push_info in pairs(user_push_services) do
			for _, match in ipairs(push_info.matches) do
				if match.match == "urn:xmpp:push2:match:important" then
					module:log("debug", "Not pushing because not important")
				else
					notify_push_services[identifier] = push_info;
				end
			end
		end
	end

	for push_registration_id, push_info in pairs(notify_push_services) do
		local send_push = true;		-- only send push to this node when not already done for this stanza or if no stanza is given at all
		if stanza then
			if not stanza._push_notify2 then stanza._push_notify2 = {}; end
			if stanza._push_notify2[push_registration_id] then
				if log_push_decline then
					module:log("debug", "Already sent push notification for %s@%s to %s (%s)", node, module.host, push_info.jid, tostring(push_info.node));
				end
				send_push = false;
			end
			stanza._push_notify2[push_registration_id] = true;
		end

		if send_push then
			local any_match = false;
			local push_notification_payload = st.stanza("notification", { xmlns = xmlns_push })
			push_notification_payload:text_tag("client", push_info.client)
			push_notification_payload:text_tag("priority", is_voip(stanza) and "high" or (is_important(stanza, session) and "normal" or "low"))
			if is_voip(stanza) then
				push_notification_payload:tag("voip"):up()
			end

			local sends_added = {};
			for _, match in ipairs(push_info.matches) do
				local does_match = false;
				if match.match == "urn:xmpp:push2:match:all" then
					does_match = true
				elseif match.match == "urn:xmpp:push2:match:important" then
					does_match = is_important(stanza, session)
				elseif match.match == "urn:xmpp:push2:match:archived" then
					does_match = stanza:get_child("stana-id", "urn:xmpp:sid:0")
				elseif match.match == "urn:xmpp:push2:match:archived-with-body" then
					does_match = stanza:get_child("stana-id", "urn:xmpp:sid:0") and has_body(stanza)
				end

				local to_user, to_host = jid.split(stanza.attr.to)
				to_user = to_user or session.username
				to_host = to_host or module.host

				-- If another session has recent activity within configured grace period, don't send push
				if does_match and match.grace and not is_voip(stanza) and to_host == module.host and host_sessions[to_user] then
					local now = os_time()
					for _, session in pairs(host_sessions[to_user].sessions) do
						if session.last_activity and session.push_registration_id ~= push_registration_id and (now - session.last_activity) < match.grace then
							does_match = false
						end
					end
				end

				local chat = match.chats and (match.chats[stanza.attr.from] or match.chats[jid.bare(stanza.attr.from)] or match.chats[jid.host(stanza.attr.from)])
				if does_match and chat then
					does_match = false

					local nick = (session.rooms_joined and session.rooms_joined[jid.bare(stanza.attr.from)]) or to_user

					if not does_match and chat.mention then
						local body = stanza:get_child_text("body")
						if body and body:find(nick, 1, true) then
							does_match = true
						end
					end
					if not does_match and chat.reply then
						local reply = stanza:get_child("reply", "urn:xmpp:reply:0")
						if reply and (reply.attr.to == to_user.."@"..to_host or (jid.bare(reply.attr.to) == jid.bare(stanza.attr.from) and jid.resource(reply.attr.to) == nick)) then
							does_match = true
						end
					end
				end

				if does_match and not sends_added[match.send] then
					sends_added[match.send] = true
					any_match = true
					if match.send == "urn:xmpp:push2:send:notify-only" then
						-- Nothing more to add
					elseif match.send == "urn:xmpp:push2:send:sce+rfc8291+rfc8292:0" then
						add_sce_rfc8291(match, stanza, push_notification_payload)
						add_rfc8292(match, stanza, push_notification_payload)
					else
						module:log("debug", "Unkonwn send profile: " .. push_info.send)
					end
				end
			end

			if any_match then
				local push_publish = st.message({ to = push_info.service, from = module.host, id = uuid.generate() })
					:add_child(push_notification_payload):up()

				-- TODO: watch for message error replies and count or something
				module:send(push_publish)
				pushes = pushes + 1
			end
		end
	end

	return pushes
end

-- small helper function to extract relevant push settings
local function get_push_settings(stanza, session)
	local to = stanza.attr.to
	local node = to and jid.split(to) or session.username
	local user_push_services = push2_registrations:get(node)
	return node, (user_push_services or {})
end

-- publish on offline message
module:hook("message/offline/handle", function(event)
	local node, user_push_services = get_push_settings(event.stanza, event.origin);
	module:log("debug", "Invoking handle_notify_request() for offline stanza");
	handle_notify_request(event.stanza, node, user_push_services, event.origin, true);
end, 1);

-- publish on bare groupchat
-- this picks up MUC messages when there are no devices connected
module:hook("message/bare/groupchat", function(event)
	local node, user_push_services = get_push_settings(event.stanza, event.origin);
	local notify_push_services = {};
	for identifier, push_info in pairs(user_push_services) do
		for _, match in ipairs(push_info.matches) do
			if match.match == "urn:xmpp:push2:match:archived-with-body" or match.match == "urn:xmpp:push2:match:archived" then
				module:log("debug", "Not pushing because we are not archiving this stanza")
			else
				notify_push_services[identifier] = push_info;
			end
		end
	end

	handle_notify_request(event.stanza, node, notify_push_services, event.origin, true);
end, 1);

local function process_stanza_queue(queue, session, queue_type)
	if not session.push_registration_id then return; end
	local notified = { unimportant = false; important = false }
	for i=1, #queue do
		local stanza = queue[i];
		-- fast ignore of already pushed stanzas
		if stanza and not (stanza._push_notify2 and stanza._push_notify2[session.push_registration_id]) then
			local node, all_push_services = get_push_settings(stanza, session)
			local user_push_services = {[session.push_registration_id] = all_push_services[session.push_registration_id]}
			local stanza_type = "unimportant";
			if is_important(stanza, session) then stanza_type = "important"; end
			if not notified[stanza_type] then		-- only notify if we didn't try to push for this stanza type already
				if handle_notify_request(stanza, node, user_push_services, session, false) ~= 0 then
					if session.hibernating and not session.first_hibernated_push then
						-- if the message was important
						-- then record the time of first push in the session for the smack module which will extend its hibernation
						-- timeout based on the value of session.first_hibernated_push
						if is_important(stanza, session) and not hibernate_past_first_push then
							session.first_hibernated_push = os_time();
							-- check for prosody 0.12 mod_smacks
							if session.hibernating_watchdog and session.original_smacks_callback and session.original_smacks_timeout then
								-- restore old smacks watchdog (--> the start of our original timeout will be delayed until first push)
								session.hibernating_watchdog:cancel();
								session.hibernating_watchdog = watchdog.new(session.original_smacks_timeout, session.original_smacks_callback);
							end
						end
					end
					notified[stanza_type] = true
				end
			end
		end
		if notified.unimportant and notified.important then break; end		-- stop processing the queue if all push types are exhausted
	end
end

-- publish on unacked smacks message (use timer to send out push for all stanzas submitted in a row only once)
local function process_stanza(session, stanza)
	if session.push_registration_id then
		session.log("debug", "adding new stanza to push_queue");
		if not session.push_queue then session.push_queue = {}; end
		local queue = session.push_queue;
		queue[#queue+1] = st.clone(stanza);
		if not session.awaiting_push_timer then		-- timer not already running --> start new timer
			session.awaiting_push_timer = module:add_timer(1.0, function ()
				process_stanza_queue(session.push_queue, session, "push");
				session.push_queue = {};		-- clean up queue after push
				session.awaiting_push_timer = nil;
			end);
		end
	end
	return stanza;
end

local function process_smacks_stanza(event)
	local session = event.origin;
	local stanza = event.stanza;
	if not session.push_registration_id then
		session.log("debug", "NOT invoking handle_notify_request() for newly smacks queued stanza (session.push_registration_id is not set: %s)",
			session.push_registration_id
		);
	else
		process_stanza(session, stanza)
	end
end

-- smacks hibernation is started
local function hibernate_session(event)
	local session = event.origin;
	local queue = event.queue;
	session.first_hibernated_push = nil;
	if session.push_registration_id and session.hibernating_watchdog then -- check for prosody 0.12 mod_smacks
		-- save old watchdog callback and timeout
		session.original_smacks_callback = session.hibernating_watchdog.callback;
		session.original_smacks_timeout = session.hibernating_watchdog.timeout;
		-- cancel old watchdog and create a new watchdog with extended timeout
		session.hibernating_watchdog:cancel();
		session.hibernating_watchdog = watchdog.new(extended_hibernation_timeout, function()
			session.log("debug", "Push-extended smacks watchdog triggered");
			if session.original_smacks_callback then
				session.log("debug", "Calling original smacks watchdog handler");
				session.original_smacks_callback();
			end
		end);
	end
	-- process unacked stanzas
	process_stanza_queue(queue, session, "smacks");
end

-- smacks hibernation is ended
local function restore_session(event)
	local session = event.resumed;
	if session then		-- older smacks module versions send only the "intermediate" session in event.session and no session.resumed one
		if session.awaiting_push_timer then
			session.awaiting_push_timer:stop();
			session.awaiting_push_timer = nil;
		end
		session.first_hibernated_push = nil;
		-- the extended smacks watchdog will be canceled by the smacks module, no need to anything here
	end
end

-- smacks ack is delayed
local function ack_delayed(event)
	local session = event.origin;
	local queue = event.queue;
	local stanza = event.stanza;
	if not session.push_registration_id then return; end
	if stanza then process_stanza(session, stanza); return; end		-- don't iterate through smacks queue if we know which stanza triggered this
	for i=1, #queue do
		local queued_stanza = queue[i];
		-- process unacked stanzas (handle_notify_request() will only send push requests for new stanzas)
		process_stanza(session, queued_stanza);
	end
end

-- archive message added
local function archive_message_added(event)
	-- event is: { origin = origin, stanza = stanza, for_user = store_user, id = id }
	-- only notify for new mam messages when at least one device is online
	if not event.for_user or not host_sessions[event.for_user] then return; end
	-- Note that the stanza in the event is a clone not the same as other hooks, so dedupe doesn't work
	-- This is a problem if you wan to to also hook offline message storage for example
	local stanza = st.clone(event.stanza)
	stanza:tag("stanza-id", { xmlns = "urn:xmpp:sid:0", by = event.for_user.."@"..module.host, id = event.id }):up()
	local user_session = host_sessions[event.for_user] and host_sessions[event.for_user].sessions or {}
	local to = stanza.attr.to
	local to_user, to_host = jid.split(to)
	to_user = to_user or event.origin.username
	to_host = to_host or module.host

	-- only notify if the stanza destination is the mam user we store it for
	if event.for_user == to_user and to_host == module.host then
		local user_push_services = push2_registrations:get(to_user) or {}

		-- Urgent stanzas are time-sensitive (e.g. calls) and should
		-- be pushed immediately to avoid getting stuck in the smacks
		-- queue in case of dead connections, for example
		local is_voip_stanza, urgent_reason = is_voip(stanza);

		local notify_push_services;
		if is_voip_stanza then
			module:log("debug", "Urgent push for %s@%s (%s)", to_user, to_host, urgent_reason);
			notify_push_services = user_push_services;
		else
			-- only notify nodes with no active sessions (smacks is counted as active and handled separate)
			notify_push_services = {};
			for identifier, push_info in pairs(user_push_services) do
				local identifier_found = nil;
				for _, session in pairs(user_session) do
					if session.push_registration_id == identifier then
						identifier_found = session;
						break;
					end
				end
				if identifier_found then
					module:log("debug", "Not pushing '%s' of new MAM stanza (session still alive)", identifier)
				else
					notify_push_services[identifier] = push_info
				end
			end
		end

		handle_notify_request(stanza, to_user, notify_push_services, event.origin, true);
	end
end

module:hook("smacks-hibernation-start", hibernate_session);
module:hook("smacks-hibernation-end", restore_session);
module:hook("smacks-ack-delayed", ack_delayed);
module:hook("smacks-hibernation-stanza-queued", process_smacks_stanza);
module:hook("archive-message-added", archive_message_added);

local function track_activity(event)
	if has_body(event.stanza) or event.stanza:child_with_ns("http://jabber.org/protocol/chatstates") then
		event.origin.last_activity = os_time()
	end
end

module:hook("pre-message/bare", track_activity)
module:hook("pre-message/full", track_activity)

module:log("info", "Module loaded");
function module.unload()
	module:log("info", "Unloading module");
	-- cleanup some settings, reloading this module can cause process_smacks_stanza() to stop working otherwise
	for user, _ in pairs(host_sessions) do
		for _, session in pairs(host_sessions[user].sessions) do
			if session.awaiting_push_timer then session.awaiting_push_timer:stop(); end
			session.awaiting_push_timer = nil;
			session.push_queue = nil;
			session.first_hibernated_push = nil;
			-- check for prosody 0.12 mod_smacks
			if session.hibernating_watchdog and session.original_smacks_callback and session.original_smacks_timeout then
				-- restore old smacks watchdog
				session.hibernating_watchdog:cancel();
				session.hibernating_watchdog = watchdog.new(session.original_smacks_timeout, session.original_smacks_callback);
			end
		end
	end
	module:log("info", "Module unloaded");
end
