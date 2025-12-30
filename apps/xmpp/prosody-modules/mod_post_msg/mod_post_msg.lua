module:depends"http"

local jid_split = require "util.jid".split;
local jid_prep = require "util.jid".prep;
local msg = require "util.stanza".message;
local test_password = require "core.usermanager".test_password;
local b64_decode = require "util.encodings".base64.decode;
local formdecode = require "net.http".formdecode;
local xml = require"util.xml";
local json = require "util.json";

local function require_valid_user(f)
	return function(event, path)
		local request = event.request;
		local response = event.response;
		local headers = request.headers;
		if not headers.authorization then
			response.headers.www_authenticate = ("Basic realm=%q"):format(module.host.."/"..module.name);
			return 401
		end
		local from_jid, password = b64_decode(headers.authorization:match"[^ ]*$"):match"([^:]*):(.*)";
		from_jid = jid_prep(from_jid);
		if from_jid and password then
			local user, host = jid_split(from_jid);
			local ok, err = test_password(user, host, password);
			if ok and user and host then
				module:log("debug", "Authed as %s", from_jid);
				return f(event, path, from_jid);
			elseif err then
				module:log("debug", "User failed authentication: %s", err);
			end
		end
		return 401
	end
end

local function handle_post(event, path, authed_user)
	local request = event.request;
	local response = event.response;
	local headers = request.headers;

	local body_type = headers.content_type;
	local to = jid_prep(path);
	local message;
	if body_type == "text/plain" then
		if to and request.body then
			message = msg({ to = to, from = authed_user, type = "chat"},request.body);
		end
	elseif body_type == "application/x-www-form-urlencoded" then
		local post_body = formdecode(request.body);
		message = msg({ to = post_body.to or to, from = authed_user,
		                type = post_body.type or "chat"}, post_body.body);
		if post_body.html then
			local html, err = xml.parse([[<body xmlns="http://www.w3.org/1999/xhtml">]]..post_body.html..[[</body>]]);
			if not html then
				module:log("warn", "mod_post_msg: invalid XML: %s", err);
				return 400;
			end
			message:tag("html", {xmlns="http://jabber.org/protocol/xhtml-im"}):add_child(html):up();
		end
	elseif body_type == "application/json" then
		local post_body = json.decode(request.body);
		if not post_body then return 400; end
		message = msg({ to = post_body.to or to, from = authed_user,
		                type = post_body.type or "chat"}, post_body.body);
	else
		return 415;
	end
	if message and message.attr.to then
		module:log("debug", "Sending %s", tostring(message));
		module:send(message);
		return 201;
	end
	return 422;
end

module:provides("http", {
	default_path = "/msg";
	route = {
		["POST /*"] = require_valid_user(handle_post);
		OPTIONS = function(e)
			local headers = e.response.headers;
			headers.allow = "POST";
			headers.accept = "application/x-www-form-urlencoded, text/plain";
			return 200;
		end;
	}
});
