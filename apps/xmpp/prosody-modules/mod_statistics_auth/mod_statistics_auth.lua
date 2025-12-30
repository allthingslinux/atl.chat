-- mod_statistics_auth
module:set_global();

local auth_ok, auth_fail = 0, 0

function module.add_host(module)
	module:hook("authentication-success", function(event)
		auth_ok = auth_ok + 1
	end);
	module:hook("authentication-failure", function(event)
		auth_fail = auth_fail + 1
	end);
end

module:provides("statistics", {
	statistics = {
		c2s_auth = {
			get = function ()
				return auth_ok;
			end;
			tostring = tostring;
		};
		c2s_authfail = {
			get = function ()
				return auth_fail;
			end;
			tostring = tostring;
		};
	}
});
