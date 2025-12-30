local jid = require"util.jid";

module:depends("audit");
-- luacheck: read globals module.audit

module:hook("token-grant-created", function(event)
	module:audit(jid.join(event.username, event.host), "token-grant-created", {
	});
end)

module:hook("token-grant-revoked", function(event)
	module:audit(jid.join(event.username, event.host), "token-grant-revoked", {
	});
end)

module:hook("token-revoked", function(event)
	module:audit(jid.join(event.username, event.host), "token-revoked", {
	});
end)
