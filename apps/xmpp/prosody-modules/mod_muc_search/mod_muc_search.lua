-- mod_muc_search
-- https://muclumbus.jabbercat.org/docs/api#xmpp
-- TODO
-- Result set management (pagination, limits)
-- Sorting
-- min_users

local dataforms = require "util.dataforms";
local st = require "util.stanza";

local mod_muc = module:depends("muc");
assert(mod_muc.live_rooms, "Missing required MUC API. Prosody >= hg:f5c43e829d93 required");

local search_form = dataforms.new {
	{
		type = "hidden";
		value = "https://xmlns.zombofant.net/muclumbus/search/1.0#params";
		name = "FORM_TYPE";
	};
	{
		type = "text-single";
		label = "Search for";
		name = "q";
	};
	{
		type = "boolean";
		value = true;
		label = "Search in name";
		name = "sinname";
	};
	{
		type = "boolean";
		value = true;
		label = "Search in description";
		name = "sindescription";
	};
	{
		type = "boolean";
		value = true;
		label = "Search in address";
		name = "sinaddr";
	};
	{
		type = "text-single";
		value = "1";
		label = "Minimum number of users";
		name = "min_users";
	};
	{
		options = {
			{
				label = "Number of online users";
				value = "nusers";
			};
			{
				label = "Address";
				value = "address";
			};
		};
		type = "list-single";
		value = "nusers";
		label = "Sort results by";
		name = "key";
	};
};

module:hook("iq-get/host/https://xmlns.zombofant.net/muclumbus/search/1.0:search", function (event)
	local origin, stanza = event.origin, event.stanza;
	origin.send(st.reply(stanza)
		:tag("search", { xmlns = "https://xmlns.zombofant.net/muclumbus/search/1.0" })
			:add_child(search_form:form()));
	return true;
end);

module:hook("iq-set/host/https://xmlns.zombofant.net/muclumbus/search/1.0:search", function (event)
	local origin, stanza = event.origin, event.stanza;
	local search = stanza.tags[1];
	local submitted = search:get_child("x", "jabber:x:data");
	if not submitted then
		origin.send(st.error_reply("modify", "bad-request", "Missing dataform"));
		return;
	end
	local query = search_form:data(submitted);
	module:log("debug", "Got query: %q", query);

	local result = st.reply(stanza)
		:tag("result", { xmlns = "https://xmlns.zombofant.net/muclumbus/search/1.0" });

	for room in mod_muc.live_rooms() do -- TODO s/live/all/ but preferably along with pagination/rsm
		if room:get_public() and not room:get_members_only() then
			module:log("debug", "Looking at room %s %q", room.jid, room._data);
			if (query.sinname and room:get_name():find(query.q, 1, true))
			or (query.sindescription and (room:get_description() or ""):find(query.q, 1, true))
			or (query.sinaddr and room.jid:find(query.q, 1, true)) then
				result:tag("item", { address = room.jid })
					:text_tag("name", room:get_name())
					:text_tag("description", room:get_description())
					:text_tag("language", room:get_language())
					:tag("is-open"):up()
				:up();
			end
		end
	end
	origin.send(result);
	return true;
end);
