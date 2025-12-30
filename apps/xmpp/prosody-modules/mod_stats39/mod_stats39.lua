local statsman = require "core.statsmanager";
local st = require "util.stanza";
local s_format = string.format;

assert(statsman.get_stats, "not compatible with trunk based on openmetrics");

module:add_feature("http://jabber.org/protocol/stats");

module:hook("iq/host/http://jabber.org/protocol/stats:query", function (event)
	local origin, stanza = event.origin, event.stanza;
	local stats, _, extra = statsman.get_stats();
	local reply = st.reply(stanza);
	reply:tag("query", { xmlns = "http://jabber.org/protocol/stats" });
	for stat, value in pairs(stats) do
		local unit = extra[stat] and extra[stat].units;
		reply:tag("stat", { name = stat, unit = unit, value = s_format("%.12g", value) }):up();
	end
	origin.send(reply);
	return true;
end)
