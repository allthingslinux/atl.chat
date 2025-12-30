-- RESTful API
--
-- Copyright (c) 2019-2022 Kim Alvefur
--
-- This file is MIT/X11 licensed.

local encodings = require "util.encodings";
local base64 = encodings.base64;
local errors = require "util.error";
local http = require "net.http";
local id = require "util.id";
local jid = require "util.jid";
local json = require "util.json";
local st = require "util.stanza";
local um = require "core.usermanager";
local xml = require "util.xml";
local have_cbor, cbor = pcall(require, "cbor");

local jsonmap = module:require"jsonmap";

local tokens = module:depends("tokenauth");

-- Lower than the default c2s size limit to account for possible JSON->XML size increase
local stanza_size_limit = module:get_option_number("rest_stanza_size_limit", 1024 * 192);

local auth_mechanisms = module:get_option_set("rest_auth_mechanisms", { "Basic", "Bearer" }) / string.lower;

local www_authenticate_header;
do
	local header, realm = {}, module.host.."/"..module.name;
	for mech in auth_mechanisms do
		header[#header+1] = ("%s realm=%q"):format(mech, realm);
	end
	www_authenticate_header = table.concat(header, ", ");
end

local post_errors = errors.init("mod_rest", {
	noauthz = { code = 401; type = "auth"; condition = "not-authorized"; text = "No credentials provided" };
	unauthz = { code = 403; type = "auth"; condition = "not-authorized"; text = "Credentials not accepted" };
	malformauthz = { code = 403; type = "auth"; condition = "not-authorized"; text = "Credentials malformed" };
	prepauthz = { code = 403; type = "auth"; condition = "not-authorized"; text = "Credentials failed stringprep" };
	parse = { code = 400; type = "modify"; condition = "not-well-formed"; text = "Failed to parse payload" };
	xmlns = { code = 422; type = "modify"; condition = "invalid-namespace"; text = "'xmlns' attribute must be empty" };
	name = { code = 422; type = "modify"; condition = "unsupported-stanza-type"; text = "Invalid stanza, must be 'message', 'presence' or 'iq'." };
	to = { code = 422; type = "modify"; condition = "improper-addressing"; text = "Invalid destination JID" };
	from = { code = 422; type = "modify"; condition = "invalid-from"; text = "Invalid source JID" };
	from_auth = { code = 403; type = "auth"; condition = "not-authorized"; text = "Not authorized to send stanza with requested 'from'" };
	iq_type = { code = 422; type = "modify"; condition = "invalid-xml"; text = "'iq' stanza must be of type 'get' or 'set'" };
	iq_tags = { code = 422; type = "modify"; condition = "bad-format"; text = "'iq' stanza must have exactly one child tag" };
	mediatype = { code = 415; type = "cancel"; condition = "bad-format"; text = "Unsupported media type" };
	size = { code = 413; type = "modify"; condition = "resource-constraint", text = "Payload too large" };
});

local token_session_errors = errors.init("mod_tokenauth", {
	["internal-error"] = { code = 500; type = "wait"; condition = "internal-server-error" };
	["invalid-token-format"] = { code = 403; type = "auth"; condition = "not-authorized"; text = "Credentials malformed" };
	["not-authorized"] = { code = 403; type = "auth"; condition = "not-authorized"; text = "Credentials not accepted" };
});

local function check_credentials(request) -- > session | boolean, error
	local auth_type, auth_data = string.match(request.headers.authorization, "^(%S+)%s(.+)$");
	auth_type = auth_type and auth_type:lower();
	if not (auth_type and auth_data) or not auth_mechanisms:contains(auth_type) then
		return nil, post_errors.new("noauthz", { request = request });
	end

	if auth_type == "basic" and module:get_host_type() == "local" then
		local creds = base64.decode(auth_data);
		if not creds then
			return nil, post_errors.new("malformauthz", { request = request });
		end
		local username, password = string.match(creds, "^([^:]+):(.*)$");
		if not username then
			return nil, post_errors.new("malformauthz", { request = request });
		end
		username, password = encodings.stringprep.nodeprep(username), encodings.stringprep.saslprep(password);
		if not username or not password then
			return false, post_errors.new("prepauthz", { request = request });
		end
		if not um.test_password(username, module.host, password) then
			return false, post_errors.new("unauthz", { request = request });
		end
		return { username = username; host = module.host };
	elseif auth_type == "basic" and module:get_host_type() == "component" then
		local component_secret = module:get_option_string("component_secret");
		local creds = base64.decode(auth_data);
		if creds ~= module.host .. ":" .. component_secret then
			return nil, post_errors.new("malformauthz", { request = request });
		end
		return { host = module.host };
	elseif auth_type == "bearer" then
		if tokens.get_token_session then
			local token_session, err = tokens.get_token_session(auth_data);
			if not token_session then
				return false, token_session_errors.new(err or "not-authorized", { request = request });
			end
			return token_session;
		else -- COMPAT w/0.12
			local token_info = tokens.get_token_info(auth_data);
			if not token_info or not token_info.session then
				return false, post_errors.new("unauthz", { request = request });
			end
			return token_info.session;
		end
	end
	return nil, post_errors.new("noauthz", { request = request });
end

if module:get_option_string("authentication") == "anonymous" and module:get_option_boolean("anonymous_rest") then
	www_authenticate_header = nil;
	function check_credentials(request) -- luacheck: ignore 212/request
		return {
			username = id.medium():lower();
			host = module.host;
		}
	end
end

local function event_suffix(jid_to)
	local node, _, resource = jid.split(jid_to);
	if node then
		if resource then
			return '/full';
		else
			return '/bare';
		end
	else
		return '/host';
	end
end


-- TODO This ought to be handled some way other than duplicating this
-- core.stanza_router code here.
local function compat_preevents(origin, stanza) --> boolean : handled
	local to = stanza.attr.to;
	local node, host, resource = jid.split(to);

	local to_type, to_self;
	if node then
		if resource then
			to_type = '/full';
		else
			to_type = '/bare';
			if node == origin.username and host == origin.host then
				stanza.attr.to = nil;
				to_self = true;
			end
		end
	else
		if host then
			to_type = '/host';
		else
			to_type = '/bare';
			to_self = true;
		end
	end

	local event_data = { origin = origin; stanza = stanza; to_self = to_self };

	local result = module:fire_event("pre-stanza", event_data);
	if result ~= nil then return true end
	if module:fire_event('pre-' .. stanza.name .. to_type, event_data) then return true; end -- do preprocessing
	return false
end

-- (table, string) -> table
local function amend_from_path(data, path)
	local st_kind, st_type, st_to = path:match("^([mpi]%w+)/([%w_]+)/(.*)$");
	if not st_kind then return; end
	if st_kind == "iq" and st_type ~= "get" and st_type ~= "set" then
		-- GET /iq/disco/jid
		data = {
			kind = "iq";
			[st_type] = st_type == "ping" or data or {};
		};
	else
		data.kind = st_kind;
		data.type = st_type;
	end
	if st_to and st_to ~= "" then
		data.to = st_to;
	end
	return data;
end

local function parse(mimetype, data, path) --> Stanza, error enum
	mimetype = mimetype and mimetype:match("^[^; ]*");
	if mimetype == "application/xmpp+xml" then
		return xml.parse(data);
	elseif mimetype == "application/json" then
		local parsed, err = json.decode(data);
		if not parsed then
			return parsed, err;
		end
		if path then
			parsed = amend_from_path(parsed, path);
			if not parsed then return nil, "invalid-path"; end
		end
		return jsonmap.json2st(parsed);
	elseif mimetype == "application/cbor" and have_cbor then
		local parsed, err = cbor.decode(data);
		if not parsed then
			return parsed, err;
		end
		return jsonmap.json2st(parsed);
	elseif mimetype == "application/x-www-form-urlencoded"then
		local parsed = http.formdecode(data);
		if type(parsed) == "string" then
			-- This should reject GET /iq/query/to?messagebody
			if path then
				return nil, "invalid-query";
			end
			return parse("text/plain", parsed);
		end
		for i = #parsed, 1, -1 do
			parsed[i] = nil;
		end
		if path then
			parsed = amend_from_path(parsed, path);
			if not parsed then return nil, "invalid-path"; end
		end
		return jsonmap.json2st(parsed);
	elseif mimetype == "text/plain" then
		if not path then
			return st.message({ type = "chat" }, data);
		end
		local parsed = {};
		if path then
			parsed = amend_from_path(parsed, path);
			if not parsed then return nil, "invalid-path"; end
		end
		if parsed.kind == "message" then
			parsed.body = data;
		elseif parsed.kind == "presence" then
			parsed.show = data;
		else
			return nil, "invalid-path";
		end
		return jsonmap.json2st(parsed);
	elseif not mimetype and path then
		local parsed = amend_from_path({}, path);
		if not parsed then return nil, "invalid-path"; end
		return jsonmap.json2st(parsed);
	end
	return nil, "unknown-payload-type";
end

local function decide_type(accept, supported_types)
	-- assumes the accept header is sorted
	local ret = supported_types[1];
	for i = 2, #supported_types do
		if (accept:find(supported_types[i], 1, true) or 1000) < (accept:find(ret, 1, true) or 1000) then
			ret = supported_types[i];
		end
	end
	return ret;
end

local supported_inputs = {
	"application/xmpp+xml",
	"application/json",
	"application/x-www-form-urlencoded",
	"text/plain",
};

local supported_outputs = {
	"application/xmpp+xml",
	"application/json",
	"application/x-www-form-urlencoded",
};

if have_cbor then
	table.insert(supported_inputs, "application/cbor");
	table.insert(supported_outputs, "application/cbor");
end

-- Only { string : string } can be form-encoded, discard the rest
-- (jsonmap also discards anything unknown or unsupported)
local function flatten(t)
	local form = {};
	for k, v in pairs(t) do
		if type(v) == "string" then
			form[k] = v;
		elseif type(v) == "number" then
			form[k] = tostring(v);
		elseif v == true then
			form[k] = "";
		end
	end
	return form;
end

local function encode(type, s)
	if type == "text/plain" then
		return s:get_child_text("body") or "";
	elseif type == "application/xmpp+xml" then
		return tostring(s);
	end
	local mapped, err = jsonmap.st2json(s);
	if not mapped then return mapped, err; end
	if type == "application/json" then
		return json.encode(mapped);
	elseif type == "application/x-www-form-urlencoded" then
		return http.formencode(flatten(mapped));
	elseif type == "application/cbor" then
		return cbor.encode(mapped);
	end
	error "unsupported encoding";
end

-- GET → iq-get
local function parse_request(request, path)
	if path and request.method == "GET" then
		-- e.g. /version/{to}
		if request.url.query then
			return parse("application/x-www-form-urlencoded", request.url.query, "iq/"..path);
		end
		return parse(nil, nil, "iq/"..path);
	else
		return parse(request.headers.content_type, request.body, path);
	end
end

local function handle_request(event, path)
	local request, response = event.request, event.response;
	local log = request.log or module._log;
	local from;
	local origin;
	local echo = path == "echo";
	if echo then path = nil; end

	if not request.headers.authorization and www_authenticate_header then
		response.headers.www_authenticate = www_authenticate_header;
		return post_errors.new("noauthz");
	else
		local err;
		origin, err = check_credentials(request);
		if not origin then
			return err or post_errors.new("unauthz");
		end
		from = jid.join(origin.username, origin.host, origin.resource);
		origin.full_jid = from;
		origin.type = "c2s";
		origin.log = log;
	end
	if type(request.body) == "string" and #request.body > stanza_size_limit then
		return post_errors.new("size", { size = #request.body; limit = stanza_size_limit });
	end
	local payload, err = parse_request(request, path);
	if not payload then
		-- parse fail
		local ctx = { error = err, type = request.headers.content_type, data = request.body, };
		if err == "unknown-payload-type" then
			return post_errors.new("mediatype", ctx);
		end
		return post_errors.new("parse", ctx);
	end

	if (payload.attr.xmlns or "jabber:client") ~= "jabber:client" then
		return post_errors.new("xmlns");
	elseif payload.name ~= "message" and payload.name ~= "presence" and payload.name ~= "iq" then
		return post_errors.new("name");
	end

	local to = jid.prep(payload.attr.to);
	if payload.attr.to and not to then
		return post_errors.new("to");
	end

	if payload.attr.from then
		local requested_from = jid.prep(payload.attr.from);
		if not requested_from then
			return post_errors.new("from");
		end
		if jid.compare(requested_from, from) then
			from = requested_from;
		else
			return post_errors.new("from_auth");
		end
	end

	payload.attr = {
		from = from,
		to = to,
		id = payload.attr.id or id.medium(),
		type = payload.attr.type,
		["xml:lang"] = payload.attr["xml:lang"],
	};

	log("debug", "Received[rest]: %s", payload:top_tag());
	local send_type = decide_type((request.headers.accept or "") ..",".. (request.headers.content_type or ""), supported_outputs)

	if echo then
		local ret, err = errors.coerce(encode(send_type, payload));
		if not ret then return err; end
		response.headers.content_type = send_type;
		return ret;
	end

	if payload.name == "iq" then
		local responses = st.stanza("xmpp");
		function origin.send(stanza)
			responses:add_direct_child(stanza);
		end
		if compat_preevents(origin, payload) then return 202; end

		if payload.attr.type ~= "get" and payload.attr.type ~= "set" then
			return post_errors.new("iq_type");
		elseif #payload.tags ~= 1 then
			return post_errors.new("iq_tags");
		end

		-- special handling of multiple responses to MAM queries primarily from
		-- remote hosts, local go directly to origin.send()
		local archive_event_name = "message"..event_suffix(from);
		local archive_handler;
		local archive_query = payload:get_child("query", "urn:xmpp:mam:2");
		if archive_query then
			archive_handler = function(result_event)
				if result_event.stanza:find("{urn:xmpp:mam:2}result/@queryid") == archive_query.attr.queryid then
					origin.send(result_event.stanza);
					return true;
				end
			end
			module:hook(archive_event_name, archive_handler, 1);
		end

		local iq_timeout = tonumber(request.headers.prosody_rest_timeout) or module:get_option_number("rest_iq_timeout", 60*2);
		iq_timeout = math.min(iq_timeout, module:get_option_number("rest_iq_max_timeout", 300));

		local p = module:send_iq(payload, origin, iq_timeout):next(
			function (result)
				log("debug", "Sending[rest]: %s", result.stanza:top_tag());
				response.headers.content_type = send_type;
				if responses[1] then
					local tail = responses[#responses];
					if tail.name ~= "iq" or tail.attr.from ~= result.stanza.attr.from or tail.attr.id ~= result.stanza.attr.id then
						origin.send(result.stanza);
					end
				end
				if responses[2] then
					return encode(send_type, responses);
				end
				return encode(send_type, result.stanza);
			end,
			function (error)
				if not errors.is_err(error) then
					log("error", "Uncaught native error: %s", error);
					return select(2, errors.coerce(nil, error));
				elseif error.context and error.context.stanza then
					response.headers.content_type = send_type;
					log("debug", "Sending[rest]: %s", error.context.stanza:top_tag());
					return encode(send_type, error.context.stanza);
				else
					return error;
				end
			end);

		if archive_handler then
			p:finally(function ()
				module:unhook(archive_event_name, archive_handler);
			end)
		end

		return p;
	else
		function origin.send(stanza)
			log("debug", "Sending[rest]: %s", stanza:top_tag());
			response.headers.content_type = send_type;
			response:send(encode(send_type, stanza));
			return true;
		end
		if compat_preevents(origin, payload) then return 202; end

		module:send(payload, origin);
		return 202;
	end
end

module:depends("http");

local demo_handlers = {};
if module:get_option_path("rest_demo_resources", nil) then
	demo_handlers = module:require"apidemo";
end

-- Handle stanzas submitted via HTTP
module:provides("http", {
		route = {
			POST = handle_request;
			["POST /*"] = handle_request;
			["GET /*"] = handle_request;

			-- Only if api_demo_resources are set
			["GET /"] = demo_handlers.redirect;
			["GET /demo/"] = demo_handlers.main_page;
			["GET /demo/openapi.yaml"] = demo_handlers.schema;
			["GET /demo/*"] = demo_handlers.resources;
		};
	});

function new_webhook(rest_url, send_type)
	local function get_url() return rest_url; end
	if rest_url:find("%b{}") then
		local httputil = require "util.http";
		local render_url = require"util.interpolation".new("%b{}", httputil.urlencode);
		function get_url(stanza)
			local at = stanza.attr;
			return render_url(rest_url, { kind = stanza.name, type = at.type, to = at.to, from = at.from });
		end
	end
	if send_type == "json" then
		send_type = "application/json";
	end

	module:set_status("info", "Not yet connected");
	http.request(get_url(st.stanza("meta", { type = "info", to = module.host, from = module.host })), {
			method = "OPTIONS",
		}, function (body, code, response)
			if code == 0 then
				module:log_status("error", "Could not connect to callback URL %q: %s", rest_url, body);
			elseif code == 200 then
				module:set_status("info", "Connected");
				if response.headers.accept then
					send_type = decide_type(response.headers.accept, supported_outputs);
					module:log("debug", "Set 'rest_callback_content_type' = %q based on Accept header", send_type);
				end
			else
				module:log_status("warn", "Unexpected response code %d from OPTIONS probe", code);
				module:log("warn", "Endpoint said: %s", body);
			end
		end);

	local code2err = require "net.http.errors".registry;

	local function handle_stanza(event)
		local stanza, origin = event.stanza, event.origin;
		local reply_allowed = stanza.attr.type ~= "error" and stanza.attr.type ~= "result";
		local reply_needed = reply_allowed and stanza.name == "iq";
		local receipt;

		if reply_allowed and stanza.name == "message" and stanza.attr.id and stanza:get_child("urn:xmpp:receipts", "request") then
			reply_needed = true;
			receipt = st.stanza("received", { xmlns = "urn:xmpp:receipts", id = stanza.id });
		end

		local request_body = encode(send_type, stanza);

		-- Keep only the top level element and let the rest be GC'd
		stanza = st.clone(stanza, true);

		module:log("debug", "Sending[rest]: %s", stanza:top_tag());
		http.request(get_url(stanza), {
				body = request_body,
				headers = {
					["Content-Type"] = send_type,
					["Content-Language"] = stanza.attr["xml:lang"],
					Accept = table.concat(supported_inputs, ", ");
				},
			}):next(function (response)
				module:set_status("info", "Connected");
				local reply;

				local code, body = response.code, response.body;
				if not reply_allowed then
					return;
				elseif code == 202 or code == 204 then
					if not reply_needed then
						-- Delivered, no reply
						return;
					end
				else
					local parsed, err = parse(response.headers["content-type"], body);
					if not parsed then
						module:log("warn", "Failed parsing data from REST callback: %s, %q", err, body);
					elseif parsed.name ~= stanza.name then
						module:log("warn", "REST callback responded with the wrong stanza type, got %s but expected %s", parsed.name, stanza.name);
					else
						parsed.attr = {
							from = stanza.attr.to,
							to = stanza.attr.from,
							id = parsed.attr.id or id.medium();
							type = parsed.attr.type,
							["xml:lang"] = parsed.attr["xml:lang"],
						};
						if parsed.name == "message" and parsed.attr.type == "groupchat" then
							parsed.attr.to = jid.bare(stanza.attr.from);
						end
						if not stanza.attr.type and parsed:get_child("error") then
							parsed.attr.type = "error";
						end
						if parsed.attr.type == "error" then
							parsed.attr.id = stanza.attr.id;
						elseif parsed.name == "iq" then
							parsed.attr.id = stanza.attr.id;
							parsed.attr.type = "result";
						end
						reply = parsed;
					end
				end

				if not reply then
					local code_hundreds = code - (code % 100);
					if code_hundreds == 200 then
						reply = st.reply(stanza);
						if stanza.name ~= "iq" then
							reply.attr.id = id.medium();
						end
						-- TODO presence/status=body ?
					elseif code2err[code] then
						reply = st.error_reply(stanza, errors.new(code, nil, code2err));
					elseif code_hundreds == 400 then
						reply = st.error_reply(stanza, "modify", "bad-request", body);
					elseif code_hundreds == 500 then
						reply = st.error_reply(stanza, "cancel", "internal-server-error", body);
					else
						reply = st.error_reply(stanza, "cancel", "undefined-condition", body);
					end
				end

				if receipt then
					reply:add_direct_child(receipt);
				end

				module:log("debug", "Received[rest]: %s", reply:top_tag());

				origin.send(reply);
			end,
			function (err)
				module:log_status("error", "Could not connect to callback URL %q: %s", rest_url, err);
				origin.send(st.error_reply(stanza, "wait", "recipient-unavailable", err.text));
			end):catch(function (err)
				module:log("error", "Error[rest]: %s", err);
			end);

		return true;
	end

	return handle_stanza;
end

-- Forward stanzas from XMPP to HTTP and return any reply
local rest_url = module:get_option_string("rest_callback_url", nil);
if rest_url then
	local send_type = module:get_option_string("rest_callback_content_type", "application/xmpp+xml");

	local handle_stanza = new_webhook(rest_url, send_type);

	local send_kinds = module:get_option_set("rest_callback_stanzas", { "message", "presence", "iq" });

	local event_presets = {
		-- Don't override everything on normal VirtualHosts by default
		["local"] = { "host" },
		-- Comonents get to handle all kinds of stanzas
		["component"] = { "bare", "full", "host" },
	};
	local hook_events = module:get_option_set("rest_callback_events", event_presets[module:get_host_type()]);
	for kind in send_kinds do
		for event in hook_events do
			module:hook(kind.."/"..event, handle_stanza, -1);
		end
	end
end

local supported_errors = {
	"text/html",
	"application/xmpp+xml",
	"application/json",
};

-- strip some stuff, notably the optional traceback table that casues stack overflow in util.json
local function simplify_error(e)
	if not e then return end
	return {
		type = e.type;
		condition = e.condition;
		text = e.text;
		extra = e.extra;
		source = e.source;
	};
end

local http_server = require "net.http.server";
module:hook_object_event(http_server, "http-error", function (event)
	local request, response = event.request, event.response;
	local response_as = decide_type(request and request.headers.accept or "", supported_errors);
	if response_as == "application/xmpp+xml" then
		if response then
			response.headers.content_type = "application/xmpp+xml";
		end
		local stream_error = st.stanza("error", { xmlns = "http://etherx.jabber.org/streams" });
		if event.error then
			stream_error:tag(event.error.condition, {xmlns = 'urn:ietf:params:xml:ns:xmpp-streams' }):up();
			if event.error.text then
				stream_error:text_tag("text", event.error.text, {xmlns = 'urn:ietf:params:xml:ns:xmpp-streams' });
			end
		end
		return tostring(stream_error);
	elseif response_as == "application/json" then
		if response then
			response.headers.content_type = "application/json";
		end
		return json.encode({
				type = "error",
				error = simplify_error(event.error),
				code = event.code,
			});
	end
end, 1);
