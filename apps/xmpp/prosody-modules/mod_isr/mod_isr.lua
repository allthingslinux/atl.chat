local st = require "util.stanza";

local mod_smacks = module:depends("smacks");

local xmlns_sasl2 = "urn:xmpp:sasl:1";
local xmlns_sm = "urn:xmpp:sm:3";
local xmlns_isr = "https://xmpp.org/extensions/isr/0";
local xmlns_errors = "urn:ietf:params:xml:ns:xmpp-stanzas";

module:hook_tag(xmlns_sasl2, "authenticate", function (session, auth)
	local isr_resume = auth:get_child("inst-resume", xmlns_isr);
	if not isr_resume then return end
	local is_using_token = isr_resume.attr["with-isr-token"] ~= "false";
	if is_using_token then
		-- TODO: If authing with token, set session.sasl_handler to our own
		-- event.session.sasl_handler = ...
		error("not yet implemented");
	end

	-- Cache resume element for future processing after SASL success
	session.isr_sm_resume = isr_resume:get_child("resume", "urn:xmpp:sm:3");
end, 100);

module:hook("sasl2/c2s/success", function (event)
	local session = event.session;
	local sm_resume = session.isr_sm_resume;
	if sm_resume then
		session.isr_sm_resume = nil;
		local resumed, err = mod_smacks.do_resume(session, sm_resume);
		if not resumed then
			local failed = st.stanza("failed", { xmlns = xmlns_sm, h = ("%d"):format(err.context.h) })
				:tag(err.condition, { xmlns = xmlns_errors });
			event.success:add_child(failed);
		else
			event.session = resumed.session;
			event.isr_resumed = resumed;
			event.success:tag("resumed", { xmlns = xmlns_sm,
				h = ("%d"):format(event.session.handled_stanza_count);
				previd = resumed.id; }):up();
		end
	end
end, 100);

module:hook("sasl2/c2s/success", function (event)
	-- The authenticate response has already been sent at this point
	local resumed = event.isr_resumed;
	if resumed then
		resumed.finish(); -- Finish resume and sync stanzas
	end
end, -1100);

module:hook("sasl2/c2s/failure", function (event)
	event.session.isr_sm_resume = nil;
end);

