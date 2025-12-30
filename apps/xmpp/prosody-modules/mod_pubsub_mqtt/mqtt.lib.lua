local bit = require "util.bitcompat";

local stream_mt = {};
stream_mt.__index = stream_mt;

function stream_mt:read_bytes(n_bytes)
	module:log("debug", "Reading %d bytes... (buffer: %d)", n_bytes, #self.buffer);
	local data = self.buffer;
	if not data then
		module:log("debug", "No data, pausing.");
		data = coroutine.yield();
		module:log("debug", "Have %d bytes of data now (want %d)", #data, n_bytes);
	end
	if #data >= n_bytes then
		data, self.buffer = data:sub(1, n_bytes), data:sub(n_bytes+1);
	elseif #data < n_bytes then
		module:log("debug", "Not enough data (only %d bytes out of %d), pausing.", #data, n_bytes);
		self.buffer = data..coroutine.yield();
		module:log("debug", "Now we have %d bytes, reading...", #data);
		return self:read_bytes(n_bytes);
	end
	module:log("debug", "Returning %d bytes (buffer: %d)", #data, #self.buffer);
	return data;
end

function stream_mt:read_string()
	local len1, len2 = self:read_bytes(2):byte(1,2);
	local len = bit.lshift(len1, 8) + len2;
	return self:read_bytes(len), len+2;
end

function stream_mt:read_word()
	local len1, len2 = self:read_bytes(2):byte(1,2);
	local result = bit.lshift(len1, 8) + len2;
	module:log("debug", "read_word(%02x, %02x) = %04x (%d)", len1, len2, result, result);
	return result;
end

local function hasbit(byte, n_bit)
	return bit.band(byte, 2^n_bit) ~= 0;
end

local function encode_string(str)
	return string.char(bit.band(#str, 0xff00), bit.band(#str, 0x00ff))..str;
end

local packet_type_codes = {
	"connect", "connack",
	"publish", "puback", "pubrec", "pubrel", "pubcomp",
	"subscribe", "suback", "unsubscribe", "unsuback",
	"pingreq", "pingresp",
	"disconnect"
};

function stream_mt:read_packet()
	local packet = {};
	local header = self:read_bytes(1):byte();
	packet.type = packet_type_codes[bit.rshift(bit.band(header, 0xf0), 4)];
	packet.dup = bit.band(header, 0x08) == 0x08;
	packet.qos = bit.rshift(bit.band(header, 0x06), 1);
	packet.retain = bit.band(header, 0x01) == 0x01;

	-- Get length
	local length, multiplier = 0, 1;
	repeat
		local digit = self:read_bytes(1):byte();
		length = length + bit.band(digit, 0x7f)*multiplier;
		multiplier = multiplier*128;
	until bit.band(digit, 0x80) == 0;
	packet.length = length;
	if packet.type == "connect" then
		if self:read_string() ~= "MQTT" then
			module:log("warn", "Unexpected packet signature!");
			packet.type = nil; -- Invalid packet
		else
			packet.version = self:read_bytes(1):byte();
			module:log("debug", "ver: %02x", packet.version);
			if packet.version ~= 0x04 then
				module:log("warn", "MQTT version mismatch (got %02x, we support %02x", packet.version, 0x04);
			end
			local flags = self:read_bytes(1):byte();
			module:log("debug", "flags: %02x", flags);
			packet.keepalive_timer = self:read_bytes(2):byte();
			module:log("debug", "keepalive: %d", packet.keepalive_timer);
			packet.connect_flags = {};
			length = length - 11;
			packet.connect_flags = {
				clean_session = hasbit(flags, 1);
				will = hasbit(flags, 2);
				will_qos = bit.band(bit.rshift(flags, 2), 0x02);
				will_retain = hasbit(flags, 5);
				user_name = hasbit(flags, 7);
				password = hasbit(flags, 6);
			};
			module:log("debug", "%s", require "util.serialization".serialize(packet.connect_flags, "debug"));
			module:log("debug", "Reading client_id...");
			packet.client_id = self:read_string();
			if packet.connect_flags.will then
				module:log("debug", "Reading will...");
				packet.will = {
					topic = self:read_string();
					message = self:read_string();
					qos = packet.connect_flags.will_qos;
					retain = packet.connect_flags.will_retain;
				};
			end
			if packet.connect_flags.user_name then
				module:log("debug", "Reading username...");
				packet.username = self:read_string();
			end
			if packet.connect_flags.password then
				module:log("debug", "Reading password...");
				packet.password = self:read_string();
			end
			module:log("debug", "Done parsing connect!");
			length = 0; -- No payload left
		end
	elseif packet.type == "publish" then
		packet.topic = self:read_string();
		length = length - (#packet.topic+2);
		if packet.qos == 1 or packet.qos == 2 then
			packet.id = self:read_bytes(2);
			length = length - 2;
		end
	elseif packet.type == "subscribe" then
		if packet.qos == 1 or packet.qos == 2 then
			packet.id = self:read_bytes(2);
			length = length - 2;
		end
		local topics = {};
		while length > 0 do
			local topic, len = self:read_string();
			table.insert(topics, topic);
			self:read_bytes(1); -- QoS not used
			length = length - (len+1);
		end
		packet.topics = topics;
	end
	if length > 0 then
		packet.data = self:read_bytes(length);
	end
	module:log("debug", "MQTT packet complete!");
	return packet;
end

local function new_parser(self)
	return coroutine.wrap(function (data)
		self.buffer = data;
		while true do
			data = coroutine.yield(self:read_packet());
			module:log("debug", "Parser: %d new bytes", #data);
			self.buffer = (self.buffer or "")..data;
		end
	end);
end

function stream_mt:feed(data)
	local packets = {};
	local packet = self.parser(data);
	while packet do
		module:log("debug", "Received packet");
		table.insert(packets, packet);
		packet = self.parser("");
	end
	module:log("debug", "Returning %d packets", #packets);
	return packets;
end

local function new_stream()
	local stream = setmetatable({}, stream_mt);
	stream.parser = new_parser(stream);
	return stream;
end

local function serialize_packet(packet)
	local type_num = 0;
	for i, v in ipairs(packet_type_codes) do -- FIXME: I'm so tired right now.
		if v == packet.type then
			type_num = i;
			break;
		end
	end
	local header = string.char(bit.lshift(type_num, 4));

	if packet.type == "publish" then
		local topic = packet.topic or "";
		packet.data = string.char(bit.band(#topic, 0xff00), bit.band(#topic, 0x00ff))..topic..packet.data;
	elseif packet.type == "suback" then
		local t = {};
		for i, result_code in ipairs(packet.results) do
			table.insert(t, string.char(result_code));
		end
		packet.data = packet.id..table.concat(t);
	end

	-- Get length
	local length = #(packet.data or "");
	repeat
		local digit = length%128;
		length = math.floor(length/128);
		if length > 0 then
			digit = bit.bor(digit, 0x80);
		end
		header = header..string.char(digit); -- FIXME: ...
	until length <= 0;

	return header..(packet.data or "");
end

return {
	new_stream = new_stream;
	serialize_packet = serialize_packet;
};
