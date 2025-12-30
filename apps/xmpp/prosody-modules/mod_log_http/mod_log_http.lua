module:set_global();

local http = require "net.http";
local codes = require "net.http.codes";
local json = require "util.json";

local log = assert(io.open(assert(module:get_option_string("log_http_file"), "Please supply log_http_file in the config"), "a+"));
log:setvbuf("line");

local function append_request(id, req)
	local headers = {};
	for k, v in pairs(req.headers) do
		table.insert(headers, { name = k, value = v });
	end
	local queryString = {};
	if req.query then
		for _, pair in ipairs(http.formdecode(req.query)) do
			table.insert(queryString, pair);
		end
	end
	log:write("<<<", json.encode({
		id = id;
		type = "request";
		method = req.method;
		url = req.url;
		httpVersion = "HTTP/1.1";
		cookies = {};
		headers = headers;
		queryString = queryString;
		postData = req.body and {
			mimeType = req.headers["Content-Type"];
			text = req.body;
		} or nil;
		headersSize = -1;
		bodySize = -1;
	}), "\n");
end

local function append_response(id, resp)
	local headers = {};
	for k, v in pairs(resp.headers) do
		table.insert(headers, { name = k, value = v });
	end
	log:write(">>>", json.encode({
		id = id;
		type = "response";
		status = resp.code;
		statusText = codes[resp.code];
		httpVersion = resp.httpversion;
		cookies = {};
		headers = headers;
		content = resp.body and {
			size = #resp.body;
			mimeType = resp.headers.content_type;
			text = resp.body;
		} or nil;
		headersSize = -1;
		bodySize = -1;
	}), "\n");
end

module:hook_object_event(http.events, "request", function (event)
	module:log("warn", "Request to %s!", event.url);
	append_request(event.request.id, event.request);
end);

module:hook_object_event(http.events, "request-connection-error", function (event)
	module:log("warn", "Failed to make request to %s!", event.url);
end);

module:hook_object_event(http.events, "response", function (event)
	module:log("warn", "Received response %d from %s!", event.code, event.url);
	append_response(event.request.id, event.response);
end);

function module.unload()
	log:close();
end
