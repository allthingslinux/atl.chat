-- HTTP Access to PEP Avatar
-- By Kim Alvefur <zash@zash.se>

local mod_pep = module:depends"pep";

local um = require "core.usermanager";
local nodeprep = require "util.encodings".stringprep.nodeprep;
local base64_decode = require "util.encodings".base64.decode;
local urlencode = require "util.http".urlencode;

module:depends("http")
module:provides("http", {
	route = {
		["GET /*"] = function (event, path)
			if path == "" then
				return [[<h1>Hello from mod_http_pep_avatar</h1><p>This module provides access to public avatars of local users.</p>]];
			end;

			local request, response = event.request, event.response;
			local actor = request.ip;

			local user, item_id = path:match("^([^/]+)/(%x+)$");
			if not user then user = path; end
			local prepped = nodeprep(user);
			if not prepped then return 400; end
			if prepped ~= user then
				response.headers.location = module:http_url() .. "/" .. urlencode(prepped);
				return 302;
			end
			if not um.user_exists(user, module.host) then
				return 404;
			end

			local pep_service = mod_pep.get_pep_service(user);

			local ok, avatar_hash, avatar_meta = pep_service:get_last_item("urn:xmpp:avatar:metadata", actor);

			if not ok or not avatar_hash then
				return 404;
			end

			if (item_id or avatar_hash) == request.headers.if_none_match then
				return 304;
			end

			local data_ok, avatar_data = pep_service:get_items("urn:xmpp:avatar:data", actor, item_id or avatar_hash);
			if not data_ok or type(avatar_data) ~= "table" or not avatar_data[item_id or avatar_hash] then
				return 404;
			end

			local info = avatar_meta.tags[1]:get_child("info");
			if item_id and info.attr.id ~= item_id then
				info = nil;
				for altinfo in avatar_meta.tags[1]:childtags("info") do
					if altinfo.attr.id == item_id then
						info = altinfo;
					end
				end
			end

			if not info then
				return 404;
			end

			response.headers.etag = item_id or avatar_hash;

			response.headers.content_type = info and info.attr.type or "application/octet-stream";

			local data = avatar_data[item_id or avatar_hash];
			return base64_decode(data.tags[1]:get_text());
		end;
	}
});
