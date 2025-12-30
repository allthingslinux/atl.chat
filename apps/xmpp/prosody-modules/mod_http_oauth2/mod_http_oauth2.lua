local usermanager = require "core.usermanager";
local url = require "socket.url";
local array = require "util.array";
local cache = require "util.cache";
local encodings = require "util.encodings";
local errors = require "util.error";
local hashes = require "util.hashes";
local http = require "util.http";
local id = require "util.id";
local it = require "util.iterators";
local jid = require "util.jid";
local json = require "util.json";
local schema = require "util.jsonschema";
local jwt = require "util.jwt";
local random = require "util.random";
local set = require "util.set";
local st = require "util.stanza";

local base64 = encodings.base64;

local function b64url(s)
	return (base64.encode(s):gsub("[+/=]", { ["+"] = "-", ["/"] = "_", ["="] = "" }))
end

local function tmap(t)
	return function(k)
		return t[k];
	end
end

local function array_contains(haystack, needle)
	if not haystack then
		return false
	end
	for i = 1, #haystack do
		if haystack[i] == needle then
			return true
		end
	end
	return false
end

local function strict_url_parse(urlstr)
	local url_parts = url.parse(urlstr);
	if not url_parts then return url_parts; end
	if url_parts.userinfo then return false; end
	if url_parts.port then
		local port = tonumber(url_parts.port);
		if not port then return false; end
		if port <= 0 or port > 0xffff then return false; end
		if port ~= math.floor(port) then return false; end
	end
	if url_parts.host then
		if encodings.stringprep.nameprep(url_parts.host) ~= url_parts.host then
			return false;
		end
		if not encodings.idna.to_ascii(url_parts.host) then
			return false;
		end
	end
	return url_parts;
end

local function strict_formdecode(query)
	if not query then
		return nil;
	end
	local params = http.formdecode(query);
	if type(params) ~= "table" then
		return nil, "no-pairs";
	end
	local dups = {};
	for _, pair in ipairs(params) do
		if dups[pair.name] then
			return nil, "duplicate";
		end
		dups[pair.name] = true;
	end
	return params;
end

local function read_file(base_path, fn, required)
	local f, err = io.open(base_path .. "/" .. fn);
	if not f then
		module:log(required and "error" or "debug", "Unable to load template file: %s", err);
		if required then
			return error("Failed to load templates");
		end
		return nil;
	end
	local data = assert(f:read("*a"));
	assert(f:close());
	return data;
end

local allowed_locales = module:get_option_array("allowed_oauth2_locales", {});
-- TODO Allow translations or per-locale templates somehow.

local template_path = module:get_option_path("oauth2_template_path", "html");
local templates = {
	login = read_file(template_path, "login.html", true);
	consent = read_file(template_path, "consent.html", true);
	oob = read_file(template_path, "oob.html", true);
	device = read_file(template_path, "device.html", true);
	error = read_file(template_path, "error.html", true);
	css = read_file(template_path, "style.css");
	js = read_file(template_path, "script.js");
};

local site_name = module:get_option_string("site_name", module.host);

local security_policy = module:get_option_string("oauth2_security_policy", "default-src 'self'");

local render_html = require"util.interpolation".new("%b{}", st.xml_escape);
local function render_page(template, data, sensitive)
	data = data or {};
	data.site_name = site_name;
	local resp = {
		status_code = data.error and data.error.code or 200;
		headers = {
			["Content-Type"] = "text/html; charset=utf-8";
			["Content-Security-Policy"] = security_policy;
			["Referrer-Policy"] = "no-referrer";
			["X-Frame-Options"] = "DENY";
			["Cache-Control"] = (sensitive and "no-store" or "no-cache")..", private";
			["Pragma"] = "no-cache";
		};
		body = render_html(template, data);
	};
	return resp;
end

local authorization_server_metadata = nil;

local tokens = module:depends("tokenauth");

local default_access_ttl = module:get_option_number("oauth2_access_token_ttl", 3600);
local default_refresh_ttl = module:get_option_number("oauth2_refresh_token_ttl", 604800);

-- Used to derive client_secret from client_id, set to enable stateless dynamic registration.
local registration_key = module:get_option_string("oauth2_registration_key");
local registration_algo = module:get_option_string("oauth2_registration_algorithm", "HS256");
local registration_ttl = module:get_option("oauth2_registration_ttl", nil);
local registration_options = module:get_option("oauth2_registration_options",
	{ default_ttl = registration_ttl; accept_expired = not registration_ttl });

local pkce_required = module:get_option_boolean("oauth2_require_code_challenge", true);
local respect_prompt = module:get_option_boolean("oauth2_respect_oidc_prompt", false);
local expect_username_jid = module:get_option_boolean("oauth2_expect_username_jid", false);

local verification_key;
local sign_client, verify_client;
if registration_key then
	-- Tie it to the host if global
	verification_key = hashes.hmac_sha256(registration_key, module.host);
	sign_client, verify_client = jwt.init(registration_algo, registration_key, registration_key, registration_options);
end

local new_device_token, verify_device_token = jwt.init("HS256", random.bytes(32), nil, { default_ttl = 600 });

-- verify and prepare client structure
local function check_client(client_id)
	if not verify_client then
		return nil, "client-registration-not-enabled";
	end

	local ok, client = verify_client(client_id);
	if not ok then
		return ok, client;
	end

	client.client_hash = b64url(hashes.sha256(client_id));
	return client;
end

local purpose_map = { ["oauth2-refresh"] = "refresh_token"; ["oauth"] = "access_token" };

-- scope : string | array | set
--
-- at each step, allow the same or a subset of scopes
-- (all ( client ( grant ( token ) ) ))
-- preserve order since it determines role if more than one granted

-- string -> array
local function parse_scopes(scope_string)
	return array(scope_string:gmatch("%S+"));
end

local openid_claims = set.new();

module:add_item("openid-claim", { claim = "openid"; title = "OpenID";
	description = "Tells the application your JID and when you authenticated."; });

-- https://openid.net/specs/openid-connect-core-1_0.html#OfflineAccess
-- The "offline_access" scope grants access to refresh tokens
module:add_item("openid-claim", { claim = "offline_access"; title = "Offline Access";
	description = "Application may renew access without interaction."; });

module:handle_items("openid-claim", function(event)
	authorization_server_metadata = nil;
	openid_claims:add(event.item.claim or event.item);
end, function()
	authorization_server_metadata = nil;
	openid_claims = set.new(array.new(module:get_host_items("openid-claim")):map(function(item)
		return item.claim or item;
	end));
end, true);

-- array -> array, array, array
local function split_scopes(scope_list)
	local claims, roles, unknown = array(), array(), array();
	local all_roles = usermanager.get_all_roles(module.host);
	for _, scope in ipairs(scope_list) do
		if openid_claims:contains(scope) then
			claims:push(scope);
		elseif scope == "xmpp" or all_roles[scope] then
			roles:push(scope);
		else
			unknown:push(scope);
		end
	end
	return claims, roles, unknown;
end

local function can_assume_role(username, requested_role)
	return requested_role == "xmpp" or usermanager.user_can_assume_role(username, module.host, requested_role);
end

-- function (string) : function(string) : boolean
local function role_assumable_by(username)
	return function(role)
		return can_assume_role(username, role);
	end
end

-- string, array --> array
local function user_assumable_roles(username, requested_roles)
	return array.filter(requested_roles, role_assumable_by(username));
end

-- string, string|nil --> string, string
local function filter_scopes(username, requested_scope_string)
	local requested_scopes, requested_roles = split_scopes(parse_scopes(requested_scope_string or ""));

	local granted_roles = user_assumable_roles(username, requested_roles);
	local granted_scopes = requested_scopes + granted_roles;

	local selected_role = granted_roles[1];

	return granted_scopes:concat(" "), selected_role;
end

local function code_expires_in(code) --> number, seconds until code expires
	return os.difftime(code.expires, os.time());
end

local function code_expired(code) --> boolean, true: has expired, false: still valid
	return code_expires_in(code) < 0;
end

-- LRU cache for short-term storage of authorization codes and device codes
local codes = cache.new(10000, function (_, code)
	-- If the cache is full and the oldest item hasn't expired yet then we
	-- might be under some kind of DoS attack, so might as well reject further
	-- entries for a bit.
	return code_expired(code)
end);

-- Clear out unredeemed codes so they don't linger in memory.
module:daily("Clear expired authorization codes", function()
	-- The tail should be the least recently touched item, and most likely to
	-- have expired already, so check and remove that one until encountering
	-- one that has not expired.
	local k, code = codes:tail();
	while code and code_expired(code) do
		codes:set(k, nil);
		k, code = codes:tail();
	end
end)

local function get_issuer()
	return (module:http_url(nil, "/"):gsub("/$", ""));
end

-- Non-standard special redirect URI that has the AS show the authorization
-- code to the user for them to copy-paste into the client, which can then
-- continue as if it received it via redirect.
local oob_uri = "urn:ietf:wg:oauth:2.0:oob";

-- RFC 8628 OAuth 2.0 Device Authorization Grant
local device_uri = "urn:ietf:params:oauth:grant-type:device_code";

local loopbacks = set.new({ "localhost", "127.0.0.1", "::1" });

local function oauth_error(err_name, err_desc)
	return errors.new({
		type = "modify";
		condition = "bad-request";
		code = err_name == "invalid_client" and 401 or 400;
		text = err_desc or err_name:gsub("^.", string.upper):gsub("_", " ");
		extra = { oauth2_response = { error = err_name, error_description = err_desc } };
	});
end

-- client_id / client_metadata are pretty large, filter out a subset of
-- properties that are deemed useful e.g. in case tokens issued to a certain
-- client needs to be revoked
local function client_subset(client)
	return {
		name = client.client_name;
		uri = client.client_uri;
		id = client.software_id;
		version = client.software_version;
		hash = client.client_hash;
	};
end

local function may_issue_refresh_token(client, scope_string)
	return array_contains(client.grant_types, "refresh_token") and array_contains(parse_scopes(scope_string), "offline_access");
end

local function new_access_token(token_jid, role, scope_string, client, id_token, refresh_token_info)
	local token_data = { oauth2_scopes = scope_string, oauth2_client = nil };
	if client then
		token_data.oauth2_client = client_subset(client);
	end
	if next(token_data) == nil then
		token_data = nil;
	end

	local grant = refresh_token_info and refresh_token_info.grant;
	if not grant then
		-- No existing grant, create one
		grant = tokens.create_grant(token_jid, token_jid, nil, token_data);
	end

	if refresh_token_info then
		-- out with the old refresh tokens
		local ok, err = tokens.revoke_token(refresh_token_info.token);
		if not ok then
			module:log("error", "Could not revoke refresh token: %s", err);
			return 500;
		end
	end
	-- in with the new refresh token
	local refresh_token;
	if refresh_token_info ~= false and may_issue_refresh_token(client, scope_string) then
		refresh_token = tokens.create_token(token_jid, grant.id, nil, default_refresh_ttl, "oauth2-refresh");
	end

	if role == "xmpp" then
		-- Special scope meaning the users default role.
		local user_default_role = usermanager.get_user_role(jid.node(token_jid), module.host);
		role = user_default_role and user_default_role.name;
	end

	local access_token, access_token_info = tokens.create_token(token_jid, grant.id, role, default_access_ttl, "oauth2");

	local expires_at = access_token_info.expires;
	return {
		token_type = "bearer";
		access_token = access_token;
		expires_in = expires_at and (expires_at - os.time()) or nil;
		scope = scope_string;
		id_token = id_token;
		refresh_token = refresh_token or nil;
	};
end

local function normalize_loopback(uri)
	local u = url.parse(uri);
	if u.scheme == "http" and loopbacks:contains(u.host) then
		u.authority = nil;
		u.host = "::1";
		u.port = nil;
		return url.build(u);
	end
	-- else, not a valid loopback uri
end

local function get_redirect_uri(client, query_redirect_uri) -- record client, string : string
	if query_redirect_uri == device_uri and client.grant_types then
		if array_contains(client.grant_types, device_uri) then
			return query_redirect_uri;
		end
		-- Tried to use device authorization flow without registering it.
		return;
	elseif not client.redirect_uris then
		return;
	elseif not query_redirect_uri then
		if #client.redirect_uris ~= 1 then
			-- Client registered multiple URIs, it needs specify which one to use
			return;
		end
		-- When only a single URI is registered, that's the default
		return client.redirect_uris[1];
	end
	-- Verify the client-provided URI matches one previously registered
	for _, redirect_uri in ipairs(client.redirect_uris) do
		if query_redirect_uri == redirect_uri then
			return redirect_uri
		end
	end
	-- The authorization server MUST allow any port to be specified at the time
	-- of the request for loopback IP redirect URIs, to accommodate clients that
	-- obtain an available ephemeral port from the operating system at the time
	-- of the request.
	-- https://www.ietf.org/archive/id/draft-ietf-oauth-v2-1-08.html#section-8.4.2
	local loopback_redirect_uri = normalize_loopback(query_redirect_uri);
	if loopback_redirect_uri then
		for _, redirect_uri in ipairs(client.redirect_uris) do
			if loopback_redirect_uri == normalize_loopback(redirect_uri) then
				return query_redirect_uri;
			end
		end
	end
end

local grant_type_handlers = {};
local response_type_handlers = {};
local verifier_transforms = {};

function grant_type_handlers.implicit()
	-- Placeholder to make discovery work correctly.
	-- Access tokens are delivered via redirect when using the implict flow, not
	-- via the token endpoint, so how did you get here?
	return oauth_error("invalid_request");
end

local function make_client_secret(client_id) --> client_secret
	return hashes.hmac_sha256(verification_key, client_id, true);
end

local function verify_client_secret(client_id, client_secret)
	return hashes.equals(make_client_secret(client_id), client_secret);
end

function grant_type_handlers.password(params, client)
	local request_username

	if expect_username_jid then
		local request_jid = params.username;
		if not request_jid then
			return oauth_error("invalid_request", "missing 'username' (JID)");
		end
		local _request_username, request_host = jid.prepped_split(request_jid);

		if not (_request_username and request_host) or request_host ~= module.host then
			return oauth_error("invalid_request", "invalid JID");
		end

		request_username = _request_username
	else
		request_username = params.username;
		if not request_username then
			return oauth_error("invalid_request", "missing 'username'");
		end
	end

	local request_password = params.password;
	if not request_password then
		return oauth_error("invalid_request", "missing 'password'");
	end

	local auth_event = {
		session = {
			type = "oauth2";
			ip = "::";
			username = request_username;
			host = module.host;
			log = module._log;
			sasl_handler = { username = request_username; selected = "x-oauth2-password" };
			client_id = client.client_name;
		};
	};

	if not usermanager.test_password(request_username, module.host, request_password) then
		module:fire_event("authentication-failure", auth_event);
		return oauth_error("invalid_grant", "incorrect credentials");
	end

	module:fire_event("authentication-success", auth_event);

	local granted_jid = jid.join(request_username, module.host);
	local granted_scopes, granted_role = filter_scopes(request_username, params.scope);
	return json.encode(new_access_token(granted_jid, granted_role, granted_scopes, client));
end

function response_type_handlers.code(client, params, granted_jid, id_token)
	local request_username, request_host = jid.split(granted_jid);
	if not request_host or request_host ~= module.host then
		return oauth_error("invalid_request", "invalid JID");
	end
	local granted_scopes, granted_role = filter_scopes(request_username, params.scope);

	local redirect_uri = get_redirect_uri(client, params.redirect_uri);

	if pkce_required and not params.code_challenge and redirect_uri ~= device_uri and redirect_uri ~= oob_uri then
		return oauth_error("invalid_request", "PKCE required");
	end

	local prefix = "authorization_code:";
	local code = id.medium();
	if redirect_uri == device_uri then
		local is_device, device_state = verify_device_token(params.state);
		if is_device then
			-- reconstruct the device_code
			prefix = "device_code:";
			code = b64url(hashes.hmac_sha256(verification_key, device_state.user_code));
		else
			return oauth_error("invalid_request");
		end
	end
	local ok = codes:set(prefix.. params.client_id .. "#" .. code, {
		expires = os.time() + 600;
		granted_jid = granted_jid;
		granted_scopes = granted_scopes;
		granted_role = granted_role;
		challenge = params.code_challenge;
		challenge_method = params.code_challenge_method;
		id_token = id_token;
	});
	if not ok then
		return oauth_error("temporarily_unavailable");
	end

	if redirect_uri == oob_uri then
		return render_page(templates.oob, { client = client; authorization_code = code }, true);
	elseif redirect_uri == device_uri then
		return render_page(templates.device, { client = client }, true);
	elseif not redirect_uri then
		return oauth_error("invalid_redirect_uri");
	end

	local redirect = url.parse(redirect_uri);

	local query = strict_formdecode(redirect.query);
	if type(query) ~= "table" then query = {}; end
	table.insert(query, { name = "code", value = code });
	table.insert(query, { name = "iss", value = get_issuer() });
	if params.state then
		table.insert(query, { name = "state", value = params.state });
	end
	redirect.query = http.formencode(query);

	return {
		status_code = 303;
		headers = {
			cache_control = "no-store";
			pragma = "no-cache";
			location = url.build(redirect);
		};
	}
end

-- Implicit flow
function response_type_handlers.token(client, params, granted_jid)
	local request_username, request_host = jid.split(granted_jid);
	if not request_host or request_host ~= module.host then
		return oauth_error("invalid_request", "invalid JID");
	end
	local granted_scopes, granted_role = filter_scopes(request_username, params.scope);
	local token_info = new_access_token(granted_jid, granted_role, granted_scopes, client, nil);

	local redirect = url.parse(get_redirect_uri(client, params.redirect_uri));
	if not redirect then return oauth_error("invalid_redirect_uri"); end
	token_info.state = params.state;
	redirect.fragment = http.formencode(token_info);

	return {
		status_code = 303;
		headers = {
			cache_control = "no-store";
			pragma = "no-cache";
			location = url.build(redirect);
		};
	}
end

function grant_type_handlers.authorization_code(params, client)
	if not params.code then return oauth_error("invalid_request", "missing 'code'"); end
	if params.scope and params.scope ~= "" then
		-- FIXME allow a subset of granted scopes
		return oauth_error("invalid_scope", "unknown scope requested");
	end
	local code, err = codes:get("authorization_code:" .. params.client_id .. "#" .. params.code);
	if err then error(err); end
	-- MUST NOT use the authorization code more than once, so remove it to
	-- prevent a second attempted use
	-- TODO if a second attempt *is* made, revoke any tokens issued
	codes:set("authorization_code:" .. params.client_id .. "#" .. params.code, nil);
	if not code or type(code) ~= "table" or code_expired(code) then
		module:log("debug", "authorization_code invalid or expired: %q", code);
		return oauth_error("invalid_client", "incorrect credentials");
	end

	-- TODO Decide if the code should be removed or not when PKCE fails
	local transform = verifier_transforms[code.challenge_method or "plain"];
	if not transform then
		return oauth_error("invalid_request", "unknown challenge transform method");
	elseif transform(params.code_verifier) ~= code.challenge then
		return oauth_error("invalid_grant", "incorrect credentials");
	end

	return json.encode(new_access_token(code.granted_jid, code.granted_role, code.granted_scopes, client, code.id_token));
end

function grant_type_handlers.refresh_token(params, client)
	if not params.refresh_token then return oauth_error("invalid_request", "missing 'refresh_token'"); end

	local refresh_token_info = tokens.get_token_info(params.refresh_token);
	if not refresh_token_info or refresh_token_info.purpose ~= "oauth2-refresh" then
		return oauth_error("invalid_grant", "invalid refresh token");
	end

	local refresh_token_client = refresh_token_info.grant.data.oauth2_client;
	if not refresh_token_client.hash or refresh_token_client.hash ~= client.client_hash then
		module:log("warn", "OAuth client %q (%s) tried to use refresh token belonging to %q (%s)", client.client_name, client.client_hash,
			refresh_token_client.name, refresh_token_client.hash);
		return oauth_error("unauthorized_client", "incorrect credentials");
	end

	local refresh_scopes = refresh_token_info.grant.data.oauth2_scopes;

	if params.scope then
		local granted_scopes = set.new(parse_scopes(refresh_scopes));
		local requested_scopes = parse_scopes(params.scope);
		refresh_scopes = array.filter(requested_scopes, function(scope)
			return granted_scopes:contains(scope);
		end):concat(" ");
	end

	local username = jid.split(refresh_token_info.jid);
	local new_scopes, role = filter_scopes(username, refresh_scopes);

	-- new_access_token() requires the actual token
	refresh_token_info.token = params.refresh_token;

	return json.encode(new_access_token(refresh_token_info.jid, role, new_scopes, client, nil, refresh_token_info));
end

grant_type_handlers[device_uri] = function(params, client)
	if not params.device_code then return oauth_error("invalid_request", "missing 'device_code'"); end

	local code = codes:get("device_code:" .. params.client_id .. "#" .. params.device_code);
	if type(code) ~= "table" or code_expired(code) then
		return oauth_error("expired_token");
	elseif code.error then
		return code.error;
	elseif not code.granted_jid then
		return oauth_error("authorization_pending");
	end
	codes:set("device_code:" .. params.client_id .. "#" .. params.device_code, nil);

	return json.encode(new_access_token(code.granted_jid, code.granted_role, code.granted_scopes, client, code.id_token));
end

-- RFC 7636 Proof Key for Code Exchange by OAuth Public Clients

function verifier_transforms.plain(code_verifier)
	-- code_challenge = code_verifier
	return code_verifier;
end

function verifier_transforms.S256(code_verifier)
	-- code_challenge = BASE64URL-ENCODE(SHA256(ASCII(code_verifier)))
	return code_verifier and b64url(hashes.sha256(code_verifier));
end

-- Used to issue/verify short-lived tokens for the authorization process below
local new_user_token, verify_user_token = jwt.init("HS256", random.bytes(32), nil, { default_ttl = 600 });

-- From the given request, figure out if the user is authenticated and has granted consent yet
-- As this requires multiple steps (seek credentials, seek consent), we have a lot of state to
-- carry around across requests. We also need to protect against CSRF and session mix-up attacks
-- (e.g. the user may have multiple concurrent flows in progress, session cookies aren't unique
--  to one of them).
-- Our strategy here is to preserve the original query string (containing the authz request), and
-- encode the rest of the flow in form POSTs.
local function get_auth_state(request)
	local form = request.method == "POST"
	         and request.body
	         and request.body ~= ""
	         and request.headers.content_type == "application/x-www-form-urlencoded"
	         and http.formdecode(request.body);

	if type(form) ~= "table" then return {}; end

	if not form.user_token then
		-- First step: login
		local username = encodings.stringprep.nodeprep(form.username);
		local password = encodings.stringprep.saslprep(form.password);
		-- Many things hooked to authentication-{success,failure} don't expect
		-- non-XMPP sessions so here's something close enough...
		local auth_event = {
			session = {
				type = "http";
				ip = request.ip;
				conn = request.conn;
				username = username;
				host = module.host;
				log = request.log;
				sasl_handler = { username = username; selected = "x-www-form" };
				client_id = request.headers.user_agent;
			};
		};
		if not (username and password) or not usermanager.test_password(username, module.host, password) then
			module:fire_event("authentication-failure", auth_event);
			return {
				error = "Invalid username/password";
			};
		end
		module:fire_event("authentication-success", auth_event);
		return {
			user = {
				username = username;
				host = module.host;
				token = new_user_token({ username = username; host = module.host; amr = { "pwd" } });
			};
		};
	elseif form.user_token and form.consent then
		-- Second step: consent
		local ok, user = verify_user_token(form.user_token);
		if not ok then
			return {
				error = user == "token-expired" and "Session expired - try again" or nil;
			};
		end

		local scopes = array():append(form):filter(function(field)
			return field.name == "scope";
		end):pluck("value");

		user.token = form.user_token;
		return {
			user = user;
			scopes = scopes;
			consent = form.consent == "granted";
		};
	end

	return {};
end

local function get_request_credentials(request)
	if not request.headers.authorization then return; end

	local auth_type, auth_data = string.match(request.headers.authorization, "^(%S+)%s(.+)$");
	if not auth_type then return nil; end

	-- As described in Section 2.3 of [RFC5234], the string Bearer is case-insensitive.
	-- https://datatracker.ietf.org/doc/html/draft-ietf-oauth-v2-1-11#section-5.1.1
	auth_type = auth_type:lower();

	if auth_type == "basic" then
		local creds = base64.decode(auth_data);
		if not creds then return; end
		local username, password = string.match(creds, "^([^:]+):(.*)$");
		if not username then return; end
		return {
			type = "basic";
			username = username;
			password = password;
		};
	elseif auth_type == "bearer" then
		return {
			type = "bearer";
			bearer_token = auth_data;
		};
	end

	return nil;
end

if module:get_host_type() == "component" then
	local component_secret = assert(module:get_option_string("component_secret"), "'component_secret' is a required setting when loaded on a Component");

	function grant_type_handlers.password(params)
		local request_jid = params.username;
		if not request_jid then
			return oauth_error("invalid_request", "missing 'username' (JID)");
		end
		local request_password = params.password
		if not request_password then
			return oauth_error("invalid_request", "missing 'password'");
		end
		local request_username, request_host, request_resource = jid.prepped_split(request_jid);
		if params.scope then
			-- TODO shouldn't we support scopes / roles here?
			return oauth_error("invalid_scope", "unknown scope requested");
		end
		if not request_host or request_host ~= module.host then
			return oauth_error("invalid_request", "invalid JID");
		end
		if request_password == component_secret then
			local granted_jid = jid.join(request_username, request_host, request_resource);
			return json.encode(new_access_token(granted_jid, nil, nil, nil));
		end
		return oauth_error("invalid_grant", "incorrect credentials");
	end

	-- TODO How would this make sense with components?
	-- Have an admin authenticate maybe?
	response_type_handlers.code = nil;
	response_type_handlers.token = nil;
	grant_type_handlers.authorization_code = nil;
end

local function render_error(err)
	return render_page(templates.error, { error = err });
end

-- OAuth errors should be returned to the client if possible, i.e. by
-- appending the error information to the redirect_uri and sending the
-- redirect to the user-agent. In some cases we can't do this, e.g. if
-- the redirect_uri is missing or invalid. In those cases, we render an
-- error directly to the user-agent.
local function error_response(request, redirect_uri, err)
	if not redirect_uri or redirect_uri == oob_uri then
		return render_error(err);
	end
	local params = strict_formdecode(request.url.query);
	if redirect_uri == device_uri then
		local is_device, device_state = verify_device_token(params.state);
		if is_device then
			local device_code = b64url(hashes.hmac_sha256(verification_key, device_state.user_code));
			local code = codes:get("device_code:" .. params.client_id .. "#" .. device_code);
			if type(code) == "table" then
				code.error = err;
				code.expires = os.time() + 60;
				codes:set("device_code:" .. params.client_id .. "#" .. device_code, code);
			end
		end
		return render_error(err);
	end
	local redirect_query = url.parse(redirect_uri);
	local sep = redirect_query.query and "&" or "?";
	redirect_uri = redirect_uri
		.. sep .. http.formencode(err.extra.oauth2_response)
		.. "&" .. http.formencode({ state = params.state, iss = get_issuer() });
	module:log("debug", "Sending error response to client via redirect to %s", redirect_uri);
	return {
		status_code = 303;
		headers = {
			cache_control = "no-store";
			pragma = "no-cache";
			location = redirect_uri;
		};
	};
end

local allowed_grant_type_handlers = module:get_option_set("allowed_oauth2_grant_types", {
	"authorization_code";
	"refresh_token";
	device_uri;
})
if allowed_grant_type_handlers:contains("device_code") then
	-- expand short form because that URI is long
	module:log("debug", "Expanding %q to %q in '%s'", "device_code", device_uri, "allowed_oauth2_grant_types");
	allowed_grant_type_handlers:remove("device_code");
	allowed_grant_type_handlers:add(device_uri);
end
for handler_type in pairs(grant_type_handlers) do
	if not allowed_grant_type_handlers:contains(handler_type) then
		module:log("debug", "Grant type %q disabled", handler_type);
		grant_type_handlers[handler_type] = nil;
	else
		module:log("debug", "Grant type %q enabled", handler_type);
	end
end

-- "token" aka implicit flow is considered insecure
local allowed_response_type_handlers = module:get_option_set("allowed_oauth2_response_types", {"code"})
for handler_type in pairs(response_type_handlers) do
	if not allowed_response_type_handlers:contains(handler_type) then
		module:log("debug", "Response type %q disabled", handler_type);
		response_type_handlers[handler_type] = nil;
	else
		module:log("debug", "Response type %q enabled", handler_type);
	end
end

local allowed_challenge_methods = module:get_option_set("allowed_oauth2_code_challenge_methods", { "S256" })
for handler_type in pairs(verifier_transforms) do
	if not allowed_challenge_methods:contains(handler_type) then
		module:log("debug", "Challenge method %q disabled", handler_type);
		verifier_transforms[handler_type] = nil;
	else
		module:log("debug", "Challenge method %q enabled", handler_type);
	end
end

function handle_token_grant(event)
	local credentials = get_request_credentials(event.request);

	event.response.headers.content_type = "application/json";
	event.response.headers.cache_control = "no-store";
	event.response.headers.pragma = "no-cache";
	local params = strict_formdecode(event.request.body);
	if not params then
		return oauth_error("invalid_request", "Could not parse request body as 'application/x-www-form-urlencoded'");
	end

	if credentials and credentials.type == "basic" then
		-- client_secret_basic converted internally to client_secret_post
		params.client_id = http.urldecode(credentials.username);
		params.client_secret = http.urldecode(credentials.password);
	end

	if not params.client_id then return oauth_error("invalid_request", "missing 'client_id'"); end
	if not params.client_secret then return oauth_error("invalid_request", "missing 'client_secret'"); end

	local client = check_client(params.client_id);
	if not client then
		return oauth_error("invalid_client", "incorrect credentials");
	end

	if not verify_client_secret(params.client_id, params.client_secret) then
		module:log("debug", "client_secret mismatch");
		return oauth_error("invalid_client", "incorrect credentials");
	end


	local grant_type = params.grant_type
	if not array_contains(client.grant_types, grant_type) then
		return oauth_error("invalid_request", "'grant_type' not registered");
	end

	local grant_handler = grant_type_handlers[grant_type];
	if not grant_handler then
		return oauth_error("invalid_request", "'grant_type' not available");
	end

	return grant_handler(params, client);
end

local function handle_authorization_request(event)
	local request = event.request;

	-- Directly returning errors to the user before we have a validated client object
	if not request.url.query then
		return render_error(oauth_error("invalid_request", "Missing query parameters"));
	end
	local params = strict_formdecode(request.url.query);
	if not params then
		return render_error(oauth_error("invalid_request", "Invalid query parameters"));
	end

	if not params.client_id then
		return render_error(oauth_error("invalid_request", "Missing 'client_id' parameter"));
	end

	local client = check_client(params.client_id);

	if not client then
		return render_error(oauth_error("invalid_request", "Invalid 'client_id' parameter"));
	end

	local redirect_uri = get_redirect_uri(client, params.redirect_uri);
	if not redirect_uri then
		return render_error(oauth_error("invalid_request", "Invalid 'redirect_uri' parameter"));
	end
	-- From this point we know that redirect_uri is safe to use

	local response_type = params.response_type;
	if not array_contains(client.response_types, response_type) then
		return error_response(request, redirect_uri, oauth_error("invalid_client", "'response_type' not registered"));
	end
	if not allowed_response_type_handlers:contains(response_type) then
		return error_response(request, redirect_uri, oauth_error("unsupported_response_type", "'response_type' not allowed"));
	end
	local response_handler = response_type_handlers[response_type];
	if not response_handler then
		return error_response(request, redirect_uri, oauth_error("unsupported_response_type"));
	end

	local requested_scopes = parse_scopes(params.scope or "");
	if client.scope then
		local client_scopes = set.new(parse_scopes(client.scope));
		requested_scopes:filter(function(scope)
			return client_scopes:contains(scope);
		end);
	end

	-- The 'prompt' parameter from OpenID Core
	local prompt = set.new(parse_scopes(respect_prompt and params.prompt or "select_account login consent"));

	local auth_state = get_auth_state(request);
	if not auth_state.user then
		if not prompt:contains("login") then
			-- Currently no cookies or such are used, so login is required every time.
			return error_response(request, redirect_uri, oauth_error("login_required"));
		end

		-- Render login page
		local extra = {};
		if params.login_hint then
			extra.username_hint = (jid.prepped_split(params.login_hint) or encodings.stringprep.nodeprep(params.login_hint));
		elseif not prompt:contains("select_account") then
			-- TODO If the login page is split into account selection followed by login
			-- (e.g. password), and then the account selection could be skipped iff the
			-- 'login_hint' parameter is present.
			return error_response(request, redirect_uri, oauth_error("account_selection_required"));
		end
		return render_page(templates.login, { state = auth_state; client = client; extra = extra });
	elseif auth_state.consent == nil then
		local scopes, roles = split_scopes(requested_scopes);
		roles = user_assumable_roles(auth_state.user.username, roles);

		if not prompt:contains("consent") then
			if array_contains(scopes, "offline_access") then
				-- MUST ensure that the prompt parameter contains consent
				return error_response(request, redirect_uri, oauth_error("consent_required"));
			end
			local grants = tokens.get_user_grants(auth_state.user.username);
			local matching_grant;
			if grants then
				for grant_id, grant in pairs(grants) do
					if grant.data and grant.data.oauth2_client and grant.data.oauth2_client.hash == client.client_hash then
						if set.new(parse_scopes(grant.data.oauth2_scopes)) == set.new(scopes+roles) then
							matching_grant = grant_id;
							break
						end
					end
				end
			end

			if not matching_grant then
				return error_response(request, redirect_uri, oauth_error("consent_required"));
			else
				-- Consent for these scopes already granted to this exact client, continue
				auth_state.scopes = scopes + roles;
				auth_state.consent = "granted";
			end

		else
			-- Render consent page
			module:log("debug", "scopes=%q", scopes);
			local scope_choices = array.new(module:get_host_items("openid-claim")):map(function(item)
				if type(item) == "string" then
					return { claim = item };
				elseif type(item) == "table" and type(item.claim) == "string" then
					return item;
				end
			end):filter(function (item)
				if array_contains(scopes, item.claim) then
					module:log("debug", "scopes contains %q", item);
					return true;
				else
					module:log("debug", "scopes contains NO %q", item);
					return false;
				end
			end);
			for _, role in ipairs(roles) do
				if role == "xmpp" then
					scope_choices:push({ claim = role; title = "XMPP";
						description = "Unlimited access to your account, including sending and receiving messages."; });
				else
					scope_choices:push({ claim = role; title = role, description = "Prosody Role" });
				end
			end
			return render_page(templates.consent, { state = auth_state; client = client; scopes = scope_choices }, true);
		end
	elseif not auth_state.consent then
		-- Notify client of rejection
		return error_response(request, redirect_uri, oauth_error("access_denied"));
	end
	-- else auth_state.consent == true

	local granted_scopes = auth_state.scopes
	if client.scope then
		local client_scopes = set.new(parse_scopes(client.scope));
		granted_scopes:filter(function(scope)
			return client_scopes:contains(scope);
		end);
	end

	params.scope = granted_scopes:concat(" ");

	local user_jid = jid.join(auth_state.user.username, module.host);
	local id_token;
	-- https://openid.net/specs/openid-connect-core-1_0.html#rfc.section.3.1.2.1
	if array_contains(granted_scopes, "openid") then
		local client_secret = make_client_secret(params.client_id);
		local id_token_signer = jwt.new_signer("HS256", client_secret);
		id_token = id_token_signer({
			iss = get_issuer(); -- REQUIRED
			sub = url.build({ scheme = "xmpp"; path = user_jid }); -- REQUIRED
			aud = params.client_id; -- REQUIRED
			-- exp REQUIRED, set by util.jwt
			-- iat REQUIRED, set by util.jwt
			auth_time = auth_state.user.iat; -- REQUIRED when Essential Claim, otherwise OPTIONAL
			nonce = params.nonce;
			amr = auth_state.user.amr; -- RFC 8176: Authentication Method Reference Values
		});
	end
	local ret = response_handler(client, params, user_jid, id_token);
	if errors.is_err(ret) then
		return error_response(request, redirect_uri, ret);
	end
	return ret;
end

local function handle_device_authorization_request(event)
	local request = event.request;

	local credentials = get_request_credentials(request);

	local params = strict_formdecode(request.body);
	if not params then
		return render_error(oauth_error("invalid_request", "Invalid query parameters"));
	end

	if credentials and credentials.type == "basic" then
		-- client_secret_basic converted internally to client_secret_post
		params.client_id = http.urldecode(credentials.username);
		local client_secret = http.urldecode(credentials.password);

		if not verify_client_secret(params.client_id, client_secret) then
			module:log("debug", "client_secret mismatch");
			return oauth_error("invalid_client", "incorrect credentials");
		end
	else
		return 401;
	end

	local client = check_client(params.client_id);

	if not client then
		return render_error(oauth_error("invalid_request", "Invalid 'client_id' parameter"));
	end

	if not array_contains(client.grant_types, device_uri) then
		return render_error(oauth_error("invalid_client", "Client not registered for device authorization grant"));
	end

	local requested_scopes = parse_scopes(params.scope or "");
	if client.scope then
		local client_scopes = set.new(parse_scopes(client.scope));
		requested_scopes:filter(function(scope)
			return client_scopes:contains(scope);
		end);
	end

	-- TODO better code generator, this one should be easy to type from a
	-- screen onto a phone
	local user_code = (id.tiny() .. "-" .. id.tiny()):upper();
	local collisions = 0;
	while codes:get("authorization_code:" .. device_uri .. "#" .. user_code) do
		collisions = collisions + 1;
		if collisions > 10 then
			return oauth_error("temporarily_unavailable");
		end
		user_code = (id.tiny() .. "-" .. id.tiny()):upper();
	end
	-- device code should be derivable after consent but not guessable by the user
	local device_code = b64url(hashes.hmac_sha256(verification_key, user_code));
	local verification_uri = module:http_url() .. "/device";
	local verification_uri_complete = verification_uri .. "?" .. http.formencode({ user_code = user_code });

	local expires = os.time() + 600;
	local dc_ok = codes:set("device_code:" .. params.client_id .. "#" .. device_code, { expires = expires });
	local uc_ok = codes:set("user_code:" .. user_code,
		{ user_code = user_code; expires = expires; client_id = params.client_id;
    scope = requested_scopes:concat(" ") });
	if not dc_ok or not uc_ok then
		return oauth_error("temporarily_unavailable");
	end

	return {
		headers = { content_type = "application/json"; cache_control = "no-store"; pragma = "no-cache" };
		body = json.encode {
			device_code = device_code;
			user_code = user_code;
			verification_uri = verification_uri;
			verification_uri_complete = verification_uri_complete;
			expires_in = 600;
			interval = 5;
		};
	}
end

local function handle_device_verification_request(event)
	local request = event.request;
	local params = strict_formdecode(request.url.query);
	if not params or not params.user_code then
		return render_page(templates.device, { client = false });
	end

	local device_info = codes:get("user_code:" .. params.user_code);
	if not device_info or code_expired(device_info) or not codes:set("user_code:" .. params.user_code, nil) then
		return render_page(templates.device, {
			client = false;
			error = oauth_error("expired_token", "Incorrect or expired code");
		});
	end

	return {
		status_code = 303;
		headers = {
			location = module:http_url() .. "/authorize" .. "?" .. http.formencode({
				client_id = device_info.client_id;
				redirect_uri = device_uri;
				response_type = "code";
				scope = device_info.scope;
				state = new_device_token({ user_code = params.user_code });
			});
		};
	}
end

local function handle_introspection_request(event)
	local request = event.request;
	local credentials = get_request_credentials(request);
	if not credentials or credentials.type ~= "basic" then
		event.response.headers.www_authenticate = string.format("Basic realm=%q", module.host.."/"..module.name);
		return 401;
	end
	-- OAuth "client" credentials
	if not verify_client_secret(credentials.username, credentials.password) then
		return 401;
	end

	local client = check_client(credentials.username);
	if not client then
		return 401;
	end

	local form_data = http.formdecode(request.body or "=");
	local token = form_data.token;
	if not token then
		return 400;
	end

	local token_info = tokens.get_token_info(form_data.token);
	if not token_info then
		return { headers = { content_type = "application/json" }; body = json.encode { active = false } };
	end
	local token_client = token_info.grant.data.oauth2_client;
	if not token_client or token_client.hash ~= client.client_hash then
		return 403;
	end

	return {
		headers = { content_type = "application/json" };
		body = json.encode {
			active = true;
			client_id = credentials.username; -- Verified via client hash
			username = jid.node(token_info.jid);
			scope = token_info.grant.data.oauth2_scopes;
			token_type = purpose_map[token_info.purpose];
			exp = token.expires;
			iat = token.created;
			sub = url.build({ scheme = "xmpp"; path = token_info.jid });
			aud = credentials.username;
			iss = get_issuer();
			jti = token_info.id;
		};
	};
end

-- RFC 7009 says that the authorization server should validate that only the client that a token was issued to should be able to revoke it. However
-- this would prevent someone who comes across a leaked token from doing the responsible thing and revoking it, so this is not enforced by default.
local strict_auth_revoke = module:get_option_boolean("oauth2_require_auth_revoke", false);

local function handle_revocation_request(event)
	local request, response = event.request, event.response;
	response.headers.cache_control = "no-store";
	response.headers.pragma = "no-cache";
	local credentials = get_request_credentials(request);
	if credentials then
		if credentials.type ~= "basic" then
			response.headers.www_authenticate = string.format("Basic realm=%q", module.host.."/"..module.name);
			return 401;
		end
		-- OAuth "client" credentials
		if not verify_client_secret(credentials.username, credentials.password) then
			return 401;
		end
		-- TODO check that it's their token I guess?
	elseif strict_auth_revoke then
		-- Why require auth to revoke a leaked token?
		response.headers.www_authenticate = string.format("Basic realm=%q", module.host.."/"..module.name);
		return 401;
	end

	local form_data = strict_formdecode(event.request.body);
	if not form_data or not form_data.token then
		response.headers.accept = "application/x-www-form-urlencoded";
		return 415;
	end

	if credentials then
		local client = check_client(credentials.username);
		if not client then
			return 401;
		end
		local token_info = tokens.get_token_info(form_data.token);
		if not token_info then
			return 404;
		end
		local token_client = token_info.grant.data.oauth2_client;
		if not token_client or token_client.hash ~= client.client_hash then
			return 403;
		end
	end

	local ok, err = tokens.revoke_token(form_data.token);
	if not ok then
		module:log("warn", "Unable to revoke token: %s", tostring(err));
		return 500;
	end
	return 200;
end

local registration_schema = {
	title = "OAuth 2.0 Dynamic Client Registration Protocol";
	description = "This endpoint allows dynamically registering an OAuth 2.0 client.";
	type = "object";
	required = {
		-- These are shown to users in the template
		"client_name";
		"client_uri";
	};
	properties = {
		redirect_uris = {
			title = "List of Redirect URIs";
			type = "array";
			minItems = 1;
			uniqueItems = true;
			items = {
				title = "Redirect URI";
				type = "string";
				format = "uri";
				examples = {
					"https://app.example.com/redirect";
					"http://localhost:8080/redirect";
					"com.example.app:/redirect";
					oob_uri;
				};
				["not"] = {
					const = device_uri;
				}
			};
		};
		token_endpoint_auth_method = {
			title = "Token Endpoint Authentication Method";
			description = "Authentication method the client intends to use. Recommended is `client_secret_basic`. \z
			`none` is only allowed for use with the insecure Implicit flow.";
			type = "string";
			enum = { "none"; "client_secret_post"; "client_secret_basic" };
			default = "client_secret_basic";
		};
		grant_types = {
			title = "Grant Types";
			description = "List of grant types the client intends to use.";
			type = "array";
			minItems = 1;
			uniqueItems = true;
			items = {
				type = "string";
				enum = {
					"authorization_code";
					"implicit";
					"password";
					"client_credentials";
					"refresh_token";
					"urn:ietf:params:oauth:grant-type:jwt-bearer";
					"urn:ietf:params:oauth:grant-type:saml2-bearer";
					device_uri;
				};
			};
			default = { "authorization_code" };
		};
		application_type = {
			title = "Application Type";
			description = "Determines which kinds of redirect URIs the client may register. \z
			The value `web` limits the client to `https://` URLs with the same hostname as \z
			in `client_uri` while the value `native` allows either loopback URLs like \z
			`http://localhost:8080/` or application specific URIs like `com.example.app:/redirect`.";
			type = "string";
			enum = { "native"; "web" };
			default = "web";
		};
		response_types = {
			title = "Response Types";
			type = "array";
			uniqueItems = true;
			items = { type = "string"; enum = { "code"; "token" } };
			default = { "code" };
		};
		client_name = {
			title = "Client Name";
			description = "Human-readable name of the client, presented to the user in the consent dialog.";
			type = "string";
		};
		client_uri = {
			title = "Client URL";
			description = "Should be an link to a page with information about the client. \z
			The hostname in this URL must be the same as in every other '_uri' property.";
			type = "string";
			format = "uri";
			pattern = "^https:";
			examples = { "https://app.example.com/" };
		};
		logo_uri = {
			title = "Logo URL";
			description = "URL to the clients logotype (not currently used).";
			type = "string";
			format = "uri";
			pattern = "^https:";
			examples = { "https://app.example.com/appicon.png" };
		};
		scope = {
			title = "Scopes";
			description = "Space-separated list of scopes the client promises to restrict itself to.";
			type = "string";
			examples = { "openid xmpp" };
		};
		contacts = {
			title = "Contact Addresses";
			description = "Addresses, typically email or URLs where the client developers can be contacted.";
			type = "array";
			minItems = 1;
			items = { type = "string"; format = "email" };
		};
		tos_uri = {
			title = "Terms of Service URL";
			description = "Link to Terms of Service for the client, presented to the user in the consent dialog. \z
			MUST be a `https://` URL with hostname matching that of `client_uri`.";
			type = "string";
			format = "uri";
			pattern = "^https:";
			examples = { "https://app.example.com/tos.html" };
		};
		policy_uri = {
			title = "Privacy Policy URL";
			description = "Link to a Privacy Policy for the client. MUST be a `https://` URL with hostname matching that of `client_uri`.";
			type = "string";
			format = "uri";
			pattern = "^https:";
			examples = { "https://app.example.com/policy.pdf" };
		};
		software_id = {
			title = "Software ID";
			description = "Unique identifier for the client software, common for all instances. Typically an UUID.";
			type = "string";
			format = "uuid";
		};
		software_version = {
			title = "Software Version";
			description = "Version of the client software being registered. \z
			E.g. to allow revoking all related tokens in the event of a security incident.";
			type = "string";
			examples = { "2.3.1" };
		};
	};
}

-- Limit per-locale fields to allowed locales, partly to keep size of client_id
-- down, partly because we don't yet use them for anything.
-- Only relevant for user-visible strings and URIs.
if allowed_locales[1] then
	local props = registration_schema.properties;
	for _, locale in ipairs(allowed_locales) do
		props["client_name#" .. locale] = props["client_name"];
		props["client_uri#" .. locale] = props["client_uri"];
		props["logo_uri#" .. locale] = props["logo_uri"];
		props["tos_uri#" .. locale] = props["tos_uri"];
		props["policy_uri#" .. locale] = props["policy_uri"];
	end
end

local function redirect_uri_allowed(redirect_uri, client_uri, app_type)
	local uri = strict_url_parse(redirect_uri);
	if not uri then
		return false;
	end
	if not uri.scheme then
		return false; -- no relative URLs
	end
	if app_type == "native" then
		return uri.scheme == "http" and loopbacks:contains(uri.host) or redirect_uri == oob_uri or uri.scheme:find(".", 1, true) ~= nil;
	elseif app_type == "web" then
		return uri.scheme == "https" and uri.host == client_uri.host;
	end
end

function create_client(client_metadata)
	local valid, validation_errors = schema.validate(registration_schema, client_metadata);
	if not valid then
		return nil, errors.new({
			type = "modify";
			condition = "bad-request";
			code = 400;
			text = "Failed schema validation.";
			extra = {
				oauth2_response = {
					error = "invalid_request";
					error_description = "Client registration data failed schema validation."; -- TODO Generate from validation_errors?
					-- JSON Schema Output Format
					-- https://json-schema.org/draft/2020-12/draft-bhutton-json-schema-01#name-basic
					valid = false;
					errors = validation_errors;
				};
			};
		});
	end

	local client_uri = strict_url_parse(client_metadata.client_uri);
	if not client_uri or client_uri.scheme ~= "https" or not client_uri.host or loopbacks:contains(client_uri.host) then
		return nil, oauth_error("invalid_client_metadata", "Missing, invalid or insecure client_uri");
	end

	if not client_metadata.application_type then
		if client_metadata.redirect_uris and redirect_uri_allowed(client_metadata.redirect_uris[1], client_uri, "native") then
			client_metadata.application_type = "native";
		elseif array_contains(client_metadata.grant_types, device_uri) then
			client_metadata.application_type = "native";
		end
	end

	-- Fill in default values
	for propname, propspec in pairs(registration_schema.properties) do
		if client_metadata[propname] == nil and type(propspec) == "table" and propspec.default ~= nil then
			client_metadata[propname] = propspec.default;
		end
	end

	-- MUST ignore any metadata that it does not understand
	for propname in pairs(client_metadata) do
		if not registration_schema.properties[propname] then
			client_metadata[propname] = nil;
		end
	end

	if client_metadata.redirect_uris then
		for _, redirect_uri in ipairs(client_metadata.redirect_uris) do
			if not redirect_uri_allowed(redirect_uri, client_uri, client_metadata.application_type) then
				return nil, oauth_error("invalid_redirect_uri", "Invalid, insecure or inappropriate redirect URI.");
			end
		end
	end

	for field, prop_schema in pairs(registration_schema.properties) do
		if field ~= "client_uri" and prop_schema.format == "uri" and client_metadata[field] then
			if not redirect_uri_allowed(client_metadata[field], client_uri, "web") then
				return nil, oauth_error("invalid_client_metadata", "Invalid, insecure or inappropriate informative URI");
			end
		end
	end

	local grant_types = set.new(client_metadata.grant_types);
	local response_types = set.new(client_metadata.response_types);

	if not (grant_types - allowed_grant_type_handlers):empty() then
		return nil, oauth_error("invalid_client_metadata", "Disallowed 'grant_types' specified");
	elseif not (response_types - allowed_response_type_handlers):empty() then
		return nil, oauth_error("invalid_client_metadata", "Disallowed 'response_types' specified");
	end


	if not client_metadata.redirect_uris then
		if grant_types:contains("authorization_code") then
			return nil, oauth_error("invalid_client_metadata", "The 'authorization_code' grant requires 'redirect_uris' to be present.");
		elseif grant_types:contains("implicit") then
			return nil, oauth_error("invalid_client_metadata", "The 'implicit' grant requires 'redirect_uris' to be present.");
		end
	end

	if grant_types:contains("authorization_code") and not response_types:contains("code") then
		return nil, oauth_error("invalid_client_metadata", "Inconsistency between 'grant_types' and 'response_types'");
	elseif grant_types:contains("implicit") and not response_types:contains("token") then
		return nil, oauth_error("invalid_client_metadata", "Inconsistency between 'grant_types' and 'response_types'");
	end

	if client_metadata.token_endpoint_auth_method ~= "none" then
		-- Ensure that each client_id JWT with a client_secret is unique.
		-- A short ID along with the issued at timestamp should be sufficient to
		-- rule out brute force attacks.
		-- Not needed for public clients without a secret, but those are expected
		-- to be uncommon since they can only do the insecure implicit flow.
		client_metadata.nonce = id.short();
	elseif grant_types ~= set.new({ "implicit" }) then
		return nil, oauth_error("invalid_client_metadata", "A 'token_endpoint_auth_method' value of 'none' only works with the 'implicit' grant");
	end

	-- Do we want to keep everything?
	local client_id = sign_client(client_metadata);

	client_metadata.client_id = client_id;
	client_metadata.client_id_issued_at = os.time();

	if client_metadata.token_endpoint_auth_method ~= "none" then
		local client_secret = make_client_secret(client_id);
		client_metadata.client_secret = client_secret;
		client_metadata.client_secret_expires_at = 0;

		if not registration_options.accept_expired then
			client_metadata.client_secret_expires_at = client_metadata.client_id_issued_at + (registration_options.default_ttl or 3600);
		end
	end

	return client_metadata;
end

local function handle_register_request(event)
	local request = event.request;
	local client_metadata, err = json.decode(request.body);
	if err then
		return oauth_error("invalid_request", "Invalid JSON");
	end

	local response, err = create_client(client_metadata);
	if err then return err end

	return {
		status_code = 201;
		headers = {
			cache_control = "no-store";
			pragma = "no-cache";
			content_type = "application/json";
		};
		body = json.encode(response);
	};
end

if not registration_key then
	module:log("info", "No 'oauth2_registration_key', dynamic client registration disabled")
	handle_authorization_request = nil
	handle_register_request = nil
	handle_device_authorization_request = nil
	handle_device_verification_request = nil
end

local function handle_userinfo_request(event)
	local request = event.request;
	local credentials = get_request_credentials(request);
	if not credentials or not credentials.bearer_token then
		module:log("debug", "Missing credentials for UserInfo endpoint: %q", credentials)
		return 401;
	end
	local token_info,err = tokens.get_token_info(credentials.bearer_token);
	if not token_info then
		module:log("debug", "UserInfo query failed token validation: %s", err)
		return 403;
	end
	local scopes = set.new()
	if type(token_info.grant.data) == "table" and type(token_info.grant.data.oauth2_scopes) == "string" then
		scopes:add_list(parse_scopes(token_info.grant.data.oauth2_scopes));
	else
		module:log("debug", "token_info = %q", token_info)
	end

	if not scopes:contains("openid") then
		module:log("debug", "Missing the 'openid' scope in %q", scopes)
		-- The 'openid' scope is required for access to this endpoint.
		return 403;
	end

	local user_info = {
		iss = get_issuer();
		sub = url.build({ scheme = "xmpp"; path = token_info.jid });
	}

	local token_claims = set.intersection(openid_claims, scopes);
	token_claims:remove("openid"); -- that's "iss" and "sub" above
	if not token_claims:empty() then
		-- Another module can do that
		module:fire_event("token/userinfo", {
			token = token_info;
			claims = token_claims;
			username = jid.split(token_info.jid);
			userinfo = user_info;
		});
	end

	return {
		status_code = 200;
		headers = { content_type = "application/json" };
		body = json.encode(user_info);
	};
end

module:depends("http");
module:provides("http", {
	cors = { enabled = true; credentials = true };
	route = {
		-- OAuth 2.0 in 5 simple steps!
		-- This is the normal 'authorization_code' flow.

		-- Step 1. Create OAuth client
		["GET /register"] = { headers = { content_type = "application/schema+json" }; body = json.encode(registration_schema) };
		["POST /register"] = handle_register_request;

		-- Device flow
		["POST /device"] = handle_device_authorization_request;
		["GET /device"] = handle_device_verification_request;

		-- Step 2. User-facing login and consent view
		["GET /authorize"] = handle_authorization_request;
		["POST /authorize"] = handle_authorization_request;
		["OPTIONS /authorize"] = { status_code = 403; body = "" };

		-- Optional static content for templates
		["GET /style.css"] = templates.css and {
			headers = {
				["Content-Type"] = "text/css";
			};
			body = templates.css;
		} or nil;
		["GET /script.js"] = templates.js and {
			headers = {
				["Content-Type"] = "text/javascript";
			};
			body = templates.js;
		} or nil;

		-- Step 3. User is redirected to the 'redirect_uri' along with an
		-- authorization code.  In the insecure 'implicit' flow, the access token
		-- is delivered here.

		-- Step 4. Retrieve access token using the code.
		["POST /token"] = handle_token_grant;
		["GET /token"] = function() return 405; end;

		-- Step 4 is later repeated using the refresh token to get new access tokens.

		-- Get info about a token
		["POST /introspect"] = handle_introspection_request;
		["GET /introspect"] = function() return 405; end;

		-- Get info about the user, used for OpenID Connect
		["GET /userinfo"] = handle_userinfo_request;

		-- Step 5. Revoke token (access or refresh)
		["POST /revoke"] = handle_revocation_request;
		["GET /revoke"] = function() return 405; end;
	};
});

local http_server = require "net.http.server";

module:hook_object_event(http_server, "http-error", function (event)
	local oauth2_response = event.error and event.error.extra and event.error.extra.oauth2_response;
	if not oauth2_response then
		return;
	end
	event.response.headers.content_type = "application/json";
	event.response.status_code = event.error.code or 400;
	return json.encode(oauth2_response);
end, 5);

-- OIDC Discovery

function get_authorization_server_metadata()
	if authorization_server_metadata then
		return authorization_server_metadata;
	end
	authorization_server_metadata = {
		-- RFC 8414: OAuth 2.0 Authorization Server Metadata
		issuer = get_issuer();
		authorization_endpoint = handle_authorization_request and module:http_url() .. "/authorize" or nil;
		token_endpoint = handle_token_grant and module:http_url() .. "/token" or nil;
		jwks_uri = nil; -- REQUIRED in OpenID Discovery but not in OAuth 2.0 Metadata
		registration_endpoint = handle_register_request and module:http_url() .. "/register" or nil;
		scopes_supported = array({ "xmpp" }):append(array(it.keys(usermanager.get_all_roles(module.host)))):append(array(openid_claims:items()));
		response_types_supported = array(it.keys(response_type_handlers));
		response_modes_supported = array(it.keys(response_type_handlers)):map(tmap { token = "fragment"; code = "query" });
		grant_types_supported = array(it.keys(grant_type_handlers));
		token_endpoint_auth_methods_supported = array({ "client_secret_basic"; "client_secret_post"; "none" });
		token_endpoint_auth_signing_alg_values_supported = nil;
		service_documentation = module:get_option_string("oauth2_service_documentation", "https://modules.prosody.im/mod_http_oauth2.html");
		ui_locales_supported = allowed_locales[1] and allowed_locales;
		op_policy_uri = module:get_option_string("oauth2_policy_url", nil);
		op_tos_uri = module:get_option_string("oauth2_terms_url", nil);
		revocation_endpoint = handle_revocation_request and module:http_url() .. "/revoke" or nil;
		revocation_endpoint_auth_methods_supported = array({ "client_secret_basic"; "client_secret_post"; "none" });
		revocation_endpoint_auth_signing_alg_values_supported = nil;
		introspection_endpoint = handle_introspection_request and module:http_url() .. "/introspect";
		introspection_endpoint_auth_methods_supported = nil;
		introspection_endpoint_auth_signing_alg_values_supported = nil;
		code_challenge_methods_supported = array(it.keys(verifier_transforms));

		-- RFC 8628: OAuth 2.0 Device Authorization Grant
		device_authorization_endpoint = handle_device_authorization_request and module:http_url() .. "/device";

		-- RFC 9207: OAuth 2.0 Authorization Server Issuer Identification
		authorization_response_iss_parameter_supported = true;

		-- OpenID Connect Discovery 1.0
		userinfo_endpoint = handle_userinfo_request and module:http_url() .. "/userinfo" or nil;
		id_token_signing_alg_values_supported = { "HS256" }; -- The algorithm RS256 MUST be included, but we use HS256 and client_secret as shared key.
	}
	return authorization_server_metadata;
end

module:provides("http", {
	name = "oauth2-discovery";
	default_path = "/.well-known/oauth-authorization-server";
	cors = { enabled = true };
	route = {
		["GET"] = function()
			return {
				headers = { content_type = "application/json" };
				body = json.encode(get_authorization_server_metadata());
			}
		end
	};
});

module:shared("tokenauth/oauthbearer_config").oidc_discovery_url = module:http_url("oauth2-discovery", "/.well-known/oauth-authorization-server");
