local async = require "util.async";
local promise = require "util.promise";
local http = require "net.http";
local st = require "util.stanza";

local xmlns_metadata = "xmpp:prosody.im/protocol/media-metadata#0"

local fetch_headers = {
	bytes = "content-length";
	type = "content-type";
	etag = "etag";
	blurhash = "blurhash";
};

local function fetch_media_metadata(url)
	return promise.new(function (resolve)
		http.request(url, { method = "HEAD" }, function (body, code, response) --luacheck: ignore 212/body
			if code == 200 then
				local metadata = {};
				for metadata_name, header_name in pairs(fetch_headers) do
					metadata[metadata_name] = response.headers[header_name];
				end
				resolve(metadata);
			else
				resolve(nil);
			end
		end);
	end);
end

local function metadata_to_tag(metadata)
	if not metadata then return; end

	local metadata_tag = st.stanza("metadata", { xmlns = xmlns_metadata });
	for k, v in pairs(metadata) do
		metadata_tag:text_tag(k, v)
	end

	return metadata_tag;
end

module:hook("muc-occupant-groupchat", function (event)
	local stanza = event.stanza;

	local promises;

	for oob in stanza:childtags("x", "jabber:x:oob") do
		if not promises then promises = {}; end
		local url = oob:get_child_text("url");
		local p = fetch_media_metadata(url)
			:next(metadata_to_tag)
			:next(function (metadata_tag)
				oob:add_child(metadata_tag);
			end);
		table.insert(promises, p);
	end

	if not promises then return; end

	async.wait(promise.all(promises));
end);
