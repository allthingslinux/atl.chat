-- HTTP Is User Valid
-- By Nicolas Cedilnik <nicoco@nicoco.fr>

local jid_prep = require "util.jid".prep;
local jid_split = require "util.jid".split;
local test_password = require "core.usermanager".test_password;
local b64_decode = require "util.encodings".base64.decode;
local saslprep = require "util.encodings".stringprep.saslprep;
local realm = module:get_host() .. "/" .. module:get_name();
module:depends"http";

local function authenticate (event, path)
	local request = event.request;
	local response = event.response;
	local headers = request.headers;
	if not headers.authorization then
		response.headers.www_authenticate = ("Basic realm=%q"):format(realm);
		return 401
	end
	local from_jid, password = b64_decode(headers.authorization:match"[^ ]*$"):match"([^:]*):(.*)";
	from_jid = jid_prep(from_jid);
	password = saslprep(password);
	if from_jid and password then
		local user, host = jid_split(from_jid);
		local ok, err = test_password(user, host, password);
		if ok and user and host then
			return 200
		elseif err then
			return 401
		end
	end
end

module:provides("http", {
	route = {
		GET = authenticate
	};
});
