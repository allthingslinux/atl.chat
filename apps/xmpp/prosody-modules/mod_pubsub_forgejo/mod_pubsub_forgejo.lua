module:depends("http")
local pubsub_service = module:depends("pubsub").service

local st = require "util.stanza"
local json = require "util.json"
local hashes = require "util.hashes"
local from_hex = require"util.hex".from
local hmacs = {
	sha1 = hashes.hmac_sha1,
	sha256 = hashes.hmac_sha256,
	sha384 = hashes.hmac_sha384,
	sha512 = hashes.hmac_sha512
}

local format = module:require "format"
local default_templates = module:require "templates"

-- configuration
local forgejo_secret = module:get_option("forgejo_secret")

local default_node = module:get_option("forgejo_node", "forgejo")
local node_prefix = module:get_option_string("forgejo_node_prefix", "forgejo/")
local node_mapping = module:get_option_string("forgejo_node_mapping")
local forgejo_actor = module:get_option_string("forgejo_actor") or true

local skip_commitless_push = module:get_option_boolean(
				                             "forgejo_skip_commitless_push", true)
local custom_templates = module:get_option("forgejo_templates")

local forgejo_templates = default_templates

if custom_templates ~= nil then
	for k, v in pairs(custom_templates) do forgejo_templates[k] = v end
end

-- used for develoment, should never be set in prod!
local insecure = module:get_option_boolean("forgejo_insecure", false)
-- validation
if not insecure then assert(forgejo_secret, "Please set 'forgejo_secret'") end

local error_mapping = {
	["forbidden"] = 403,
	["item-not-found"] = 404,
	["internal-server-error"] = 500,
	["conflict"] = 409
}

local function verify_signature(secret, body, signature)
	if insecure then return true end
	if not signature then return false end
	local algo, digest = signature:match("^([^=]+)=(%x+)")
	if not algo then return false end
	local hmac = hmacs[algo]
	if not algo then return false end
	return hmac(secret, body) == from_hex(digest)
end

function handle_POST(event)
	local request, response = event.request, event.response

	if not verify_signature(forgejo_secret, request.body,
	                        request.headers.x_hub_signature) then
		module:log("debug", "Signature validation failed")
		return 401
	end

	local data = json.decode(request.body)
	if not data then
		response.status_code = 400
		return "Invalid JSON. From you of all people..."
	end

	local forgejo_event = request.headers.x_forgejo_event or data.object_kind

	if skip_commitless_push and forgejo_event == "push" and data.total_commits == 0 then
		module:log("debug", "Skipping push event with 0 commits")
		return 501
	end

	if forgejo_templates[forgejo_event] == nil then
		module:log("debug", "Unsupported forgejo event %q", forgejo_event)
		return 501
	end

	local item = format(data, forgejo_templates[forgejo_event])

	if item == nil then
		module:log("debug", "Formatter returned nil for event %q", forgejo_event)
		return 501
	end

	local node = default_node
	if node_mapping then node = node_prefix .. data.repository[node_mapping] end

	create_node(node)

	local ok, err = pubsub_service:publish(node, forgejo_actor, item.attr.id, item)
	if not ok then return error_mapping[err] or 500 end

	response.status_code = 202
	return "Thank you forgejo.\n" .. tostring(item:indent(1, " "))
end

module:provides("http", {route = {POST = handle_POST}})

function create_node(node)
	if not pubsub_service.nodes[node] then
		local ok, err = pubsub_service:create(node, true)
		if not ok then
			module:log("error", "Error creating node: %s", err)
		else
			module:log("debug", "Node %q created", node)
		end
	end
end
