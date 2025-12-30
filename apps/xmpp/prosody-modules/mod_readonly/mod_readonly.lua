local st = require "util.stanza";

local stores = module:get_option("readonly_stores", {
	vcard = { "vcard-temp", "vCard" };
});

local namespaces = {};
for name, namespace in pairs(stores) do
	namespaces[table.concat(namespace, ":")] = name;
end

local function prevent_write(event)
	local stanza = event.stanza;
	local xmlns_and_tag = stanza.tags[1].attr.xmlns..":"..stanza.tags[1].name;
	local store_name = namespaces[xmlns_and_tag];
	if store_name then
		module:log("warn", "Preventing modification of %s store by %s", store_name, stanza.attr.from);
		event.origin.send(st.error_reply(stanza, "cancel", "not-allowed", store_name.." data is read-only"));
		return true; -- Block stanza
	end
end

for namespace in pairs(namespaces) do
	module:hook("iq-set/bare/"..namespace, prevent_write, 200);
end
