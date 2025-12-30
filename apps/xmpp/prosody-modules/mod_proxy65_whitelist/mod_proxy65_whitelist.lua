local allowed_streamhosts = module:get_option_set("allowed_streamhosts", {}); -- eg proxy.eu.jabber.org

if module:get_option_boolean("allow_local_streamhosts", true) then
	for hostname, host in pairs(hosts) do
		if host.modules.proxy65 then
			allowed_streamhosts:add(hostname);
		end
	end

	module:hook_global("host-activated", function (host)
		if hosts[host].modules.proxy65 then
			allowed_streamhosts:add(host);
		end
	end);
end

local function filter_streamhosts(tag)
	if tag.name == "streamhost" and not allowed_streamhosts:contains(tag.attr.jid) then
		return nil;
	end
	return tag;
end

module:hook("iq/full", function (event)
	local stanza = event.stanza;
	if stanza.attr.type == "set" then
		local payload = stanza:get_child("query", "http://jabber.org/protocol/bytestreams");
		if payload then
			payload:maptags(filter_streamhosts);
		end
	end
end, 1);
