
module:hook("authentication-success", function (event)
	local session = event.session;
	local sasl_handler = session and session.sasl_handler;
	local log = session and session.log or module._log
	log("info", "Authenticated with %s", sasl_handler and sasl_handler.selected or "legacy auth");
end);
