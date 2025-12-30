-- HTTP Access to datamanager
-- By Kim Alvefur <zash@zash.se>

local t_concat = table.concat;
local t_insert = table.insert;
local jid_prep = require "util.jid".prep;
local jid_split = require "util.jid".split;
local test_password = require "core.usermanager".test_password;
local is_admin = require "core.usermanager".is_admin
local dm_load = require "util.datamanager".load;
local dm_store = require "util.datamanager".store;
local dm_list_load = require "util.datamanager".list_load;
local dm_list_store = require "util.datamanager".list_store;
local dm_list_append = require "util.datamanager".list_append;
local b64_decode = require "util.encodings".base64.decode;
local saslprep = require "util.encodings".stringprep.saslprep;
local realm = module:get_host() .. "/" .. module:get_name();
module:depends"http";

local encoders = {
	lua = require "util.serialization".serialize,
	json = require "util.json".encode
};
local decoders = {
	lua = require "util.serialization".deserialize,
	json = require "util.json".decode,
};
local content_type_map = {
	["text/x-lua"] = "lua"; lua = "text/x-lua";
	["application/json"] = "json"; json = "application/json";
}

local function require_valid_user(f)
	return function(event, path)
		local request = event.request;
		local response = event.response;
		local headers = request.headers;
		if not headers.authorization then
			response.headers.www_authenticate = ("Basic realm=%q"):format(realm);
			return 401
		end
		local from_jid, password = b64_decode(headers.authorization:match"[^ ]*$"):match"([^:]*):(.*)";
		from_jid = jid_prep(from_jid);
		password = saslprep(password);
		if from_jid and password then
			local user, host = jid_split(from_jid);
			local ok, err = test_password(user, host, password);
			if ok and user and host then
				return f(event, path, from_jid);
			elseif err then
				module:log("debug", "User failed authentication: %s", err);
			end
		end
		return 401
	end
end

local function handle_request(event, path, authed_user)
	local request, response = event.request, event.response;

	--module:log("debug", "spliting path");
	local path_items = {};
	for i in string.gmatch(path, "[^/]+") do
		t_insert(path_items, i);
	end
	--module:log("debug", "split path, got %d parts: %s", #path_items, table.concat(path_items, ", "));

	local user_node, user_host = jid_split(authed_user);
	if #path_items < 3 then
		--module:log("debug", "since we need at least 3 parts, adding %s/%s", user_host, user_node);
		t_insert(path_items, 1, user_node);
		t_insert(path_items, 1, user_host);
		--return http_response(400, "Bad Request");
	end

	if #path_items < 3 then
		return 404;
	end

	local p_host, p_user, p_store, p_type = unpack(path_items);

	if not p_store or not p_store:match("^[%a_]+$") then
		return 404;
	end

	if user_host ~= path_items[1] or user_node ~= path_items[2] then
		-- To only give admins access to anything, move the inside of this block after authz
		--module:log("debug", "%s wants access to %s@%s[%s], is admin?", authed_user, p_user, p_host, p_store)
		if not is_admin(authed_user, p_host) then
			return 403;
		end
	end

	local method = request.method;
	if method == "GET" then
		local data = dm_load(p_user, p_host, p_store);

		data = data or dm_list_load(p_user, p_host, p_store);

		--TODO Use the Accept header
		local content_type = p_type or "json";
		if data and encoders[content_type] then
			response.headers.content_type = content_type_map[content_type].."; charset=utf-8";
			return encoders[content_type](data);
		else
			return 404;
		end
	elseif method == "POST" or method == "PUT" then
		local body = request.body;
		if not body then

			return 400;
		end
		local content_type, content = request.headers.content_type, body;
		content_type = content_type and content_type_map[content_type]
		--module:log("debug", "%s: %s", content_type, tostring(content));
		content = content_type and decoders[content_type] and decoders[content_type](content);
		--module:log("debug", "%s: %s", type(content), tostring(content));
		if not content then
			return 400;
		end
		local ok, err
		if method == "PUT" then
			ok, err = dm_store(p_user, p_host, p_store, content);
		elseif method == "POST" then
			ok, err = dm_list_append(p_user, p_host, p_store, content);
		end
		if ok then
			response.headers.location = t_concat({module:http_url(nil,"/data"),p_host,p_user,p_store}, "/");
			return 201;
		else
			response.headers.debug = err;
			return 500;
		end
	elseif method == "DELETE" then
		dm_store(p_user, p_host, p_store, nil);
		dm_list_store(p_user, p_host, p_store, nil);
		return 204;
	end
end

local handle_request_with_auth = require_valid_user(handle_request);

module:provides("http", {
	default_path = "/data";
	route = {
		["GET /*"] = handle_request_with_auth,
		["PUT /*"] = handle_request_with_auth,
		["POST /*"] = handle_request_with_auth,
		["DELETE /*"] = handle_request_with_auth,
	};
});
