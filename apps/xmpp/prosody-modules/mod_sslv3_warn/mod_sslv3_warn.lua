local st = require"util.stanza";
local host = module.host;

local warning_message = module:get_option_string("sslv3_warning", "Your connection is encrypted using the SSL 3.0 protocol, which has been demonstrated to be insecure and will be disabled soon.  Please upgrade your client.");

module:hook("resource-bind", function (event)
	local session = event.session;
	module:log("debug", "mod_%s sees that %s logged in", module.name, session.username);

	local ok, protocol = pcall(function(session)
		return session.conn:socket():info"protocol";
	end, session);
	if not ok then
		module:log("debug", protocol);
	elseif protocol == "SSLv3" then
		module:add_timer(15, function ()
			if session.type == "c2s" and session.resource then
				session.send(st.message({ from = host, type = "headline", to = session.full_jid }, warning_message));
			end
		end);
	end
end);
