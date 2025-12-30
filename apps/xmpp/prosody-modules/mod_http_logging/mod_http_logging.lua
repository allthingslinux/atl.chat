-- mod_http_logging
--
-- Copyright (C) 2015 Kim Alvefur
--
-- This project is MIT/X11 licensed. Please see the
-- COPYING file in the source package for more information.
--
-- Produces HTTP logs in the style of Apache
--
-- TODO
-- * Configurable format?

module:set_global();

local server = require "net.http.server";

local function get_content_len(response, body)
	local len = response.headers.content_length;
	if len then return len; end
	if not body then body = response.body; end
	if body then return #tostring(body); end
end

local function log_response(response, body)
	local len = tostring(get_content_len(response, body) or "-");
	local request = response.request;
	local ip = request.ip;
	if not ip and request.conn then
		ip = request.conn:ip();
	end
	local req = string.format("%s %s HTTP/%s", request.method, request.path, request.httpversion);
	local date = os.date("%d/%m/%Y:%H:%M:%S %z");
	module:log("info", "%s - - [%s] \"%s\" %d %s", ip, date, req, response.status_code, len);
end

local send_response = server.send_response;
local function log_and_send_response(response, body)
	if not response.finished then
		log_response(response, body);
	end
	return send_response(response, body);
end

local send_file = server.send_file;
local function log_and_send_file(response, f)
	if not response.finished then
		log_response(response);
	end
	return send_file(response, f);
end

if module.wrap_object_event then
	-- Use object event wrapping, allows clean unloading of the module
	module:wrap_object_event(server._events, false, function (handlers, event_name, event_data)
		if event_data.response then
			event_data.response.send = log_and_send_response;
			event_data.response.send_file = log_and_send_file;
		end
		return handlers(event_name, event_data);
	end);
else
	-- Fall back to monkeypatching, unlikely to behave nicely in the
	-- presence of other modules also doing this
	server.send_response = log_and_send_response;
	server.send_file = log_and_send_file;
	function module.unload()
		server.send_response = send_response;
		server.send_file = send_file;
	end
end
