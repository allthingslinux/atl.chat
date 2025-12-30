module:depends("http");

local st = require "util.stanza";
local json = require "util.json";
local hashes = require "util.hashes";
local from_hex = require "util.hex".from;
local hmacs = {
	sha1 = hashes.hmac_sha1;
	sha256 = hashes.hmac_sha256;
	sha384 = hashes.hmac_sha384;
	sha512 = hashes.hmac_sha512;
};

local pubsub_service = module:depends("pubsub").service;

-- configuration
local default_node = module:get_option("github_node", "github");
local node_prefix = module:get_option_string("github_node_prefix", "github/");
local node_mapping = module:get_option_string("github_node_mapping");
local github_actor = module:get_option_string("github_actor") or true;
local github_secret = module:get_option("github_secret");

-- validation
assert(github_secret, "Please set 'github_secret'");

local error_mapping = {
	["forbidden"] = 403;
	["item-not-found"] = 404;
	["internal-server-error"] = 500;
	["conflict"] = 409;
};

local function verify_signature(secret, body, signature)
	if not signature then return false; end
	local algo, digest = signature:match("^([^=]+)=(%x+)");
	if not algo then return false; end
	local hmac = hmacs[algo];
	if not algo then return false; end
	return hmac(secret, body) == from_hex(digest);
end

function handle_POST(event)
	local request, response = event.request, event.response;

	if not verify_signature(github_secret, request.body, request.headers.x_hub_signature) then
		module:log("debug", "Signature validation failed");
		return 401;
	end

	local data = json.decode(request.body);
	if not data then
		response.status_code = 400;
		return "Invalid JSON. From you of all people...";
	end

	local node = default_node;
	if node_mapping then
		node = node_prefix .. data.repository[node_mapping];
	end

	local github_event = request.headers.x_github_event or data.object_kind;
	if not github_event and data.commits then
		github_event = "push"; -- curl?
	end
	module:log("debug", "Handling '%s' event: \n%s\n", github_event, tostring(request.body));

	if github_event == "push" then

		for _, commit in ipairs(data.commits) do
			local ok, err = pubsub_service:publish(node, github_actor, commit.id,
				st.stanza("item", { id = commit.id, xmlns = "http://jabber.org/protocol/pubsub" })
				:tag("entry", { xmlns = "http://www.w3.org/2005/Atom" })
					:tag("id"):text(commit.id):up()
					:tag("title"):text(commit.message:match("^[^\r\n]*")):up()
					:tag("summary"):text(("Commit to %s by %s: %s"):format(data.repository.name, commit.author.name, commit.message:match("^[^\r\n]*"))):up()
					:tag("content"):text(commit.message):up()
					:tag("link", { rel = "alternate", href = commit.url }):up()
					:tag("published"):text(commit.author.date):up()
					:tag("author")
						:tag("name"):text(commit.author.name):up()
						:tag("email"):text(commit.author.email):up()
						:up()
			);
			if not ok then
				return error_mapping[err] or 500;
			end
		end

	elseif github_event then
		module:log("debug", "Unsupported Github event %q", github_event);
		return 501;
	end

	response.status_code = 202;
	return "Thank you Github!";
end

module:provides("http", {
	route = {
		POST = handle_POST;
	};
});

if not node_mapping then
	function module.load()
		if not pubsub_service.nodes[default_node] then
			local ok, err = pubsub_service:create(default_node, true);
			if not ok then
				module:log("error", "Error creating node: %s", err);
			else
				module:log("debug", "Node %q created", default_node);
			end
		end
	end
end
