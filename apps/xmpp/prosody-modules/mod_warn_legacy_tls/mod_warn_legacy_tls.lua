local st = require"util.stanza";
local host = module.host;

local deprecated_protocols = module:get_option_set("legacy_tls_versions", { "SSLv3", "TLSv1", "TLSv1.1" });
local warning_message = module:get_option_string("legacy_tls_warning", "Your connection is encrypted using the %s protocol, which has known problems and will be disabled soon.  Please upgrade your client.");

module:hook("resource-bind", function (event)
	local session = event.session;
	module:log("debug", "mod_%s sees that %s logged in", module.name, session.username);

	local ok, protocol = pcall(function(session)
		return session.conn:socket():info"protocol";
	end, session);
	if not ok then
		module:log("debug", "Could not determine TLS version: %s", protocol);
	elseif deprecated_protocols:contains(protocol) then
		session.log("warn", "Uses %s", protocol);
		module:add_timer(15, function ()
			if session.type == "c2s" and session.resource then
				session.send(st.message({ from = host, type = "headline", to = session.full_jid }, warning_message:format(protocol)));
			end
		end);
	else
		module:log("debug", "Using acceptable TLS version: %s", protocol);
	end
end);
