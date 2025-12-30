module:depends("cache_c2s_caps");

local st = require "util.stanza";
local encodings = require "util.encodings";
local b64_encode = encodings.base64.encode;
local b64_decode = encodings.base64.decode;
local sha1 = require"util.hashes".sha1;

-- TODO: Move that to storage.
local cache = {};
-- TODO: use util.cache for this.
local in_flight = {};

local function check_cid(src)
	return src:match("^cid:(%w+%+%w+@bob%.xmpp%.org)$");
end

local function handle_data_carrier(tag)
	if tag.name ~= "data" or tag.attr.xmlns ~= "urn:xmpp:bob" then
		return tag;
	end
	local cid = tag.attr.cid;
	local media_type = tag.attr.type;
	local max_age = tag.attr['max-age'];
	local b64_content = tag:get_text();
	local content = b64_decode(b64_content);
	local hash = sha1(content, true);
	if cid ~= "sha1+"..hash.."@bob.xmpp.org" then
		module:log("debug", "Invalid BoB cid, %s ~= %s", cid, "sha1+"..hash.."@bob.xmpp.org");
		return nil;
	end
	cache[cid] = { media_type = media_type, max_age = max_age, content = content };
	if in_flight[cid] then
		local iq = st.iq({ type = "result", id = "fixme" });
		iq:add_direct_child(tag);
		for jid, data in pairs(in_flight[cid]) do
			iq.attr.from = data.from;
			iq.attr.to = jid;
			iq.attr.id = data.id;
			module:send(iq);
		end
		in_flight[cid] = nil;
	end
	return nil;
end

local current_id = 0;
local function send_iq(room_jid, jid, cid, log)
	local iq = st.iq({ type = "get", from = room_jid, to = jid, id = "bob-"..current_id })
		:tag("data", { xmlns = "urn:xmpp:bob", cid = cid });
	log("debug", "found BoB image in XHTML-IM, asking %s for cid %s", jid, cid);
	module:send(iq);
	in_flight[cid] = {};
end

local function find_images(tag, jid, room_jid, log)
	if tag.name == "img" and tag.attr.xmlns == "http://www.w3.org/1999/xhtml" then
		local src = tag.attr.src;
		local cid = check_cid(src);
		if not cid then
			return;
		end
		if cache[cid] then
			log("debug", "cid %s already found in cache", cid);
			return;
		end
		if in_flight[cid] then
			log("debug", "cid %s already queried", cid);
			return;
		end
		send_iq(room_jid, jid, cid, log);
		return;
	end
	for child in tag:childtags(nil, "http://www.w3.org/1999/xhtml") do
		find_images(child, jid, room_jid, log);
	end
end

local function message_handler(event)
	local stanza, origin = event.stanza, event.origin;
	local jid = stanza.attr.from;
	local room_jid = stanza.attr.to;
	local log = origin.log or module._log;

	-- Remove and cache all <data/> elements embedded here.
	stanza:maptags(handle_data_carrier);

	-- Find and query all of the cids not already cached.
	local tag = stanza:get_child("html", "http://jabber.org/protocol/xhtml-im");
	if not tag then
		return;
	end
	for body in tag:childtags("body", "http://www.w3.org/1999/xhtml") do
		find_images(body, jid, room_jid, log);
	end
end

local function handle_data_get(stanza, cid, log)
	local data = cache[cid];
	if not data then
		log("debug", "BoB requested for data not in cache (cid %s), falling through.", cid);
		if in_flight[cid] then
			log("debug", "But an iq has already been sent, let’s wait…");
			in_flight[cid][stanza.attr.from] = { id = stanza.attr.id, from = stanza.attr.to };
			return true;
		end
		return nil;
	end

	local iq = st.reply(stanza);
	iq:text_tag("data", b64_encode(data.content), {
		xmlns = "urn:xmpp:bob",
		cid = cid,
		type = data.media_type,
		['max-age'] = data.max_age,
	});
	log("debug", "Answering BoB request for cid %s on the behalf of %s", cid, stanza.attr.to);
	module:send(iq);
	return true;
end

local function iq_handler(event)
	local stanza, origin = event.stanza, event.origin;
	local tag = stanza.tags[1];
	if not tag or tag.name ~= "data" or tag.attr.xmlns ~= "urn:xmpp:bob" then
		return nil;
	end
	local log = origin.log or module._log;
	local cid = tag.attr.cid;
	if not cid then
		log("debug", "BoB iq doesn’t contain a cid attribute.");
		return;
	end
	if stanza.attr.type == "get" then
		return handle_data_get(stanza, cid, log);
	elseif stanza.attr.type == "result" then
		handle_data_carrier(tag);
		return true;
	end
	-- TODO: also handle error iqs.
end

module:hook("message/bare", message_handler, 1);
module:hook("iq/full", iq_handler, 1);
module:hook("iq/bare", iq_handler, 1);
