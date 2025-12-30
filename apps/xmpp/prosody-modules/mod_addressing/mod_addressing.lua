-- TODO Querying other servers for support, needs to keep track of remote
-- server disco features

local xmlns_address = 'http://jabber.org/protocol/address';

local function handle_extended_addressing(data)
	local stanza = data.stanza;
	if stanza.attr.type == "error" then
		return -- so we don't process bounces
	end
	local orig_to = stanza.attr.to;
	local addresses = stanza:get_child("addresses", xmlns_address);
	if addresses then
		module:log("debug", "Extended addressing found");
		local destinations = {};
		addresses:maptags(function(address)
			if address.attr.xmlns == xmlns_address and address.name == "address" then
				local type, jid, delivered = address.attr.type, address.attr.jid, address.attr.delivered;
				if (type == "cc" or type == "bcc" or type == "to")
					and jid and not delivered then
					destinations[#destinations+1] = jid;
					module:log("debug", "%s to %s", type, jid)
					if type == "to" or type == "cc" then
						address.attr.delivered = "true";
						return address;
					elseif type == "bcc" then
						return nil;
					end
				end
			end
			return address; -- unsupported stuff goes right back
		end);
		for i=1,#destinations do
			stanza.attr.to = destinations[i];
			module:log("debug", "posting stanza to %s", destinations[i])
			module:send(stanza);
		end
		stanza.attr.to = orig_to;
		return stanza.attr.to == module.host or nil;
	end
end

module:hook("message/host", handle_extended_addressing, 10);
module:hook("message/bare", handle_extended_addressing, 10);
module:hook("message/full", handle_extended_addressing, 10);

module:hook("presence/host", handle_extended_addressing, 10);
module:hook("presence/bare", handle_extended_addressing, 10);
module:hook("presence/full", handle_extended_addressing, 10);

-- IQ stanzas makes no sense

module:add_feature(xmlns_address);
