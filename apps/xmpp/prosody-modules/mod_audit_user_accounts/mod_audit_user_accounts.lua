module:depends("audit");
-- luacheck: read globals module.audit

local dt = require "util.datetime";
local jid = require "util.jid";
local st = require "util.stanza";

local function audit_basic_event(name, custom_handler)
	module:hook(name, function (event)
		local custom;
		if custom_handler then
			custom = custom_handler(event);
		end
		module:audit(jid.join(event.username, module.host), name, {
			session = event.session;
			custom = custom;
		});
	end);
end

audit_basic_event("user-registered", function (event)
	local invite = event.validated_invite or (event.session and event.session.validated_invite);
	if not invite then return; end
	return {
		st.stanza(
			"invite-used",
			{
				xmlns = "xmpp:prosody.im/audit",
				token = invite.token,
			}
		);
	};
end);

audit_basic_event("user-deregistered-pending");
audit_basic_event("user-deregistered");

audit_basic_event("user-enabled");
audit_basic_event("user-disabled", function (event)
	local meta = event.meta;
	if not meta then return end

	local meta_st = st.stanza("disabled", {
		xmlns = "xmpp:prosody.im/audit";
		reason = meta.reason;
		when = meta.when and dt.datetime(meta.when) or nil;
	});
	if meta.comment then
		meta_st:text_tag("comment", meta.comment);
	end

	return { meta_st };
end);
