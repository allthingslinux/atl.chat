module:set_global();

local mqtt = module:require "mqtt";
local id = require "util.id";
local st = require "util.stanza";

local function tostring_content(item)
	return tostring(item[1]);
end

local data_translators = setmetatable({
	utf8 = {
		from_item = function (item)
			return item:find("{https://prosody.im/protocol/data}data#");
		end;
		to_item = function (payload)
			return st.stanza("item", { xmlns = "http://jabber.org/protocol/pubsub", id = id.medium() })
				:text_tag("data", payload, { xmlns = "https://prosody.im/protocol/data" })
		end;
	};
	json = {
		from_item = function (item)
			return item:find("{urn:xmpp:json:0}json#");
		end;
		to_item = function (payload)
			return st.stanza("item", { xmlns = "http://jabber.org/protocol/pubsub", id = id.medium() })
				:text_tag("json", payload, { xmlns = "urn:xmpp:json:0" });
		end;
	};
	atom_title = {
		from_item = function (item)
			return item:find("{http://www.w3.org/2005/Atom}entry/title#");
		end;
		to_item = function (payload)
			return st.stanza("item", { xmlns = "http://jabber.org/protocol/pubsub", id = id.medium() })
				:tag("entry", { xmlns = "http://www.w3.org/2005/Atom" })
					:text_tag("title", payload, { type = "text" });
		end;
	};
}, {
	__index = function () return { from_item = tostring }; end;
});

local pubsub_services = {};
local pubsub_subscribers = {};
local packet_handlers = {};

function handle_packet(session, packet)
	module:log("debug", "MQTT packet received! Length: %d", packet.length);
	for k,v in pairs(packet) do
		module:log("debug", "MQTT %s: %s", tostring(k), tostring(v));
	end
	local handler = packet_handlers[packet.type];
	if not handler then
		module:log("warn", "Unhandled command: %s", tostring(packet.type));
		return;
	end
	handler(session, packet);
end

function packet_handlers.connect(session, packet)
	module:log("info", "MQTT client connected (sending connack)");
	module:log("debug", "MQTT version: %02x", packet.version);
	if packet.version ~= 0x04 then -- Version mismatch
		session.conn:write(mqtt.serialize_packet{
			type = "connack";
			data = string.char(0x00, 0x01);
		});
		return;
	end
	session.conn:write(mqtt.serialize_packet{
		type = "connack";
		data = string.char(0x00, 0x00);
	});
end

function packet_handlers.disconnect(session, packet)
	session.conn:close();
end

function packet_handlers.publish(session, packet)
	module:log("info", "PUBLISH to %s", packet.topic);
	local host, payload_type, node = packet.topic:match("^([^/]+)/([^/]+)/(.+)$");
	if not host then
		module:log("warn", "Invalid topic format - expected: HOST/TYPE/NODE");
		return;
	end
	local pubsub = pubsub_services[host];
	if not pubsub then
		module:log("warn", "Unable to locate host/node: %s", packet.topic);
		return;
	end

	local payload_translator = data_translators[payload_type];
	if not payload_translator or not payload_translator.to_item then
		module:log("warn", "Unsupported payload type '%s' on topic '%s'", payload_type, packet.topic);
		return;
	end

	local payload_item = payload_translator.to_item(packet.data);
	local ok, err = pubsub:publish(node, true, payload_item.attr.id, payload_item);
	if not ok then
		module:log("warn", "Error publishing MQTT data: %s", tostring(err));
	end
end

function packet_handlers.subscribe(session, packet)
	local results = {};
	for i, topic in ipairs(packet.topics) do
		module:log("info", "SUBSCRIBE to %s", topic);
		local host, payload_type, node = topic:match("^([^/]+)/([^/]+)/(.+)$");
		if not host then
			module:log("warn", "Invalid topic format - expected: HOST/TYPE/NODE");
			results[i] = 0x80; -- Failure
		else
			local pubsub = pubsub_subscribers[host];
			if not pubsub then
				module:log("warn", "Unable to locate host/node: %s", topic);
				results[i] = 0x80; -- Failure
			else
				local node_subs = pubsub[node];
				if not node_subs then
					node_subs = {};
					pubsub[node] = node_subs;
				end
				session.subscriptions[topic] = payload_type;
				node_subs[session] = payload_type;
				module:log("debug", "Successfully subscribed to %s", topic);
				results[i] = 0x00; -- Success
			end
		end
	end
	local ack = mqtt.serialize_packet{ type = "suback", id = packet.id, results = results };
	session.conn:write(ack);
end

function packet_handlers.pingreq(session, packet)
	session.conn:write(mqtt.serialize_packet{type = "pingresp"});
end

local sessions = {};

local mqtt_listener = {};

function mqtt_listener.onconnect(conn)
	sessions[conn] = {
		conn = conn;
		stream = mqtt.new_stream();
		subscriptions = {};
	};
end

function mqtt_listener.onincoming(conn, data)
	local session = sessions[conn];
	if session then
		local packets = session.stream:feed(data);
		for i = 1, #packets do
			handle_packet(session, packets[i]);
		end
	end
end

function mqtt_listener.ondisconnect(conn)
	local session = sessions[conn];
	for topic in pairs(session.subscriptions) do
		local host, node = topic:match("^([^/]+)/(.+)$");
		local subs = pubsub_subscribers[host];
		if subs then
			local node_subs = subs[node];
			if node_subs then
				node_subs[session] = nil;
			end
		end
	end
	sessions[conn] = nil;
	module:log("debug", "MQTT client disconnected");
end

module:provides("net", {
	default_port = 1883;
	listener = mqtt_listener;
});

module:provides("net", {
	name = "pubsub_mqtt_tls";
	encryption = "ssl";
	default_port = 8883;
	listener = mqtt_listener;
});

function module.add_host(module)
	local pubsub_module = hosts[module.host].modules.pubsub
	if pubsub_module then
		module:log("debug", "MQTT enabled for %s", module.host);
		module:depends("pubsub");
		pubsub_services[module.host] = assert(pubsub_module.service);
		local subscribers = {};
		pubsub_subscribers[module.host] = subscribers;
		local function handle_publish(event)
			-- Build MQTT packet
			local packet_types = setmetatable({}, {
				__index = function (self, payload_type)
					local packet = mqtt.serialize_packet{
						type = "publish";
						id = "\000\000";
						topic = module.host.."/"..payload_type.."/"..event.node;
						data = data_translators[payload_type].from_item(event.item) or "";
					};
					rawset(self, payload_type, packet);
					return packet;
				end;
			});
			-- Broadcast to subscribers
			module:log("debug", "Broadcasting PUBLISH to subscribers of %s/*/%s", module.host, event.node);
			for session, payload_type in pairs(subscribers[event.node] or {}) do
				session.conn:write(packet_types[payload_type]);
				module:log("debug", "Sent to %s", tostring(session));
			end
		end
		pubsub_services[module.host].events.add_handler("item-published", handle_publish);
		function module.unload()
			module:log("debug", "MQTT disabled for %s", module.host);
			pubsub_module.service.remove_handler("item-published", handle_publish);
			pubsub_services[module.host] = nil;
			pubsub_subscribers[module.host] = nil;
		end
	end
end
