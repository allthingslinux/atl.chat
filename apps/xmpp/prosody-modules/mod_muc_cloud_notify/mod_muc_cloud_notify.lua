-- XEP-XXX: MUC Push Notifications
-- Copyright (C) 2015-2016 Kim Alvefur
-- Copyright (C) 2017-2018 Thilo Molitor
--
-- This file is MIT/X11 licensed.

local s_match = string.match;
local s_sub = string.sub;
local os_time = os.time;
local next = next;
local st = require"util.stanza";
local jid = require"util.jid";
local dataform = require"util.dataforms".new;
local hashes = require"util.hashes";

local xmlns_push = "urn:xmpp:push:0";

-- configuration
local include_body = module:get_option_boolean("push_notification_with_body", false);
local include_sender = module:get_option_boolean("push_notification_with_sender", false);
local max_push_errors = module:get_option_number("push_max_errors", 16);
local max_push_devices = module:get_option_number("push_max_devices", 5);
local dummy_body = module:get_option_string("push_notification_important_body", "New Message!");

local host_sessions = prosody.hosts[module.host].sessions;
local push_errors = {};
local id2node = {};

module:depends("muc");

-- ordered table iterator, allow to iterate on the natural order of the keys of a table,
-- see http://lua-users.org/wiki/SortedIteration
local function __genOrderedIndex( t )
	local orderedIndex = {}
	for key in pairs(t) do
		table.insert( orderedIndex, key )
	end
	-- sort in reverse order (newest one first)
	table.sort( orderedIndex, function(a, b)
		if a == nil or t[a] == nil or b == nil or t[b] == nil then return false end
		-- only one timestamp given, this is the newer one
		if t[a].timestamp ~= nil and t[b].timestamp == nil then return true end
		if t[a].timestamp == nil and t[b].timestamp ~= nil then return false end
		-- both timestamps given, sort normally
		if t[a].timestamp ~= nil and t[b].timestamp ~= nil then return t[a].timestamp > t[b].timestamp end
		return false	-- normally not reached
	end)
	return orderedIndex
end
local function orderedNext(t, state)
	-- Equivalent of the next function, but returns the keys in timestamp
	-- order. We use a temporary ordered key table that is stored in the
	-- table being iterated.

	local key = nil
	--print("orderedNext: state = "..tostring(state) )
	if state == nil then
		-- the first time, generate the index
		t.__orderedIndex = __genOrderedIndex( t )
		key = t.__orderedIndex[1]
	else
		-- fetch the next value
		for i = 1, #t.__orderedIndex do
			if t.__orderedIndex[i] == state then
				key = t.__orderedIndex[i+1]
			end
		end
	end

	if key then
		return key, t[key]
	end

	-- no more value to return, cleanup
	t.__orderedIndex = nil
	return
end
local function orderedPairs(t)
	-- Equivalent of the pairs() function on tables. Allows to iterate
	-- in order
	return orderedNext, t, nil
end

-- small helper function to return new table with only "maximum" elements containing only the newest entries
local function reduce_table(table, maximum)
	local count = 0;
	local result = {};
	for key, value in orderedPairs(table) do
		count = count + 1;
		if count > maximum then break end
		result[key] = value;
	end
	return result;
end

-- For keeping state across reloads while caching reads
local push_store = (function()
	local store = module:open_store();
	local push_services = {};
	local api = {};
	function api:get(user)
		if not push_services[user] then
			local err;
			push_services[user], err = store:get(user);
			if not push_services[user] and err then
				module:log("warn", "Error reading push notification storage for user '%s': %s", user, tostring(err));
				push_services[user] = {};
				return push_services[user], false;
			end
		end
		if not push_services[user] then push_services[user] = {} end
		return push_services[user], true;
	end
	function api:set(user, data)
		push_services[user] = reduce_table(data, max_push_devices);
		local ok, err = store:set(user, push_services[user]);
		if not ok then
			module:log("error", "Error writing push notification storage for user '%s': %s", user, tostring(err));
			return false;
		end
		return true;
	end
	function api:set_identifier(user, push_identifier, data)
		local services = self:get(user);
		services[push_identifier] = data;
		return self:set(user, services);
	end
	return api;
end)();


-- Forward declarations, as both functions need to reference each other
local handle_push_success, handle_push_error;

function handle_push_error(event)
	local stanza = event.stanza;
	local error_type, condition = stanza:get_error();
	local node = id2node[stanza.attr.id];
	if node == nil then return false; end		-- unknown stanza? Ignore for now!
	local from = stanza.attr.from;
	local user_push_services = push_store:get(node);
	local changed = false;
	
	for push_identifier, _ in pairs(user_push_services) do
		local stanza_id = hashes.sha256(push_identifier, true);
		if stanza_id == stanza.attr.id then
			if user_push_services[push_identifier] and user_push_services[push_identifier].jid == from and error_type ~= "wait" then
				push_errors[push_identifier] = push_errors[push_identifier] + 1;
				module:log("info", "Got error of type '%s' (%s) for identifier '%s': "
					.."error count for this identifier is now at %s", error_type, condition, push_identifier,
					tostring(push_errors[push_identifier]));
				if push_errors[push_identifier] >= max_push_errors then
					module:log("warn", "Disabling push notifications for identifier '%s'", push_identifier);
					-- remove push settings from sessions
					if host_sessions[node] then
						for _, session in pairs(host_sessions[node].sessions) do
							if session.push_identifier == push_identifier then
								session.push_identifier = nil;
								session.push_settings = nil;
								session.first_hibernated_push = nil;
							end
						end
					end
					-- save changed global config
					changed = true;
					user_push_services[push_identifier] = nil
					push_errors[push_identifier] = nil;
					-- unhook iq handlers for this identifier (if possible)
					if module.unhook then
						module:unhook("iq-error/host/"..stanza_id, handle_push_error);
						module:unhook("iq-result/host/"..stanza_id, handle_push_success);
						id2node[stanza_id] = nil;
					end
				end
			elseif user_push_services[push_identifier] and user_push_services[push_identifier].jid == from and error_type == "wait" then
				module:log("debug", "Got error of type '%s' (%s) for identifier '%s': "
					.."NOT increasing error count for this identifier", error_type, condition, push_identifier);
			end
		end
	end
	if changed then
		push_store:set(node, user_push_services);
	end
	return true;
end

function handle_push_success(event)
	local stanza = event.stanza;
	local node = id2node[stanza.attr.id];
	if node == nil then return false; end		-- unknown stanza? Ignore for now!
	local from = stanza.attr.from;
	local user_push_services = push_store:get(node);
	
	for push_identifier, _ in pairs(user_push_services) do
		if hashes.sha256(push_identifier, true) == stanza.attr.id then
			if user_push_services[push_identifier] and user_push_services[push_identifier].jid == from and push_errors[push_identifier] > 0 then
				push_errors[push_identifier] = 0;
				module:log("debug", "Push succeeded, error count for identifier '%s' is now at %s again", push_identifier, tostring(push_errors[push_identifier]));
			end
		end
	end
	return true;
end

-- http://xmpp.org/extensions/xep-0357.html#disco
local function account_dico_info(event)
	(event.reply or event.stanza):tag("feature", {var=xmlns_push}):up();
end
module:hook("account-disco-info", account_dico_info);

-- http://xmpp.org/extensions/xep-0357.html#enabling
local function push_enable(event)
	local origin, stanza = event.origin, event.stanza;
	local enable = stanza.tags[1];
	origin.log("debug", "Attempting to enable push notifications");
	-- MUST contain a 'jid' attribute of the XMPP Push Service being enabled
	local push_jid = enable.attr.jid;
	-- SHOULD contain a 'node' attribute
	local push_node = enable.attr.node;
	-- CAN contain a 'include_payload' attribute
	local include_payload = enable.attr.include_payload;
	if not push_jid then
		origin.log("debug", "MUC Push notification enable request missing the 'jid' field");
		origin.send(st.error_reply(stanza, "modify", "bad-request", "Missing jid"));
		return true;
	end
	local publish_options = enable:get_child("x", "jabber:x:data");
	if not publish_options then
		-- Could be intentional
		origin.log("debug", "No publish options in request");
	end
	local push_identifier = push_jid .. "<" .. (push_node or "");
	local push_service = {
		jid = push_jid;
		node = push_node;
		include_payload = include_payload;
		options = publish_options and st.preserialize(publish_options);
		timestamp = os_time();
	};
	local ok = push_store:set_identifier(origin.username.."@"..origin.host, push_identifier, push_service);
	if not ok then
		origin.send(st.error_reply(stanza, "wait", "internal-server-error"));
	else
		origin.push_identifier = push_identifier;
		origin.push_settings = push_service;
		origin.first_hibernated_push = nil;
		origin.log("info", "MUC Push notifications enabled for %s by %s (%s)",
			 tostring(stanza.attr.to),
			 tostring(stanza.attr.from),
			 tostring(origin.push_identifier)
			);
		origin.send(st.reply(stanza));
	end
	return true;
end
module:hook("iq-set/host/"..xmlns_push..":enable", push_enable);


-- http://xmpp.org/extensions/xep-0357.html#disabling
local function push_disable(event)
	local origin, stanza = event.origin, event.stanza;
	local push_jid = stanza.tags[1].attr.jid; -- MUST include a 'jid' attribute
	local push_node = stanza.tags[1].attr.node; -- A 'node' attribute MAY be included
	if not push_jid then
		origin.send(st.error_reply(stanza, "modify", "bad-request", "Missing jid"));
		return true;
	end
	local user_push_services = push_store:get(origin.username);
	for key, push_info in pairs(user_push_services) do
		if push_info.jid == push_jid and (not push_node or push_info.node == push_node) then
			origin.log("info", "Push notifications disabled (%s)", tostring(key));
			if origin.push_identifier == key then
				origin.push_identifier = nil;
				origin.push_settings = nil;
				origin.first_hibernated_push = nil;
			end
			user_push_services[key] = nil;
			push_errors[key] = nil;
			if module.unhook then
				module:unhook("iq-error/host/"..key, handle_push_error);
				module:unhook("iq-result/host/"..key, handle_push_success);
				id2node[key] = nil;
			end
		end
	end
	local ok = push_store:set(origin.username, user_push_services);
	if not ok then
		origin.send(st.error_reply(stanza, "wait", "internal-server-error"));
	else
		origin.send(st.reply(stanza));
	end
	return true;
end
module:hook("iq-set/host/"..xmlns_push..":disable", push_disable);

-- Patched version of util.stanza:find() that supports giving stanza names
-- without their namespace, allowing for every namespace.
local function find(self, path)
	local pos = 1;
	local len = #path + 1;

	repeat
		local xmlns, name, text;
		local char = s_sub(path, pos, pos);
		if char == "@" then
			return self.attr[s_sub(path, pos + 1)];
		elseif char == "{" then
			xmlns, pos = s_match(path, "^([^}]+)}()", pos + 1);
		end
		name, text, pos = s_match(path, "^([^@/#]*)([/#]?)()", pos);
		name = name ~= "" and name or nil;
		if pos == len then
			if text == "#" then
				local child = xmlns ~= nil and self:get_child(name, xmlns) or self:child_with_name(name);
				return child and child:get_text() or nil;
			end
			return xmlns ~= nil and self:get_child(name, xmlns) or self:child_with_name(name);
		end
		self = xmlns ~= nil and self:get_child(name, xmlns) or self:child_with_name(name);
	until not self
	return nil;
end

-- is this push a high priority one (this is needed for ios apps not using voip pushes)
local function is_important(stanza)
	local st_name = stanza and stanza.name or nil;
	if not st_name then return false; end	-- nonzas are never important here
	if st_name == "presence" then
		return false;						-- same for presences
	elseif st_name == "message" then
		-- unpack carbon copies
		local stanza_direction = "in";
		local carbon;
		local st_type;
		-- support carbon copied message stanzas having an arbitrary message-namespace or no message-namespace at all
		if not carbon then carbon = find(stanza, "{urn:xmpp:carbons:2}/forwarded/message"); end
		if not carbon then carbon = find(stanza, "{urn:xmpp:carbons:1}/forwarded/message"); end
		stanza_direction = carbon and stanza:child_with_name("sent") and "out" or "in";
		if carbon then stanza = carbon; end
		st_type = stanza.attr.type;
		
		-- headline message are always not important
		if st_type == "headline" then return false; end
		
		-- carbon copied outgoing messages are not important
		if carbon and stanza_direction == "out" then return false; end
		
		-- We can't check for body contents in encrypted messages, so let's treat them as important
		-- Some clients don't even set a body or an empty body for encrypted messages
		
		-- check omemo https://xmpp.org/extensions/inbox/omemo.html
		if stanza:get_child("encrypted", "eu.siacs.conversations.axolotl") or stanza:get_child("encrypted", "urn:xmpp:omemo:0") then return true; end
		
		-- check xep27 pgp https://xmpp.org/extensions/xep-0027.html
		if stanza:get_child("x", "jabber:x:encrypted") then return true; end
		
		-- check xep373 pgp (OX) https://xmpp.org/extensions/xep-0373.html
		if stanza:get_child("openpgp", "urn:xmpp:openpgp:0") then return true; end
		
		local body = stanza:get_child_text("body");
		if st_type == "groupchat" and stanza:get_child_text("subject") then return false; end		-- groupchat subjects are not important here
		return body ~= nil and body ~= "";			-- empty bodies are not important
	end
	return false;		-- this stanza wasn't one of the above cases --> it is not important, too
end

local push_form = dataform {
	{ name = "FORM_TYPE"; type = "hidden"; value = "urn:xmpp:push:summary"; };
	{ name = "message-count"; type = "text-single"; };
	{ name = "pending-subscription-count"; type = "text-single"; };
	{ name = "last-message-sender"; type = "jid-single"; };
	{ name = "last-message-body"; type = "text-single"; };
};

-- http://xmpp.org/extensions/xep-0357.html#publishing
local function handle_notify_request(stanza, node, user_push_services, log_push_decline)
	local pushes = 0;
	if not user_push_services or next(user_push_services) == nil then return pushes end

	-- XXX: customized
	local body = stanza:get_child_text("body");
	if not body then
		return pushes;
	end
	
	for push_identifier, push_info in pairs(user_push_services) do
		local send_push = true;		-- only send push to this node when not already done for this stanza or if no stanza is given at all
		if stanza then
			if not stanza._push_notify then stanza._push_notify = {}; end
			if stanza._push_notify[push_identifier] then
				if log_push_decline then
					module:log("debug", "Already sent push notification for %s@%s to %s (%s)", node, module.host, push_info.jid, tostring(push_info.node));
				end
				send_push = false;
			end
			stanza._push_notify[push_identifier] = true;
		end
		
		if send_push then
			-- construct push stanza
			local stanza_id = hashes.sha256(push_identifier, true);
			local push_publish = st.iq({ to = push_info.jid, from = module.host, type = "set", id = stanza_id })
				:tag("pubsub", { xmlns = "http://jabber.org/protocol/pubsub" })
					:tag("publish", { node = push_info.node })
						:tag("item")
							:tag("notification", { xmlns = xmlns_push });
			local form_data = {
				-- hardcode to 1 because other numbers are just meaningless (the XEP does not specify *what exactly* to count)
				["message-count"] = "1";
			};
			if stanza and include_sender then
				form_data["last-message-sender"] = stanza.attr.from;
			end
			if stanza and include_body then
				form_data["last-message-body"] = stanza:get_child_text("body");
			elseif stanza and dummy_body and is_important(stanza) then
				form_data["last-message-body"] = tostring(dummy_body);
			end
			push_publish:add_child(push_form:form(form_data));
			push_publish:up(); -- / notification
			push_publish:up(); -- / publish
			push_publish:up(); -- / pubsub
			if push_info.options then
				push_publish:tag("publish-options"):add_child(st.deserialize(push_info.options));
			end
			-- send out push
			module:log("debug", "Sending%s push notification for %s@%s to %s (%s)", form_data["last-message-body"] and " important" or "", node, module.host, push_info.jid, tostring(push_info.node));
			-- module:log("debug", "PUSH STANZA: %s", tostring(push_publish));
			-- handle push errors for this node
			if push_errors[push_identifier] == nil then
				push_errors[push_identifier] = 0;
				module:hook("iq-error/host/"..stanza_id, handle_push_error);
				module:hook("iq-result/host/"..stanza_id, handle_push_success);
				id2node[stanza_id] = node;
			end
			module:send(push_publish);
			pushes = pushes + 1;
		end
	end
	return pushes;
end

local function extract_reference(text, i, j)
        -- COMPAT w/ pre-Lua 5.3
        local c, pos, p1 = 0, 0, nil;
        for char in text:gmatch("([%z\1-\127\194-\244][\128-\191]*)") do
                c, pos = c + 1, pos + #char;
                if not p1 and i < c then
                        p1 = pos;
                end
                if c == j then
                        return text:sub(p1, pos);
                end
        end
end

-- archive message added
local function archive_message_added(event)
	-- event is: { origin = origin, stanza = stanza, for_user = store_user, id = id }
	-- only notify for new mam messages when at least one device is online
	local room = event.room;
	local stanza = event.stanza;
	local body = stanza:get_child_text('body');

	for reference in stanza:childtags("reference", "urn:xmpp:reference:0") do
		local ref_begin, ref_end = tonumber(reference.attr['begin']), tonumber(reference.attr['end']);
		if reference.attr['type'] == 'mention' and ref_begin and ref_end then
			local nick = extract_reference(body, ref_begin, ref_end);
			local jid = room:get_registered_jid(nick);

			if room._occupants[room.jid..'/'..nick] then
				-- We only notify for members not currently in the room
				module:log("debug", "Not notifying %s, because he's currently in the room", jid);
			else
				-- We only need to notify once, even when there are multiple mentions.
				local user_push_services = push_store:get(jid);
				handle_notify_request(event.stanza, jid, user_push_services, true);
				return
			end
		end
	end
end

module:hook("muc-add-history", archive_message_added);

local function send_ping(event)
	local user = event.user;
	local user_push_services = push_store:get(user);
	local push_services = event.push_services or user_push_services;
	handle_notify_request(nil, user, push_services, true);
end
-- can be used by other modules to ping one or more (or all) push endpoints
module:hook("cloud-notify-ping", send_ping);

module:log("info", "Module loaded");
function module.unload()
	if module.unhook then
		module:unhook("account-disco-info", account_dico_info);
		module:unhook("iq-set/host/"..xmlns_push..":enable", push_enable);
		module:unhook("iq-set/host/"..xmlns_push..":disable", push_disable);

		module:unhook("muc-add-history", archive_message_added);
		module:unhook("cloud-notify-ping", send_ping);

		for push_identifier, _ in pairs(push_errors) do
			local stanza_id = hashes.sha256(push_identifier, true);
			module:unhook("iq-error/host/"..stanza_id, handle_push_error);
			module:unhook("iq-result/host/"..stanza_id, handle_push_success);
			id2node[stanza_id] = nil;
		end
	end

	module:log("info", "Module unloaded");
end
