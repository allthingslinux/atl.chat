module:depends("http");
local nodeprep = require "util.encodings".stringprep.nodeprep;

local jid_split = require "util.jid".split;
local json = require "util.json";

local streams = {};

function client_closed(response)
	local node = response._eventsource_node;
	module:log("debug", "Destroying client for %q", node);
	streams[node][response] = nil;
	if next(streams[node]) == nil then
		streams[node] = nil;
	end
end

function serve_stream(event, node)
	local response = event.response;

	node = nodeprep(node);
	if node == nil then
		return 400;
	end

	module:log("debug", "Client subscribed to: %s", node);

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

function handle_message(event)
	local room, stanza = event.room, event.stanza;
	local node = (jid_split(event.room.jid));
	local clientlist = streams[node];
	if not clientlist then module:log("debug", "No clients for %q", node); return; end

	-- Extract body from message
	local body = event.stanza:get_child_text("body");
	if not body then
		return;
	end
	local nick = select(3, jid_split(stanza.attr.from));
	-- Encode body and broadcast to eventsource subscribers
	local json_data = json.encode({
		nick = nick;
		body = body;
	});
	local data = "data: "..json_data:gsub("\n", "\ndata: \n").."\n\n";
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


module:hook("muc-broadcast-message", handle_message);
