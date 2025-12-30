local jid = require "util.jid";
local json = require "util.json";
local promise = require "util.promise";
local st = require "util.stanza";
local uuid = require "util.uuid";

local xmlns_cmd = "http://jabber.org/protocol/commands";

module:hook("muc-disco#info", function(event)
	event.reply:tag("feature", {var = xmlns_cmd}):up();
end);

module:hook("iq-get/bare/http://jabber.org/protocol/disco#items:query", function (event)
	local room = prosody.hosts[module:get_host()].modules.muc.get_room_from_jid(event.stanza.attr.to);
	local occupant = room:get_occupant_by_real_jid(event.stanza.attr.from)
	if event.stanza.tags[1].attr.node ~= xmlns_cmd or not occupant then
		return
	end

	local bots = module:get_option_array("adhoc_bots", {})
	bots:map(function(bot)
		return module:send_iq(
			st.iq({ type = "get", id = uuid.generate(), to = bot, from = room:get_occupant_jid(event.stanza.attr.from) })
				:tag("query", { xmlns = "http://jabber.org/protocol/disco#items", node = xmlns_cmd }):up(),
			nil,
			5
		)
	end)

	promise.all_settled(bots):next(function (bot_commands)
		local reply = st.reply(event.stanza):query("http://jabber.org/protocol/disco#items")
		for i, one_bot_reply in ipairs(bot_commands) do
			if one_bot_reply.status == "fulfilled"	then
			local query = one_bot_reply.value.stanza:get_child("query", "http://jabber.org/protocol/disco#items")
				if query then
					-- Should use query:childtags("item") but it doesn't work
					for j,item in ipairs(query.tags) do
						item.attr.node = json.encode({ jid = item.attr.jid, node = item.attr.node })
						item.attr.jid = event.stanza.attr.to
						reply:add_child(item)
					end
				end
			end
		end
		event.origin.send(reply:up())
	end):catch(function (e)
		module:log("error", e)
	end)

	return true;
end, 500);

local function is_adhoc_bot(jid)
	for i, bot_jid in ipairs(module:get_option_array("adhoc_bots", {})) do
		if jid == bot_jid then
			return true
		end
	end

	return false
end

module:hook("iq-set/bare/"..xmlns_cmd..":command", function (event)
	local origin, stanza = event.origin, event.stanza;
	local node = stanza.tags[1].attr.node
	local meta = json.decode(node)
	local room = prosody.hosts[module:get_host()].modules.muc.get_room_from_jid(stanza.attr.to);
	local occupant = room:get_occupant_by_real_jid(event.stanza.attr.from)
	if meta and occupant and is_adhoc_bot(meta.jid) then
		local fwd = st.clone(stanza)
		fwd.attr.to = meta.jid
		fwd.attr.from = room:get_occupant_jid(event.stanza.attr.from)
		local command = fwd:get_child("command", "http://jabber.org/protocol/commands")
		command.attr.node = meta.node
		module:send_iq(fwd):next(function(response)
			local response_command = response.stanza:get_child("command", "http://jabber.org/protocol/commands")
			response.stanza.attr.from = stanza.attr.to
			response.stanza.attr.to = stanza.attr.from
			response_command.attr.node = node
			origin.send(response.stanza)
		end):catch(function (e)
			module:log("error", e)
		end)

		return true
	end

	return
end, 500);

local function clean_xmlns(node)
		-- Recursively remove "jabber:client" attribute from node.
		-- In Prosody internal routing, xmlns should not be set.
		-- Keeping xmlns would lead to issues like mod_smacks ignoring the outgoing stanza,
		-- so we remove all xmlns attributes with a value of "jabber:client"
		if node.attr.xmlns == 'jabber:client' then
				for childnode in node:childtags() do
						clean_xmlns(childnode)
				end
				node.attr.xmlns = nil
		end
end

module:hook("message/bare", function (event)
	local origin, stanza = event.origin, event.stanza;
	if not is_adhoc_bot(stanza.attr.from) then return; end
	local room = prosody.hosts[module:get_host()].modules.muc.get_room_from_jid(stanza.attr.to);
	if room == nil then return; end
	local privilege = stanza:get_child("privilege", "urn:xmpp:privilege:2")
	if privilege == nil then return; end
	local fwd = privilege:get_child("forwarded", "urn:xmpp:forward:0")
	if fwd == nil then return; end
	local message = fwd:get_child("message", "jabber:client")
	if message == nil then return; end
	if message.attr.to ~= stanza.attr.to or jid.bare(message.attr.from) ~= stanza.attr.to then
		return
	end

	clean_xmlns(message)
	room:broadcast_message(message)
	return true
end)
