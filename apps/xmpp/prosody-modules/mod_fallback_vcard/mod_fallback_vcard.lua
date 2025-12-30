local datamanager = require "util.datamanager";
local usermanager = require "core.usermanager";
local st = require "util.stanza";
local host = module.host;
local jid_split = require "util.jid".split;

local orgname = module:get_option_string("default_vcard_orgname");
local orgmail = module:get_option_boolean("default_vcard_orgmail");

module:hook("iq/bare/vcard-temp:vCard", function(event)
	local session, stanza = event.origin, event.stanza;
	local to = stanza.attr.to;
	local username = jid_split(to);
	if not username then return end

	local vcard = datamanager.load(username, host, "vcard");
	local data = datamanager.load(username, host, "account_details");
	local exists = usermanager.user_exists(username, host);
	module:log("debug", "has %s: %s", "vcard", tostring(vcard));
	module:log("debug", "has %s: %s", "data", tostring(data));
	module:log("debug", "has %s: %s", "exists", tostring(exists));
	data = data or {};

	if not(vcard) and data and exists then
		-- MAYBE
		-- first .. " " .. last
		-- first, last = name:match("^(%w+) (%w+)$")
		local vcard = st.reply(stanza):tag("vCard", { xmlns = "vcard-temp" })
			:tag("VERSION"):text("3.0"):up()
			:tag("N")
				:tag("FAMILY"):text(data.last or ""):up()
				:tag("GIVEN"):text(data.first or ""):up()
			:up()
			:tag("FN"):text(data.name or ""):up()
			:tag("NICKNAME"):text(data.nick or username):up()
			:tag("JABBERID"):text(username.."@"..host):up();
		if orgmail then
			vcard:tag("EMAIL"):tag("USERID"):text(username.."@"..host):up():up();
		elseif data.email then
			vcard:tag("EMAIL"):tag("USERID"):text(data.email):up():up();
		end
		if orgname then
			vcard:tag("ORG"):tag("ORGNAME"):text(orgname):up():up();
		end
		session.send(vcard);
		return true;
	end
end, 1);
