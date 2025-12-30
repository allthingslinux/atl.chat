local jid = require "util.jid";
local set = require "util.set";
local st = require "util.stanza";
local usermanager = require "core.usermanager";
local host = module.host;

local admins;
if usermanager.get_jids_with_role then
	admins = set.new(usermanager.get_jids_with_role("prosody:admin", host));
else -- COMPAT w/pre-0.12
	admins = module:get_option_inherited_set("admins");
end

module:depends("spam_reporting")

module:hook("spam_reporting/spam-report", function(event)
	local reporter_bare_jid = jid.bare(event.stanza.attr.from)
	local report = reporter_bare_jid.." reported spam from "..event.jid..": "..(event.reason or "no reason given")
	for admin_jid in admins
		do
			module:send(st.message({from=host,
			type="chat",to=admin_jid},
			report));
		end
end)

module:hook("spam_reporting/abuse-report", function(event)
	local reporter_bare_jid = jid.bare(event.stanza.attr.from)
	local report = reporter_bare_jid.." reported abuse from "..event.jid..": "..(event.reason or "no reason given")
	for admin_jid in admins
		do
			module:send(st.message({from=host,
			type="chat",to=admin_jid},
			report));
		end
end)
