local st = require "util.stanza";

local pubsub = module:depends"pubsub";

local actor = module.host .. "/modules/" .. module.name;

local pubsub_xmlns = "http://jabber.org/protocol/pubsub"

local node = module:get_option_string(module.name .. "_node", "stats");

local function publish_stats(stats, stats_extra)
	local id = "current";
	local xitem = st.stanza("item", { xmlns = pubsub_xmlns, id = id })
		:tag("query", { xmlns = "http://jabber.org/protocol/stats" });

	for name, value in pairs(stats) do
		local stat_extra = stats_extra[name];
		local unit = stat_extra and stat_extra.units;
		xitem:tag("stat", { name = name, unit = unit, value = tostring(value) }):up();
	end

	local ok, err = pubsub.service:publish(node, actor, id, xitem);
	if not ok then
		module:log("error", "Error publishing stats: %s", err);
	end
end

function module.load()
	pubsub.service:create(node, true, {
		persistent_items = false;
		max_items = 1;
	});
	pubsub.service:set_affiliation(node, true, actor, "publisher");
end

module:hook_global("stats-updated", function (event)
	publish_stats(event.stats, event.stats_extra);
end);

function module.unload()
	pubsub.service:delete(node, true);
end

module:hook("pubsub-summary/http://jabber.org/protocol/stats", function (event)
	local payload = event.payload;
	local summary = {};
	for stat in payload:childtags("stat") do
		if stat.attr.name and stat.attr.value then
			table.insert(summary, string.format("%s: %g %s", stat.attr.name, tonumber(stat.attr.value), stat.attr.units or ""));
		end
	end
	table.sort(summary);
	return table.concat(summary, "\n");
end);

