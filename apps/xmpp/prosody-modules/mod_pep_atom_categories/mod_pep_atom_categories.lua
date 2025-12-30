module:depends("pep");

local st = require"util.stanza";

local options = {
	access_model = "open",
	max_items = "max",
};

module:handle_items("pep-service", function (event)
        local service = event.item.service;

        module:hook_object_event(service.events, "item-published", function(event)
		local service = event.service;
		local node = event.node;
		local actor = event.actor;
		local id = event.id;
		local item = event.item;

		local entry = item:get_child("entry", "http://www.w3.org/2005/Atom");
		if entry == nil then
			return;
		end

		for category in entry:childtags("category") do
			local term = category.attr.term;
			local payload = st.stanza("item", {xmlns = "http://jabber.org/protocol/pubsub"})
				:tag("item", {xmlns = "xmpp:linkmauve.fr/x-categories", jid = service.jid, node = node, id = id});
			service:publish("category-"..term, actor, nil, payload, options);
		end
	end);
end);
