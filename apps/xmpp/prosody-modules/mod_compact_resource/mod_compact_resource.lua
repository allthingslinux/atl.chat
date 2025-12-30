
local base64_encode = require"util.encodings".base64.encode;
local random_bytes = require"util.random".bytes;

local b64url = { ["+"] = "-", ["/"] = "_", ["="] = "" };
local function random_resource()
	return base64_encode(random_bytes(8)):gsub("[+/=]", b64url);
end

module:hook("pre-resource-bind", function (event)
	event.resource = random_resource();
end);
