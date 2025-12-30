local method = {}
local method_mt = { __index = method }

-- This should return a set of supported mechanisms
function method:mechanisms()
	return {
		["OAUTH-SOMETHING"] = true;
	}
end

-- Called when a mechanism is selecetd
function method:select(mechanism)
	return mechanism == "OAUTH-SOMETHING";
end

-- Called for each message received
function method:process(message)
	-- parse the message
	if false then
		-- To send a SASL challenge:
		return "challenge", "respond-to-this";
	end

	if false then
		-- To fail, send:
		return "failure", "not-authorized", "Helpful error message here";
	end

	self.username = "someone";
	return "success";
end

local function new_sasl()
	return setmetatable({}, method_mt);
end

function method:clean_clone()
	return setmetatable({}, method_mt);
end

local provider = {}

function provider.get_sasl_handler()
	return new_sasl();
end

module:provides("auth", provider);
