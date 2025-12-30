module:depends("http");

local st = require "util.stanza";
local json = require "util.json";
local xml = require "util.xml";
local http = require "net.http";
local uuid_generate = require "util.uuid".generate;
local timestamp_generate = require "util.datetime".datetime;
local hashes = require "util.hashes";
local from_hex = require "util.hex".from;
local hmacs = {
	sha1 = hashes.hmac_sha1;
	sha256 = hashes.hmac_sha256;
	sha384 = hashes.hmac_sha384;
	sha512 = hashes.hmac_sha512;
};

local pubsub_service = module:depends("pubsub").service;

local mappings = module:get_option("pubsub_post_mappings", nil);
local datamapper;
if type(mappings) == "table" then
	datamapper = require "util.datamapper";
	for node, f in pairs(mappings) do
		if type(f) == "string" then
			local fh = assert(module:load_resource(f));
			mappings[node] = assert(json.parse(fh:read("*a")));
			fh:close()
		end
	end
end

local function wrap(node, parsed, raw)
	if mappings and mappings[node] then
		return datamapper.unparse(mappings[node], parsed)
	end
	return st.stanza("json", { xmlns="urn:xmpp:json:0" }):text(raw);
end

local error_mapping = {
	["forbidden"] = 403;
	["item-not-found"] = 404;
	["internal-server-error"] = 500;
	["conflict"] = 409;
};

local function publish_payload(node, actor, item_id, payload)
	local post_item = st.stanza("item", { xmlns = "http://jabber.org/protocol/pubsub", id = item_id, })
		:add_child(payload);
	local ok, err = pubsub_service:publish(node, actor, item_id, post_item);
	module:log("debug", ":publish(%q, true, %q, %s) -> %q", node, item_id, payload:top_tag(), err or "");
	if not ok then
		return error_mapping[err] or 500;
	end
	return 202;
end

local function handle_json(node, actor, data)
	local parsed, err = json.decode(data);
	if not parsed then
		return { status_code = 400; body = tostring(err); }
	end
	if type(parsed) ~= "table" then
		return { status_code = 400; body = "object or array expected"; };
	end
	local payload = wrap(node, parsed, data)
	local item_id = "current";
	if payload.attr["http://jabber.org/protocol/pubsub\1id"] then
		item_id = payload.attr["http://jabber.org/protocol/pubsub\1id"];
		payload.attr["http://jabber.org/protocol/pubsub\1id"] = nil;
	elseif type(parsed.id) == "string" then
		item_id = parsed.id;
	end
	return publish_payload(node, actor, item_id, payload);
end

local function publish_atom(node, actor, feed)
	for entry in feed:childtags("entry") do
		local item_id = entry:get_child_text("id");
		if not item_id then
			item_id = uuid_generate();
			entry:tag("id"):text(item_id):up();
		end
		if not entry:get_child_text("published") then
			entry:tag("published"):text(timestamp_generate()):up();
		end
		local resp = publish_payload(node, actor, item_id, entry);
		if resp ~= 202 then return resp; end
	end
	return 202;
end

local function handle_xml(node, actor, payload)
	local xmlpayload, err = xml.parse(payload);
	if not xmlpayload then
		module:log("debug", "XML parse error: %s\n%q", err, payload);
		return { status_code = 400, body = tostring(err) };
	end
	if xmlpayload.attr.xmlns == "http://www.w3.org/2005/Atom" and xmlpayload.name == "feed" then
		return publish_atom(node, actor, xmlpayload);
	else
		return publish_payload(node, actor, "current", xmlpayload);
	end
end

local function handle_urlencoded(node, actor, data)
	local parsed = http.formdecode(data);
	if type(parsed) ~= "table" then return {status_code = 400; body = "invalid payload"}; end
	for i = 1, #parsed do parsed[i] = nil; end

	local payload = wrap(node, parsed, json.encode(parsed));
	local item_id = "current";
	if payload.attr["http://jabber.org/protocol/pubsub\1id"] then
		item_id = payload.attr["http://jabber.org/protocol/pubsub\1id"];
		payload.attr["http://jabber.org/protocol/pubsub\1id"] = nil;
	elseif type(parsed.id) == "string" then
		item_id = parsed.id;
	end
	return publish_payload(node, actor, item_id, payload);
end

local actor_source = module:get_option_string("pubsub_post_actor"); -- COMPAT
local default_secret = module:get_option_string("pubsub_post_default_secret");
local actor_secrets = module:get_option("pubsub_post_secrets");
local actors = module:get_option("pubsub_post_actors");
local default_actor = module:get_option_string("pubsub_post_default_actor");
if not default_actor and actor_source == "superuser" then
	default_actor = true;
end

local function verify_signature(secret, body, signature)
	if not signature then return false; end
	local algo, digest = signature:match("^([^=]+)=(%x+)");
	if not algo then return false; end
	local hmac = hmacs[algo];
	if not algo then return false; end
	return hmac(secret, body) == from_hex(digest);
end

function handle_POST(event, path)
	local request = event.request;

	local content_type = request.headers.content_type or "application/octet-stream";
	local actor = actors and actors[path] or default_actor or request.ip;
	local secret = actor_secrets and actor_secrets[path] or default_secret;

	module:log("debug", "Handling POST to node %q by %q with %q: \n%s\n", path, actor, content_type, request.body);

	if secret and not verify_signature(secret, request.body, request.headers.x_hub_signature) then
		module:log("debug", "Signature validation failed");
		return 401;
	end

	if not actor then
		return 401;
	end

	if content_type == "application/xml" or content_type:sub(-4) == "+xml" then
		return handle_xml(path, actor, request.body);
	elseif content_type == "application/json" or content_type:sub(-5) == "+json" then
		return handle_json(path, actor, request.body);
	elseif content_type == "application/x-www-form-urlencoded" then
		return handle_urlencoded(path, actor, request.body);
	end

	module:log("debug", "Unsupported content-type: %q", content_type);
	return 415;
end

module:provides("http", {
	route = {
		["POST /*"] = handle_POST;
	};
});

function module.load()
	module:log("debug", "Loaded at %s", module:http_url());
end
