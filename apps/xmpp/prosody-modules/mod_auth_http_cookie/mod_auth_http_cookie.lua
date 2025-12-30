-- Prosody IM
-- Copyright (C) 2008-2013 Matthew Wild
-- Copyright (C) 2008-2013 Waqas Hussain
-- Copyright (C) 2014 Kim Alvefur
--
-- This project is MIT/X11 licensed. Please see the
-- COPYING file in the source package for more information.
--

local new_sasl = require "util.sasl".new;
local base64 = require "util.encodings".base64.encode;
local have_async, async = pcall(require, "util.async");

local nodeprep = require "util.encodings".stringprep.nodeprep;

local log = module._log;
local host = module.host;

local password_auth_url = module:get_option_string("http_auth_url",  ""):gsub("$host", host);

local cookie_auth_url = module:get_option_string("http_cookie_auth_url");
if cookie_auth_url then
	cookie_auth_url = cookie_auth_url:gsub("$host", host);
end

local external_needs_authzid = cookie_auth_url and cookie_auth_url:match("$user");

if password_auth_url == "" and not cookie_auth_url then error("http_auth_url or http_cookie_auth_url required") end


local provider = {};

-- globals required by socket.http
if rawget(_G, "PROXY") == nil then
	rawset(_G, "PROXY", false)
end
if rawget(_G, "base_parsed") == nil then
	rawset(_G, "base_parsed", false)
end
if not have_async then -- FINE! Set your globals then
	prosody.unlock_globals()
	require "ltn12"
	require "socket"
	require "socket.http"
	require "ssl.https"
	prosody.lock_globals()
end

local function async_http_request(url, headers)
	module:log("debug", "async_http_auth()");
	local http = require "net.http";
	local wait, done = async.waiter();
	local content, code, request, response;
	local ex = {
		headers = headers;
	}
	local function cb(content_, code_, request_, response_)
		content, code, request, response = content_, code_, request_, response_;
		done();
	end
	http.request(url, ex, cb);
	wait();
	log("debug", "response code %s", tostring(code));
	if code >= 200 and code <= 299 then
		return true, content;
	end
	return nil;
end

local function sync_http_request(url, headers)
	module:log("debug", "sync_http_auth()");
	require "ltn12";
	local http = require "socket.http";
	local https = require "ssl.https";
	local request;
	if string.sub(url, 1, string.len('https')) == 'https' then
		request = https.request;
	else
		request = http.request;
	end
	local body_chunks = {};
	local _, code, headers, status = request{
		url = url,
		headers = headers;
		sink = ltn12.sink.table(body_chunks);
	};
	log("debug", "response code %s %s", type(code), tostring(code));
	if type(code) == "number" and code >= 200 and code <= 299 then
		log("debug", "success")
		return true, table.concat(body_chunks);
	end
	return nil;
end

local http_request = have_async and async_http_request or sync_http_request;

function http_test_password(username, password)
	local url = password_auth_url:gsub("$user", username):gsub("$password", password);
	log("debug", "Testing password for user %s at host %s with URL %s", username, host, url);
	local ok = (http_request(url, { Authorization = "Basic "..base64(username..":"..password);  }));
	if not ok then
		return nil, "not authorized";
	end
	return true;
end

function http_test_cookie(cookie, username)
	local url = external_needs_authzid and cookie_auth_url:gsub("$user", username) or cookie_auth_url;
	log("debug", "Testing cookie auth for user %s at host %s with URL %s", username or "<unknown>", host, url);
	local ok, resp = http_request(url, { Cookie = cookie;  });
	if not ok then
		return nil, "not authorized";
	end

	return external_needs_authzid or resp;
end

function provider.test_password(username, password)
	return http_test_password(username, password);
end

function provider.users()
	return function()
		return nil;
	end
end

function provider.set_password(username, password)
	return nil, "Changing passwords not supported";
end

function provider.user_exists(username)
	return true;
end

function provider.create_user(username, password)
	return nil, "User creation not supported";
end

function provider.delete_user(username)
	return nil , "User deletion not supported";
end

local function get_session_cookies(session)
	local request = session.websocket_request; -- WebSockets
	if not request and session.requests then -- BOSH
		request = session.requests[1];
	end
	if not request and session.conn._http_open_response then -- Fallback BOSH
		local response = session.conn._http_open_response;
		request = response and response.request;
	end
	if request then
		return request.headers.cookie;
	end
end

function provider.get_sasl_handler(session)
	local cookie = cookie_auth_url and get_session_cookies(session);
	log("debug", "Request cookie: %s", cookie);
	return new_sasl(host, {
		plain_test = function(sasl, username, password, realm)
			return provider.test_password(username, password), true;
		end;
		external = cookie and function (authzid)
			if external_needs_authzid then
				-- Authorize the username provided by the client, using request cookie
				if authzid ~= "" then
					module:log("warn", "Client requested authzid, but cookie auth URL does not contain $user variable");
					return nil;
				end
				local success = http_test_cookie(cookie);
				if not success then
					return nil;
				end
				return nodeprep(authzid), true;
			else
				-- Authorize client using request cookie, username comes from auth server
				if authzid == "" then
					module:log("warn", "Client did not provide authzid, but cookie auth URL contains $user variable");
					return nil;
				end
				local unprepped_username = http_test_cookie(cookie, nodeprep(authzid));
				local username = nodeprep(unprepped_username);
				if not username then
					if unprepped_username then
						log("warn", "Username supplied by cookie_auth_url is not valid for XMPP");
					end
					return nil;
				end
				return username, true;
			end;
		end;
	});
end

module:provides("auth", provider);
