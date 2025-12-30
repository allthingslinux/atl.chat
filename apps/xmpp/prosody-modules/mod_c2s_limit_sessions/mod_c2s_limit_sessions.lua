-- mod_c2s_limit_sessions

local next, count = next, require "util.iterators".count;

local max_resources = module:get_option_number("max_resources", 10);

local sessions = hosts[module.host].sessions;
module:hook("resource-bind", function(event)
	local session = event.session;
	if count(next, sessions[session.username].sessions) > max_resources then
		session:close{ condition = "policy-violation", text = "Too many resources" };
		return false
	end
end, -1);
