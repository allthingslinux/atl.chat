local s_match = string.match;
local registerMechanism = require "util.sasl".registerMechanism;
local saslprep = require "util.encodings".stringprep.saslprep;
local nodeprep = require "util.encodings".stringprep.nodeprep;
local log = require "util.logger".init("sasl");
local _ENV = nil;


local function oauthbearer(self, message)
	if not message then
		return "failure", "malformed-request";
	end

	local authorization, password = s_match(message, "^n,a=([^,]*),\1auth=Bearer ([^\1]+)");
	if not authorization then
		return "failure", "malformed-request";
	end

	local authentication = s_match(authorization, "(.-)@.*");

	-- SASLprep password and authentication
	authentication = saslprep(authentication);
	password = saslprep(password);

	if (not password) or (password == "") or (not authentication) or (authentication == "") then
		log("debug", "Username or password violates SASLprep.");
		return "failure", "malformed-request", "Invalid username or password.";
	end

	local _nodeprep = self.profile.nodeprep;
	if _nodeprep ~= false then
		authentication = (_nodeprep or nodeprep)(authentication);
		if not authentication or authentication == "" then
			return "failure", "malformed-request", "Invalid username or password."
		end
	end

	local correct, state = false, false;
    correct, state = self.profile.oauthbearer(self, authentication, password, self.realm);

	self.username = authentication
	if state == false then
		return "failure", "account-disabled";
	elseif state == nil or not correct then
		return "failure", "not-authorized", "Unable to authorize you with the authentication credentials you've sent.";
	end
	return "success";
end

registerMechanism("OAUTHBEARER", {"oauthbearer"}, oauthbearer);
