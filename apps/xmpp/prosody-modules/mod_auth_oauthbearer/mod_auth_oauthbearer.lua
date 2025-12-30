local host = module.host;
local log = module._log;
local new_sasl = require "util.sasl".new;
local base64 = require "util.encodings".base64.encode;

local provider = {};

local oauth_client_id = module:get_option_string("oauth_client_id",  "");
local oauth_client_secret = module:get_option_string("oauth_client_secret",  "");
local oauth_url = module:get_option_string("oauth_url",  "");

if oauth_client_id == "" then error("oauth_client_id required") end
if oauth_client_secret == "" then error("oauth_client_secret required") end
if oauth_url == "" then error("oauth_url required") end

-- globals required by socket.http
if rawget(_G, "PROXY") == nil then
	rawset(_G, "PROXY", false)
end
if rawget(_G, "base_parsed") == nil then
	rawset(_G, "base_parsed", false)
end

local function interp(s, tab)
	-- String interpolation, so that we can make the oauth_url configurable
	-- e.g. oauth_url = "https://api.github.com/applications/{{oauth_client_id}}/tokens/{{password}}";
	--
	-- See: http://lua-users.org/wiki/StringInterpolation
	return (s:gsub('(%b{})', function(w) return tab[w:sub(3, -3)] or w end))
end

function provider.test_password(username, password, realm)
	log("debug", "Testing signed OAuth2 for user %s at realm %s", username, realm);
	local https = require "ssl.https";
	local url = interp(oauth_url, {oauth_client_id = oauth_client_id, password = password});
	
	module:log("debug", "The URL is:  "..url);
	local _, code, headers, status = https.request{
		url = url,
		headers = {
			Authorization = "Basic "..base64(oauth_client_id..":"..oauth_client_secret);
		}
	};
	if type(code) == "number" and code >= 200 and code <= 299 then
		module:log("debug", "OAuth provider confirmed valid password");
		return true;
	else
		module:log("debug", "OAuth provider returned status code: "..code);
	end
	module:log("warn", "Auth failed. Invalid username/password or misconfiguration.");
	return nil;
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

function provider.get_sasl_handler()
	local supported_mechanisms = {};
	supported_mechanisms["OAUTHBEARER"] = true;
	return new_sasl(host, {
		oauthbearer = function(sasl, username, password, realm)
			return provider.test_password(username, password, realm), true;
		end,
        mechanisms = supported_mechanisms
	});
end

module:provides("auth", provider);
