-- Prosody IM
-- Copyright (C) 2018 Emmanuel Gil Peyrot
--
-- This project is MIT/X11 licensed. Please see the
-- COPYING file in the source package for more information.

local base64 = require"util.encodings".base64;
local sha1 = require"util.hashes".sha1;
local st = require"util.stanza";
module:depends"http";

local vcard_storage = module:open_store"vcard";

local default_avatar = [[<svg xmlns='http://www.w3.org/2000/svg' version='1.1' viewBox='0 0 150 150'>
<rect width='150' height='150' fill='#888' stroke-width='1' stroke='#000'/>
<text x='75' y='100' text-anchor='middle' font-size='100'>?</text>
</svg>]];

local function get_avatar(event, path)
	local request, response = event.request, event.response;
	local photo_type, binval;
	local vcard, err = vcard_storage:get(path);
	if vcard then
		vcard = st.deserialize(vcard);
		local photo = vcard:get_child("PHOTO", "vcard-temp");
		if photo then
			photo_type = photo:get_child_text("TYPE", "vcard-temp");
			binval = photo:get_child_text("BINVAL", "vcard-temp");
		end
	end
	if not photo_type or not binval then
		-- FIXME: should be a 404, but Firefox won’t display it in that case…
		--response.status_code = 404;
		response.headers.content_type = "image/svg+xml";
		return default_avatar;
	end
	local avatar = base64.decode(binval);
	local hash = sha1(avatar, true);
	if request.headers.if_none_match == hash then
		return 304;
	end
	response.headers.content_type = photo_type;
	response.headers.etag = hash;
	return avatar;
end

module:provides("http", {
	route = {
		["GET /*"] = get_avatar;
	};
});
