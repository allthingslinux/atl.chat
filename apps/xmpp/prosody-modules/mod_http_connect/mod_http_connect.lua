-- This feature was added after Prosody 13.0
--% requires: net-connect-filter

local hashes = require "prosody.util.hashes";
local server = require "prosody.net.server";
local connect = require"prosody.net.connect".connect;
local basic = require "prosody.net.resolvers.basic";
local new_ip = require "prosody.util.ip".new_ip;

local b64_decode = require "prosody.util.encodings".base64.decode;

local proxy_secret = module:get_option_string("http_proxy_secret", require "prosody.util.id".long());

local allow_private_ips = module:get_option_boolean("http_proxy_to_private_ips", false);
local allow_all_ports = module:get_option_boolean("http_proxy_to_all_ports", false);

local allowed_target_ports = module:get_option_set("http_proxy_to_ports", { "443", "5281", "5443", "7443" }) / tonumber;

local sessions = {};

local listeners = {};

function listeners.onconnect(conn)
	local event = sessions[conn];
	local response = event.response;
	response.status_code = 200;
	response:send("");
	response.conn:onwritable();
	response.conn:setlistener(listeners, event);
	server.link(conn, response.conn);
	server.link(response.conn, conn);
	response.conn = nil;
end

function listeners.onattach(conn, event)
	sessions[conn] = event;
end

function listeners.onfail(event, err)
	local response = event.response;
	if assert(response) then
		response.status_code = 500;
		response:send(err);
	end
end

function listeners.ondisconnect(conn, err) --luacheck: ignore 212/conn 212/err
end

local function is_permitted_target(conn_type, ip, port)
	if not (allow_all_ports or allowed_target_ports:contains(tonumber(port))) then
		module:log("warn", "Forbidding tunnel to %s:%d (forbidden port)", ip, port);
		return false;
	end
	if not allow_private_ips then
		local family = (conn_type:byte(-1, -1) == 54) and "IPv6" or "IPv4";
		local parsed_ip = new_ip(ip, family);
		if parsed_ip.private then
			module:log("warn", "Forbidding tunnel to %s:%d (forbidden ip)", ip, port);
			return false;
		end
	end
	return true;
end

local function verify_auth(user, password)
	local expiry = tonumber(user, 10);
	if os.time() > expiry then
		module:log("warn", "Attempt to use expired credentials");
		return nil;
	end
	local expected_password = hashes.hmac_sha1(proxy_secret, user);
	if hashes.equals(b64_decode(password), expected_password) then
		return true;
	end
	module:log("warn", "Credential mismatch for %s: expected '%q' got '%q'", user, expected_password, password);
end

module:depends("http");
module:provides("http", {
	default_path = "/";
	route = {
		["CONNECT /*"] = function(event)
			local request, response = event.request, event.response;
			local host, port = request.url.scheme, request.url.path;
			if port == "" then return 400 end

			-- Auth check
			local realm = host;
			local headers = request.headers;
			if not headers.proxy_authorization then
				response.headers.proxy_authenticate = ("Basic realm=%q"):format(realm);
				return 407
			end
			local user, password = b64_decode(headers.proxy_authorization:match"[^ ]*$"):match"([^:]*):(.*)";
			if not verify_auth(user, password) then
				response.headers.proxy_authenticate = ("Basic realm=%q"):format(realm);
				return 407
			end

			local resolve = basic.new(host, port, "tcp", {
				filter = is_permitted_target;
			});
			connect(resolve, listeners, nil, event)
			return true;
		end;
	}
});

local http_url = module:http_url();
local parsed_url = require "socket.url".parse(http_url);

local proxy_host = parsed_url.host;
local proxy_port = tonumber(parsed_url.port);

if not proxy_port then
	if parsed_url.scheme == "https" then
		proxy_port = 443;
	elseif parsed_url.scheme == "http" then
		proxy_port = 80;
	end
end

module:depends "external_services";

module:add_item("external_service", {
	type = "http";
	transport = "tcp";
	host = proxy_host;
	port = proxy_port;

	secret = proxy_secret;
	algorithm = "turn";
	ttl = 3600;
});
