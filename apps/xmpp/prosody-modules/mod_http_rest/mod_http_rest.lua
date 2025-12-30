module:depends"http"

local jid_split = require "util.jid".split;
local jid_prep = require "util.jid".prep;
local stanza = require "util.stanza";
local test_password = require "core.usermanager".test_password;
local b64_decode = require "util.encodings".base64.decode;
local formdecode = require "net.http".formdecode;
local xml = require"util.xml";

local function handle_post(event, path, authed_user)
	local request = event.request;
	local headers = request.headers;
	local body_type = headers.content_type;
	if body_type == "text/xml" and request.body then
        local parsed, err = xml.parse(request.body);
        if parsed then
            module:log("debug", "Sending %s", parsed);
            module:send(parsed);
            return 201;
        end
	else
		return 415;
	end
	return 422;
end

module:provides("http", {
	default_path = "/rest";
	route = {
		["POST"] = handle_post;
		OPTIONS = function(e)
			local headers = e.response.headers;
			headers.allow = "POST";
			headers.accept = "test/xml";
			return 200;
		end;
	}
});
