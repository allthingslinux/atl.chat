local datamanager = require "util.datamanager";
local st = require "util.stanza";
local host = module.host;

module:hook("user-registered", function(event)
	local username = event.username;
	local data = datamanager.load(username, host, "account_details");
	local vcard = datamanager.load(username, host, "vcard");
	--module:log("debug", "Has account details: %s", data and "yes" or "no");
	--module:log("debug", "Has vCard: %s", vcard and "yes" or "no");
	if data and not vcard then
		local name, first, last = data.name, data.first, data.last;
		if not name and (first and last) then
			name = first .. " " .. last;
		elseif name and not (first and last) then
			first, last = name:match("^(%w+)%s+(%w+)$")
		end
		local vcard = st.stanza("vCard", { xmlns = "vcard-temp" })
			:tag("VERSION"):text("3.0"):up();
		if first or last then
			vcard:tag("N")
				:tag("FAMILY"):text(last or ""):up()
				:tag("GIVEN"):text(first or ""):up()
			:up()
		end
		if name then
			vcard:tag("FN"):text(name or ""):up()
		end
		vcard:tag("NICKNAME"):text(data.nick or username):up();
		if data.email then
			vcard:tag("EMAIL"):tag("USERID"):text(data.email):up():up();
		end
		local ok, err = datamanager.store(username, host, "vcard", st.preserialize(vcard));
		if not ok then
			module:log("error", "Couldn't save vCard data, %s", err);
		end
	end
end);
