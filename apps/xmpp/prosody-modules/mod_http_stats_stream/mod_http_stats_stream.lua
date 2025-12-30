module:set_global();

local statsman = require "core.statsmanager";
local http = require "net.http.server";
local json = require "util.json";

assert(statsman.get_stats, "not compatible with trunk based on openmetrics");

local sessions = {};

local function updates_client_closed(response)
	module:log("debug", "Streamstats client closed");
	sessions[response] = nil;
end

local function get_updates(event)
	local request, response = event.request, event.response;

	response.on_destroy = updates_client_closed;

	response.headers.content_type = "text/event-stream";
	response.headers.x_accel_buffering = "no"; -- for nginx maybe?
	local resp = http.prepare_header(response);
	table.insert(resp, "event: stats-full\r\n");
	table.insert(resp, "data: ");
	table.insert(resp, json.encode(statsman.get_stats()));
	table.insert(resp, "\r\n\r\n");
	response.conn:write(table.concat(resp));

	sessions[response] = request;
	return true;
end


module:hook("stats-updated", function (event)
	local data = table.concat({
		"event: stats-updated";
		"data: "..json.encode(event.changed_stats);
		"";
		"";
	}, "\r\n")
	for response in pairs(sessions) do
		response.conn:write(data);
	end
end);


module:depends("http");
module:provides("http", {
	route = {
		GET = get_updates;
	}
});
