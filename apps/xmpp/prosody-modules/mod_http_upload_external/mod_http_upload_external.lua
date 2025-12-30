-- mod_http_upload_external
--
-- Copyright (C) 2015-2016 Kim Alvefur
--
-- This file is MIT/X11 licensed.
--

-- imports
local st = require"util.stanza";
local uuid = require"util.uuid".generate;
local http = require "util.http";
local dataform = require "util.dataforms".new;
local HMAC = require "util.hashes".hmac_sha256;
local jid = require "util.jid";

-- config
local file_size_limit = module:get_option_number(module.name .. "_file_size_limit", 100 * 1024 * 1024); -- 100 MB
local base_url = assert(module:get_option_string(module.name .. "_base_url"),
	module.name .. "_base_url is a required option");
local secret = assert(module:get_option_string(module.name .. "_secret"),
	module.name .. "_secret is a required option");
local access = module:get_option_set(module.name .. "_access", {});

local token_protocol = module:get_option_string(module.name .. "_protocol", "v1");

-- depends
module:depends("disco");

-- namespace
local legacy_namespace = "urn:xmpp:http:upload";
local namespace = "urn:xmpp:http:upload:0";

-- identity and feature advertising
module:add_identity("store", "file", module:get_option_string("name", "HTTP File Upload"))
module:add_feature(namespace);
module:add_feature(legacy_namespace);

module:add_extension(dataform {
	{ name = "FORM_TYPE", type = "hidden", value = namespace },
	{ name = "max-file-size", type = "text-single" },
}:form({ ["max-file-size"] = tostring(file_size_limit) }, "result"));

module:add_extension(dataform {
	{ name = "FORM_TYPE", type = "hidden", value = legacy_namespace },
	{ name = "max-file-size", type = "text-single" },
}:form({ ["max-file-size"] = tostring(file_size_limit) }, "result"));

local function magic_crypto_dust(random, filename, filesize, filetype)
	local param, message;
	if token_protocol == "v1" then
		param, message = "v", string.format("%s/%s %d", random, filename, filesize);
	else
		param, message = "v2", string.format("%s/%s\0%d\0%s", random, filename, filesize, filetype);
	end
	local digest = HMAC(secret, message, true);
	random, filename = http.urlencode(random), http.urlencode(filename);
	return base_url .. random .. "/" .. filename, "?"..param.."=" .. digest;
end

local function handle_request(origin, stanza, xmlns, filename, filesize, filetype)
	local user_bare = jid.bare(stanza.attr.from);
	local user_host = jid.host(user_bare);

	-- local clients or whitelisted jids/hosts only
	if not (origin.type == "c2s" or access:contains(user_bare) or access:contains(user_host)) then
		module:log("debug", "Request for upload slot from a %s", origin.type);
		origin.send(st.error_reply(stanza, "cancel", "not-authorized"));
		return nil, nil;
	end
	-- validate
	if not filename or filename:find("/") then
		module:log("debug", "Filename %q not allowed", filename or "");
		origin.send(st.error_reply(stanza, "modify", "bad-request", "Invalid filename"));
		return nil, nil;
	end
	if not filesize then
		module:log("debug", "Missing file size");
		origin.send(st.error_reply(stanza, "modify", "bad-request", "Missing or invalid file size"));
		return nil, nil;
	elseif filesize > file_size_limit then
		module:log("debug", "File too large (%d > %d)", filesize, file_size_limit);
		origin.send(st.error_reply(stanza, "modify", "not-acceptable", "File too large",
			st.stanza("file-too-large", {xmlns=xmlns})
				:tag("max-size"):text(tostring(file_size_limit))));
		return nil, nil;
	end
	local random = uuid();
	local get_url, verify = magic_crypto_dust(random, filename, filesize, filetype);
	local put_url = get_url .. verify;

	module:log("debug", "Handing out upload slot %s to %s@%s [%d %s]", get_url, origin.username, origin.host, filesize, filetype);

	return get_url, put_url;
end

-- hooks
module:hook("iq/host/"..legacy_namespace..":request", function (event)
	local stanza, origin = event.stanza, event.origin;
	local request = stanza.tags[1];
	local filename = request:get_child_text("filename");
	local filesize = tonumber(request:get_child_text("size"));
	local filetype = request:get_child_text("content-type") or "application/octet-stream";

	local get_url, put_url = handle_request(
		origin, stanza, legacy_namespace, filename, filesize, filetype);

	if not get_url then
		-- error was already sent
		return true;
	end

	local reply = st.reply(stanza)
		:tag("slot", { xmlns = legacy_namespace })
			:tag("get"):text(get_url):up()
			:tag("put"):text(put_url):up()
		:up();
	origin.send(reply);
	return true;
end);

module:hook("iq/host/"..namespace..":request", function (event)
	local stanza, origin = event.stanza, event.origin;
	local request = stanza.tags[1];
	local filename = request.attr.filename;
	local filesize = tonumber(request.attr.size);
	local filetype = request.attr["content-type"] or "application/octet-stream";

	local get_url, put_url = handle_request(
		origin, stanza, namespace, filename, filesize, filetype);

	if not get_url then
		-- error was already sent
		return true;
	end

	local reply = st.reply(stanza)
		:tag("slot", { xmlns = namespace})
			:tag("get", { url = get_url }):up()
			:tag("put", { url = put_url }):up()
		:up();
	origin.send(reply);
	return true;
end);
