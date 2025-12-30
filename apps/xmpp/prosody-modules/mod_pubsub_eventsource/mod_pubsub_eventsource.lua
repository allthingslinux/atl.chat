module:depends("http");
module:depends("pubsub");

local streams = {};

local service = hosts[module.host].modules.pubsub.service;

function client_closed(response)
	local node = response._eventsource_node;
	module:log("debug", "Destroying client for %q", node);
	streams[node][response] = nil;
	if next(streams[node]) == nil then
		streams[node] = nil;
	end
end

function serve_stream(event, node)
	module:log("debug", "Client subscribed to: %s", node);

	local response = event.response;
	response.on_destroy = client_closed;
	response._eventsource_node = node;

	response.conn:write(table.concat({
		"HTTP/1.1 200 OK";
		"Content-Type: text/event-stream";
		"Access-Control-Allow-Origin: *";
		"Access-Control-Allow-Methods: GET";
		"Access-Control-Max-Age: 7200";
		"";
		"";
	}, "\r\n"));

	local clientlist = streams[node];
	if not clientlist then
		clientlist = {};
		streams[node] = clientlist;
	end
	clientlist[response] = response.conn;

	return true;
end

function handle_update(event)
	module:log("debug", "Item published: %q", event.node);
	local node = event.node;
	local clientlist = streams[node];
	local item = event.item;
	if (item.name == "json" and item.attr.xmlns == "urn:xmpp:json:0") or (item.name == "data" and item.attr.xmlns == "https://prosody.im/protocol/data") then
		item = item[1];
	end
	local data = "data: "..tostring(item):gsub("\n", "\ndata: ").."\n\n";
	if not clientlist then module:log("debug", "No clients for %q", node); return; end
	for response, conn in pairs(clientlist) do
		conn:write(data);
	end
end

module:provides("http", {
	name = "eventsource";
	route = {
		["GET /*"] = serve_stream;
	};
});

module:hook_object_event(service.events, "item-published", handle_update);
